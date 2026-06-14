"""
WorldMonitor - 外部事件监控主服务
提供事件源管理、处理管道、HTTP 管理界面
"""

import asyncio
import json
import logging
import signal
from pathlib import Path

import aiohttp
import yaml
from aiohttp import web
from event_bus import Event as BusEvent
from event_bus import EventBus
from event_processor import PipelineManager
from event_sources import (
    EventSource,
    FileWatcherSource,
    MarketDataSource,
    PollingSource,
    RSSSource,
    ScriptSource,
    SourceConfig,
    SourceManager,
    WebhookSource,
)

logger = logging.getLogger(__name__)


class WorldMonitor:
    """WorldMonitor 主服务"""

    def __init__(self, config_path: str = "~/.hermes/config/worldmonitor.yaml"):
        self.config_path = Path(config_path).expanduser()
        self.config: dict = {}
        self.running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self.http_app: web.Application | None = None
        self.http_runner: web.AppRunner | None = None
        self.http_site: web.TCPSite | None = None

        # 核心组件
        self.event_bus = EventBus()
        self.source_manager = SourceManager()
        self.pipeline_manager = PipelineManager()

        # 集成处理器
        self._integrations: list[dict] = []

    async def start(self):
        """启动服务"""
        logger.info("Starting WorldMonitor...")

        # 加载配置
        self.config = self._load_config()

        # 设置事件循环
        self._loop = asyncio.get_event_loop()

        # 启动事件总线
        await self.event_bus.start()

        # 设置处理器
        self._setup_integrations()
        self._setup_pipelines()

        # 创建并注册事件源
        self._create_sources()

        # 启动所有事件源
        await self.source_manager.start_all()

        # 启动 HTTP 管理界面
        await self._start_http_server()

        # 设置信号处理
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self.running = True
        logger.info("WorldMonitor started successfully")

        # 保持运行
        while self.running:
            await asyncio.sleep(1)

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning(f"Config not found: {self.config_path}, using defaults")
            return self._get_default_config()

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f) or {}

            # 确保使用正确的存储路径
            if "event_bus" in config and "db_path" in config["event_bus"]:
                config["event_bus"]["db_path"] = config["event_bus"]["db_path"].replace(".db", ".json")

            logger.info(f"Config loaded: {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """默认配置"""
        return {
            "monitor": {
                "port": 11000,
                "host": "0.0.0.0",
                "admin_token": None
            },
            "event_bus": {
                "db_path": "~/.hermes/data/worldmonitor_events.db",
                "max_retries": 3
            },
            "sources": {},
            "pipelines": {},
            "integrations": {}
        }

    def _setup_integrations(self):
        """设置集成处理器"""
        integrations_config = self.config.get("integrations", {})

        # Hermes 任务执行集成
        if integrations_config.get("hermes_tasks"):
            self._integrations.append({
                "type": "hermes_task",
                "enabled": True,
                "config": integrations_config["hermes_tasks"]
            })

        # 通知集成
        for channel, config in integrations_config.get("notifications", {}).items():
            self._integrations.append({
                "type": "notification",
                "channel": channel,
                "enabled": config.get("enabled", True),
                "config": config
            })

        # 数据库更新集成
        if integrations_config.get("database"):
            self._integrations.append({
                "type": "database",
                "enabled": True,
                "config": integrations_config["database"]
            })

        # 外部 API 调用
        if integrations_config.get("external_apis"):
            self._integrations.append({
                "type": "api",
                "enabled": True,
                "config": integrations_config["external_apis"]
            })

    def _setup_pipelines(self):
        """设置处理管道"""
        pipelines_config = self.config.get("pipelines", {})

        for name, p_config in pipelines_config.items():
            from event_processor import Pipeline
            pipeline = Pipeline({"name": name, **p_config})
            self.pipeline_manager.register_pipeline(pipeline)

            # 设置管道输出接收器
            if "output" in p_config:
                self._setup_pipeline_sink(name, p_config["output"])

    def _setup_pipeline_sink(self, pipeline_name: str, output_config: dict):
        """设置管道输出"""
        output_type = output_config.get("type")

        if output_type == "hermes_task":
            # 触发 Hermes 任务
            def trigger_task(event):
                asyncio.create_task(self._trigger_hermes_task(event, output_config))

            self.pipeline_manager.add_sink(pipeline_name, trigger_task)

        elif output_type == "notification":
            # 发送通知
            def send_notification(event):
                asyncio.create_task(self._send_notification(event, output_config))

            self.pipeline_manager.add_sink(pipeline_name, send_notification)

        elif output_type == "database":
            # 更新数据库
            def update_db(event):
                asyncio.create_task(self._update_database(event, output_config))

            self.pipeline_manager.add_sink(pipeline_name, update_db)

        elif output_type == "api":
            # 调用外部 API
            def call_api(event):
                asyncio.create_task(self._call_external_api(event, output_config))

            self.pipeline_manager.add_sink(pipeline_name, call_api)

    def _create_sources(self):
        """从配置创建事件源"""
        sources_config = self.config.get("sources", {})

        for source_id, s_config in sources_config.items():
            if not s_config.get("enabled", True):
                continue

            source_type = s_config.get("type")
            config = SourceConfig(
                id=source_id,
                type=source_type,
                enabled=s_config.get("enabled", True),
                schedule=s_config.get("schedule"),
                filters=s_config.get("filters"),
                metadata=s_config.get("metadata", {})
            )

            source = self._create_source(source_type, config, s_config)
            if source:
                self.source_manager.register_source(source)

    def _create_source(self, source_type: str, config: SourceConfig, raw_config: dict) -> EventSource | None:
        """创建具体的事件源"""
        try:
            if source_type == "rss":
                return RSSSource(
                    config=config,
                    url=raw_config["url"],
                    max_items=raw_config.get("max_items", 10)
                )

            if source_type == "webhook":
                return WebhookSource(
                    config=config,
                    port=raw_config.get("port", 11001),
                    path=raw_config.get("path", "/webhook")
                )

            if source_type == "file_watcher":
                return FileWatcherSource(
                    config=config,
                    paths=raw_config["paths"],
                    patterns=raw_config.get("patterns")
                )

            if source_type == "polling":
                return PollingSource(
                    config=config,
                    endpoint=raw_config["endpoint"],
                    method=raw_config.get("method", "GET"),
                    body=raw_config.get("body"),
                    headers=raw_config.get("headers"),
                    interval=raw_config.get("interval", 60)
                )

            if source_type == "market":
                return MarketDataSource(
                    config=config,
                    market_ids=raw_config["market_ids"],
                    api_key=raw_config.get("api_key")
                )

            if source_type == "script":
                return ScriptSource(
                    config=config,
                    script_path=raw_config["script_path"],
                    args=raw_config.get("args", []),
                    env=raw_config.get("env", {}),
                    timeout=raw_config.get("timeout", 30)
                )

            logger.error(f"Unknown source type: {source_type}")
            return None

        except KeyError as e:
            logger.error(f"Missing config for {source_type}: {e}")
            return None

    async def _start_http_server(self):
        """启动 HTTP 管理服务器"""
        host = self.config.get("monitor", {}).get("host", "0.0.0.0")
        port = self.config.get("monitor", {}).get("port", 11000)

        self.http_app = web.Application()

        # 路由
        self.http_app.router.add_get("/monitor_status", self._handle_status)
        self.http_app.router.add_get("/monitor_sources", self._handle_sources)
        self.http_app.router.add_get("/monitor_events", self._handle_events)
        self.http_app.router.add_post("/monitor_sources/{source_id}/toggle", self._handle_toggle_source)
        self.http_app.router.add_post("/monitor_reload", self._handle_reload)

        # 启动
        self.http_runner = web.AppRunner(self.http_app)
        await self.http_runner.setup()
        self.http_site = web.TCPSite(self.http_runner, host, port)
        await self.http_site.start()

        logger.info(f"HTTP server started at http://{host}:{port}")

    async def stop(self):
        """停止服务"""
        if not self.running:
            return

        logger.info("Stopping WorldMonitor...")
        self.running = False

        # 停止事件源
        await self.source_manager.stop_all()

        # 停止事件总线
        await self.event_bus.stop()

        # 停止 HTTP 服务器
        if self.http_site:
            await self.http_site.stop()
        if self.http_runner:
            await self.http_runner.cleanup()

        logger.info("WorldMonitor stopped")

    # HTTP 处理器

    async def _handle_status(self, request):
        """系统状态"""
        event_bus_stats = await self.event_bus.get_statistics()
        health = await self.event_bus.health_check()
        pipeline_stats = self.pipeline_manager.get_statistics()
        source_info = self.source_manager.get_source_info()

        status = {
            "running": self.running,
            "uptime": event_bus_stats.get("uptime", 0),
            "health": health,
            "event_bus": event_bus_stats,
            "pipelines": pipeline_stats,
            "sources": source_info,
            "config": {
                "host": self.config.get("monitor", {}).get("host"),
                "port": self.config.get("monitor", {}).get("port")
            }
        }

        return web.json_response(status)

    async def _handle_sources(self, request):
        """事件源列表"""
        source_info = self.source_manager.get_source_info()
        return web.json_response({"sources": source_info})

    async def _handle_events(self, request):
        """事件查询"""
        # 解析查询参数
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))
        source = request.query.get("source")
        event_type = request.query.get("type")
        status = request.query.get("status", "processed")

        # 从持久化存储查询
        from event_bus import EventPersister
        persister = EventPersister(
            self.config.get("event_bus", {}).get("db_path", "~/.hermes/data/worldmonitor_events.db")
        )

        # 这里简化查询，实际需要更复杂的SQL
        events = await persister.get_pending_events(limit)

        # 过滤
        if source:
            events = [e for e in events if e.source == source]
        if event_type:
            events = [e for e in events if e.type == event_type]

        # 转换为可序列化格式
        event_dicts = [e.to_dict() for e in events[offset:offset+limit]]

        return web.json_response({"events": event_dicts, "total": len(events)})

    async def _handle_toggle_source(self, request):
        """启用/禁用事件源"""
        source_id = request.match_info["source_id"]

        # 查找配置并更新
        sources = self.config.get("sources", {})
        if source_id in sources:
            sources[source_id]["enabled"] = not sources[source_id].get("enabled", True)

            # 保存配置
            self._save_config()

            # 重新加载源
            self.source_manager.unregister_source(source_id)
            self._create_sources()
            await self.source_manager.start_all()

            return web.json_response({"status": "ok", "enabled": sources[source_id]["enabled"]})

        return web.json_response({"error": "Source not found"}, status=404)

    async def _handle_reload(self, request):
        """热重载配置"""
        try:
            self.config = self._load_config()

            # 停止所有源
            await self.source_manager.stop_all()

            # 清空并重建
            self.source_manager.sources.clear()
            self._create_sources()
            await self.source_manager.start_all()

            logger.info("Configuration reloaded")
            return web.json_response({"status": "ok", "message": "Configuration reloaded"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    # 集成处理器

    async def _trigger_hermes_task(self, event: BusEvent, config: dict):
        """触发 Hermes 任务"""
        try:
            task_type = config.get("task_type", "default")
            task_params = config.get("params", {})

            # 这里需要根据实际的 Hermes 集成方式实现
            # 可能的方式：
            # 1. 调用本地 CLI 工具
            # 2. 发送 HTTP 请求到 Hermes
            # 3. 写入队列文件
            # 4. 调用 Python API

            logger.info(f"Triggering Hermes task: {task_type} for event {event.id}")

            # 示例：调用 Hermes CLI
            cmd = [
                "hermes", "task", "execute",
                "--type", task_type,
                "--event", json.dumps(event.data)
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"Hermes task failed: {stderr.decode()}")

        except Exception as e:
            logger.error(f"Failed to trigger Hermes task: {e}")

    async def _send_notification(self, event: BusEvent, config: dict):
        """发送通知"""
        channel = config.get("channel", "console")

        try:
            if channel == "console":
                print(f"[NOTIFICATION] Event: {event.type} from {event.source}")
                print(f"Data: {json.dumps(event.data, indent=2)}")

            elif channel == "telegram":
                await self._send_telegram(event, config)

            elif channel == "email":
                await self._send_email(event, config)

            elif channel == "webhook":
                await self._call_webhook(event, config)

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def _send_telegram(self, event: BusEvent, config: dict):
        """发送 Telegram 通知"""
        # 实现 Telegram 发送

    async def _send_email(self, event: BusEvent, config: dict):
        """发送邮件"""

    async def _call_webhook(self, event: BusEvent, config: dict):
        """调用外部 webhook"""
        url = config.get("url")
        if not url:
            return

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=event.to_dict()) as resp:
                    if resp.status != 200:
                        logger.error(f"Webhook call failed: {resp.status}")
            except Exception as e:
                logger.error(f"Webhook error: {e}")

    async def _update_database(self, event: BusEvent, config: dict):
        """更新数据库"""
        # 实现数据库写入

    async def _call_external_api(self, event: BusEvent, config: dict):
        """调用外部 API"""
        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})

        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, json=event.to_dict(), headers=headers) as resp:
                    if resp.status not in [200, 201, 204]:
                        logger.error(f"API call failed: {resp.status}")
            except Exception as e:
                logger.error(f"API error: {e}")


async def main():
    """主入口"""
    # 日志配置
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    monitor = WorldMonitor()

    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
