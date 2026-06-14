"""
WorldMonitor Event Sources - 多样化事件源适配器
支持：RSS/Atom、HTTP Webhook、文件监控、定时轮询、市场数据、自定义脚本
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import feedparser
from event_bus import Event, EventPriority, publish_event
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """事件源配置"""
    id: str
    type: str
    enabled: bool = True
    schedule: str | None = None  # cron表达式或间隔
    filters: dict | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "enabled": self.enabled,
            "schedule": self.schedule,
            "filters": self.filters or {},
            "metadata": self.metadata or {}
        }


class EventSource(ABC):
    """事件源基类"""

    def __init__(self, config: SourceConfig):
        self.config = config
        self.running = False
        self._task: asyncio.Task | None = None
        self.error_count = 0
        self.last_run = None
        self.last_success = None

    @abstractmethod
    async def fetch(self) -> list[Event]:
        """获取事件（子类实现）"""

    async def run_once(self):
        """运行一次"""
        try:
            events = await self.fetch()

            for event in events:
                # 应用过滤器
                if self._should_filter(event):
                    continue

                # 发布到事件总线
                await publish_event(event)

            self.last_success = time.time()
            self.error_count = 0
            logger.info(f"Source {self.config.id} fetched {len(events)} events")

        except Exception as e:
            self.error_count += 1
            logger.error(f"Source {self.config.id} error: {e}")

            # 错误太多则暂停
            if self.error_count > 10:
                logger.warning(f"Source {self.config.id} disabled due to errors")
                self.running = False

        finally:
            self.last_run = time.time()

    def _should_filter(self, event: Event) -> bool:
        """检查是否应该过滤事件"""
        if not self.config.filters:
            return False

        filters = self.config.filters

        # 关键词过滤
        if "keywords" in filters:
            keywords = filters["keywords"]
            event_text = json.dumps(event.data).lower()
            if not any(k.lower() in event_text for k in keywords):
                return True

        # 正则过滤
        if "regex" in filters:
            import re
            pattern = filters["regex"]
            event_text = json.dumps(event.data)
            if not re.search(pattern, event_text):
                return True

        # 来源白名单
        if "whitelist" in filters.get("sources", []):
            if event.source not in filters["sources"]["whitelist"]:
                return True

        return False

    def start(self, loop: asyncio.AbstractEventLoop | None = None):
        """启动事件源"""
        if self.running:
            return

        if not loop:
            loop = asyncio.get_event_loop()

        self.running = True
        self._task = loop.create_task(self._run_loop())
        logger.info(f"Source {self.config.id} started")

    def stop(self):
        """停止事件源"""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info(f"Source {self.config.id} stopped")

    async def _run_loop(self):
        """事件源主循环"""
        if self.config.schedule:
            # 定时模式
            await self._run_scheduled()
        else:
            # 连续轮询模式
            await self._run_polling()

    async def _run_scheduled(self):
        """定时运行模式"""
        schedule_str = self.config.schedule

        # 解析调度配置
        interval = self._parse_schedule(schedule_str)

        while self.running:
            if interval:
                await asyncio.sleep(interval)
            else:
                # cron表达式：简单实现，每60秒检查一次
                await asyncio.sleep(60)
                # 实际cron实现需要croniter库，这里简化为

            if self.running:
                await self.run_once()

    async def _run_polling(self):
        """轮询模式（默认30秒间隔）"""
        interval = 30

        while self.running:
            await self.run_once()
            if self.running:
                await asyncio.sleep(interval)

    def _parse_schedule(self, schedule_str: str) -> float | None:
        """解析调度配置"""
        # 支持格式：30s, 5m, 1h, 1d
        if schedule_str.endswith("s"):
            return float(schedule_str[:-1])
        if schedule_str.endswith("m"):
            return float(schedule_str[:-1]) * 60
        if schedule_str.endswith("h"):
            return float(schedule_str[:-1]) * 3600
        if schedule_str.endswith("d"):
            return float(schedule_str[:-1]) * 86400

        return None


class RSSSource(EventSource):
    """RSS/Atom 订阅源"""

    def __init__(self, config: SourceConfig, url: str, max_items: int = 10):
        super().__init__(config)
        self.url = url
        self.max_items = max_items
        self.seen_guids = set()
        self.state_file = Path(f"~/.hermes/data/rss_state_{config.id}.json").expanduser()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self):
        """加载已见文章状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self.seen_guids = set(data.get("guids", []))
            except:
                self.seen_guids = set()

    def _save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, "w") as f:
                json.dump({
                    "guids": list(self.seen_guids)[-1000:]  # 保留最近1000个
                }, f)
        except Exception as e:
            logger.error(f"Failed to save RSS state: {e}")

    async def fetch(self) -> list[Event]:
        """获取RSS订阅"""
        events = []

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        logger.warning(f"RSS fetch failed: {response.status}")
                        return events

                    content = await response.text()

                # 解析feed
                feed = feedparser.parse(content)

                for entry in feed.entries[:self.max_items]:
                    guid = entry.get("id", entry.get("link", ""))

                    # 检查是否已处理
                    if guid and guid in self.seen_guids:
                        continue

                    # 创建事件
                    event_data = {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", entry.get("description", "")),
                        "published": entry.get("published", ""),
                        "author": entry.get("author", ""),
                        "feed_title": feed.feed.get("title", self.config.id)
                    }

                    event = Event(
                        id=str(uuid.uuid4()),
                        source=self.config.id,
                        type="rss.entry",
                        data=event_data,
                        timestamp=time.time(),
                        priority=EventPriority.NORMAL,
                        tags=["rss", "news"]
                    )

                    events.append(event)

                    if guid:
                        self.seen_guids.add(guid)

                self._save_state()

            except Exception as e:
                logger.error(f"RSS fetch error: {e}")
                raise

        return events


class WebhookSource(EventSource):
    """HTTP Webhook 接收器"""

    def __init__(self, config: SourceConfig, port: int = 11001, path: str = "/webhook"):
        super().__init__(config)
        self.port = port
        self.path = path
        self.server = None
        self.app = None
        self._received_events = []

    async def start(self, loop=None):
        """启动Webhook服务器"""
        await super().start(loop)
        await self._start_server()

    async def _start_server(self):
        """启动HTTP服务器"""
        try:
            from aiohttp import web

            self.app = web.Application()
            self.app.router.add_post(self.path, self._handle_webhook)

            runner = web.AppRunner(self.app)
            await runner.setup()

            site = web.TCPSite(runner, "0.0.0.0", self.port)
            await site.start()

            self.server = runner
            logger.info(f"Webhook server started on port {self.port}")

        except ImportError:
            logger.error("aiohttp not installed, webhook source disabled")
            self.running = False
        except Exception as e:
            logger.error(f"Failed to start webhook server: {e}")
            self.running = False

    async def _handle_webhook(self, request):
        """处理webhook请求"""
        try:
            data = await request.json()

            # 创建事件
            event = Event(
                id=str(uuid.uuid4()),
                source=self.config.id,
                type="webhook.received",
                data=data,
                timestamp=time.time(),
                priority=EventPriority.HIGH,
                tags=["webhook", request.headers.get("X-Event-Type", "unknown")]
            )

            # 立即发布
            await publish_event(event)

            return web.Response(text="OK")

        except Exception as e:
            logger.error(f"Webhook handling error: {e}")
            return web.Response(status=500, text=str(e))

    async def stop(self):
        """停止"""
        await super().stop()
        if self.server:
            await self.server.cleanup()

    async def fetch(self) -> list[Event]:
        """Webhook是被动接收，返回空列表"""
        return []


class FileWatcherSource(EventSource):
    """文件系统监控"""

    def __init__(self, config: SourceConfig, paths: list[str], patterns: list[str] | None = None):
        super().__init__(config)
        self.paths = [Path(p).expanduser() for p in paths]
        self.patterns = patterns or ["*"]
        self.observer = Observer()
        self._handler = None

    async def start(self, loop=None):
        """启动文件监控"""
        await super().start(loop)

        class EventHandler(FileSystemEventHandler):
            def __init__(self, source):
                self.source = source

            def on_created(self, event):
                if not event.is_directory:
                    asyncio.create_task(self._handle(event.src_path, "created"))

            def on_modified(self, event):
                if not event.is_directory:
                    asyncio.create_task(self._handle(event.src_path, "modified"))

            async def _handle(self, path, action):
                await self.source._handle_file_event(path, action)

        self._handler = EventHandler(self)

        for path in self.paths:
            if path.exists():
                self.observer.schedule(self._handler, str(path), recursive=True)

        self.observer.start()
        logger.info(f"File watcher started on {len(self.paths)} paths")

    async def _handle_file_event(self, path: str, action: str):
        """处理文件事件"""
        try:
            # 检查文件模式匹配
            if not any(Path(path).match(p) for p in self.patterns):
                return

            event = Event(
                id=str(uuid.uuid4()),
                source=self.config.id,
                type="file.change",
                data={
                    "path": path,
                    "action": action,
                    "size": os.path.getsize(path) if os.path.exists(path) else 0,
                    "mtime": os.path.getmtime(path) if os.path.exists(path) else 0
                },
                timestamp=time.time(),
                priority=EventPriority.HIGH if action == "created" else EventPriority.LOW,
                tags=["filesystem", action]
            )

            await publish_event(event)

        except Exception as e:
            logger.error(f"File event handling error: {e}")

    async def fetch(self) -> list[Event]:
        """文件监控被动触发，返回空列表"""
        return []

    async def stop(self):
        """停止监控"""
        await super().stop()
        self.observer.stop()
        self.observer.join()


class PollingSource(EventSource):
    """定时轮询数据源"""

    def __init__(self, config: SourceConfig, endpoint: str, method: str = "GET",
                 body: dict | None = None, headers: dict | None = None,
                 interval: int = 60):
        super().__init__(config)
        self.endpoint = endpoint
        self.method = method.upper()
        self.body = body
        self.headers = headers or {}
        self.interval = interval
        self.last_data_hash = None

    async def fetch(self) -> list[Event]:
        """轮询获取数据"""
        events = []

        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {"headers": self.headers}
                if self.body and self.method in ["POST", "PUT", "PATCH"]:
                    kwargs["json"] = self.body

                async with session.request(self.method, self.endpoint, **kwargs) as response:
                    if response.status == 200:
                        data = await response.json()

                        # 检查数据是否变化
                        data_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
                        if data_hash != self.last_data_hash:
                            self.last_data_hash = data_hash

                            event = Event(
                                id=str(uuid.uuid4()),
                                source=self.config.id,
                                type="polling.update",
                                data=data,
                                timestamp=time.time(),
                                priority=EventPriority.NORMAL,
                                tags=["polling", "api"]
                            )
                            events.append(event)
                    else:
                        logger.warning(f"Polling failed: {response.status}")

        except Exception as e:
            logger.error(f"Polling error: {e}")
            raise

        return events


class MarketDataSource(EventSource):
    """市场数据源（Polymarket等）"""

    def __init__(self, config: SourceConfig, market_ids: list[str],
                 api_key: str | None = None):
        super().__init__(config)
        self.market_ids = market_ids
        self.api_key = api_key
        self.base_url = "https://clob.polymarket.com"

    async def fetch(self) -> list[Event]:
        """获取市场数据"""
        events = []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # 批量获取市场数据
                tasks = []
                for market_id in self.market_ids:
                    url = f"{self.base_url}/market/{market_id}"
                    tasks.append(self._fetch_market(session, url, headers))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Event):
                        events.append(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Market fetch error: {result}")

        except Exception as e:
            logger.error(f"Market data source error: {e}")
            raise

        return events

    async def _fetch_market(self, session, url: str, headers: dict) -> Event | None:
        """获取单个市场数据"""
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    return Event(
                        id=str(uuid.uuid4()),
                        source=self.config.id,
                        type="market.update",
                        data={
                            "market": data,
                            "timestamp": time.time()
                        },
                        timestamp=time.time(),
                        priority=EventPriority.HIGH,
                        tags=["market", "crypto", "polymarket"]
                    )
        except Exception as e:
            logger.error(f"Failed to fetch market {url}: {e}")

        return None


class ScriptSource(EventSource):
    """自定义脚本数据源"""

    def __init__(self, config: SourceConfig, script_path: str,
                 args: list[str] | None = None, env: dict | None = None,
                 timeout: int = 30):
        super().__init__(config)
        self.script_path = Path(script_path).expanduser()
        self.args = args or []
        self.env = env or {}
        self.timeout = timeout

    async def fetch(self) -> list[Event]:
        """执行脚本获取事件"""
        events = []

        if not self.script_path.exists():
            logger.error(f"Script not found: {self.script_path}")
            return events

        try:
            # 构建环境
            env = os.environ.copy()
            env.update(self.env)
            env["SOURCE_ID"] = self.config.id

            # 执行脚本
            proc = await asyncio.create_subprocess_exec(
                str(self.script_path),
                *self.args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout
                )
            except TimeoutError:
                proc.kill()
                logger.error(f"Script timeout: {self.script_path}")
                return events

            if proc.returncode != 0:
                logger.error(f"Script failed: {stderr.decode()}")
                return events

            # 解析输出（期望JSON数组或单个JSON对象）
            output = stdout.decode().strip()
            if not output:
                return events

            try:
                data = json.loads(output)

                if isinstance(data, list):
                    # 数组格式：每个元素是一个事件
                    for item in data:
                        if isinstance(item, dict):
                            event = Event(
                                id=str(uuid.uuid4()),
                                source=self.config.id,
                                type="script.output",
                                data=item,
                                timestamp=time.time(),
                                priority=EventPriority.NORMAL,
                                tags=["script"]
                            )
                            events.append(event)
                elif isinstance(data, dict):
                    # 单个事件或转换后的数据
                    event = Event(
                        id=str(uuid.uuid4()),
                        source=self.config.id,
                        type="script.output",
                        data=data,
                        timestamp=time.time(),
                        priority=EventPriority.NORMAL,
                        tags=["script"]
                    )
                    events.append(event)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON output from script: {self.script_path}")

        except Exception as e:
            logger.error(f"Script execution error: {e}")
            raise

        return events


class SourceManager:
    """事件源管理器"""

    def __init__(self):
        self.sources: dict[str, EventSource] = {}
        self.running = False

    def register_source(self, source: EventSource):
        """注册事件源"""
        self.sources[source.config.id] = source
        logger.info(f"Source registered: {source.config.id}")

    def unregister_source(self, source_id: str):
        """注销事件源"""
        if source_id in self.sources:
            source = self.sources[source_id]
            source.stop()
            del self.sources[source_id]
            logger.info(f"Source unregistered: {source_id}")

    async def start_all(self):
        """启动所有事件源"""
        self.running = True

        for source in self.sources.values():
            if source.config.enabled:
                if asyncio.iscoroutinefunction(source.start):
                    await source.start()
                else:
                    source.start()

        logger.info(f"Started {len(self.sources)} sources")

    async def stop_all(self):
        """停止所有事件源"""
        self.running = False

        tasks = []
        for source in self.sources.values():
            if asyncio.iscoroutinefunction(source.stop):
                tasks.append(source.stop())
            else:
                source.stop()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("All sources stopped")

    def get_source_info(self) -> list[dict]:
        """获取所有源状态"""
        info = []
        for source_id, source in self.sources.items():
            info.append({
                "id": source_id,
                "type": source.config.type,
                "enabled": source.config.enabled,
                "running": source.running,
                "last_run": source.last_run,
                "last_success": source.last_success,
                "error_count": source.error_count
            })
        return info
