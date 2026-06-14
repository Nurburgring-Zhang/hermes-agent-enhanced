"""
WorldMonitor Event Bus - 事件总线核心系统
提供发布订阅、优先级队列、持久化事件流
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """事件优先级枚举"""
    CRITICAL = 1  # 关键事件，立即处理
    HIGH = 2      # 高优先级
    NORMAL = 5    # 正常优先级
    LOW = 8       # 低优先级
    BACKGROUND = 10  # 后台任务


@dataclass
class Event:
    """标准事件结构"""
    id: str
    source: str               # 事件来源标识
    type: str                 # 事件类型
    data: dict[str, Any]      # 事件数据
    timestamp: float          # 事件时间戳
    priority: int = EventPriority.NORMAL  # 优先级
    tags: list[str] = None    # 标签，用于路由过滤
    retry_count: int = 0      # 重试次数
    max_retries: int = 3      # 最大重试次数

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """从字典创建事件"""
        return cls(**data)

    def should_retry(self) -> bool:
        """判断是否应该重试"""
        return self.retry_count < self.max_retries

    def increment_retry(self):
        """增加重试计数"""
        self.retry_count += 1

    def is_expired(self, ttl_seconds: int) -> bool:
        """检查事件是否过期"""
        age = time.time() - self.timestamp
        return age > ttl_seconds


class EventPersister:
    """事件持久化存储（基于JSON文件）"""

    def __init__(self, store_path: str = "~/.hermes/data/worldmonitor_events.json"):
        self.store_path = Path(store_path).expanduser()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._events: dict[str, dict] = {}
        self._load()

    def _load(self):
        """从文件加载事件"""
        try:
            if self.store_path.exists():
                with open(self.store_path) as f:
                    data = json.load(f)
                    self._events = data.get("events", {})
        except Exception as e:
            logger.error(f"Failed to load events: {e}")
            self._events = {}

    def _save(self):
        """保存事件到文件"""
        try:
            with open(self.store_path, "w") as f:
                json.dump({
                    "events": self._events,
                    "updated": time.time()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save events: {e}")

    async def store(self, event: Event):
        """存储事件"""
        async with self._lock:
            self._events[event.id] = {
                "id": event.id,
                "source": event.source,
                "type": event.type,
                "data": event.data,
                "timestamp": event.timestamp,
                "priority": event.priority,
                "tags": event.tags,
                "retry_count": event.retry_count,
                "max_retries": event.max_retries,
                "status": "pending",
                "created": time.time()
            }
            self._save()

    async def mark_processed(self, event_id: str):
        """标记事件已处理"""
        async with self._lock:
            if event_id in self._events:
                self._events[event_id]["status"] = "processed"
                self._events[event_id]["processed_at"] = time.time()
                self._save()

    async def mark_failed(self, event_id: str, error: str):
        """标记事件处理失败"""
        async with self._lock:
            if event_id in self._events:
                self._events[event_id]["status"] = "failed"
                self._events[event_id]["error"] = error
                self._save()

    async def get_pending_events(self, limit: int = 100) -> list[Event]:
        """获取待处理事件（按优先级）"""
        async with self._lock:
            pending = []
            for event_data in self._events.values():
                if event_data["status"] == "pending":
                    pending.append(event_data)

            # 排序：优先级升序，时间戳升序
            pending.sort(key=lambda e: (e["priority"], e["timestamp"]))

            # 转换为 Event 对象
            events = []
            for event_data in pending[:limit]:
                clean_data = {
                    "id": event_data["id"],
                    "source": event_data["source"],
                    "type": event_data["type"],
                    "data": event_data["data"],
                    "timestamp": event_data["timestamp"],
                    "priority": event_data["priority"],
                    "tags": event_data["tags"],
                    "retry_count": event_data["retry_count"],
                    "max_retries": event_data["max_retries"]
                }
                events.append(Event.from_dict(clean_data))

            return events

    async def get_statistics(self) -> dict:
        """获取事件统计"""
        async with self._lock:
            stats = {
                "by_status": {},
                "total": len(self._events)
            }

            for event_data in self._events.values():
                status = event_data["status"]
                if status not in stats["by_status"]:
                    stats["by_status"][status] = {"count": 0, "oldest": None, "newest": None}

                stats["by_status"][status]["count"] += 1

                ts = event_data["timestamp"]
                if stats["by_status"][status]["oldest"] is None or ts < stats["by_status"][status]["oldest"]:
                    stats["by_status"][status]["oldest"] = ts
                if stats["by_status"][status]["newest"] is None or ts > stats["by_status"][status]["newest"]:
                    stats["by_status"][status]["newest"] = ts

            return stats


class EventSubscription:
    """事件订阅"""

    def __init__(
        self,
        callback: Callable,
        filters: dict | None = None,
        max_concurrent: int = 10
    ):
        self.callback = callback
        self.filters = filters or {}
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active = True

    def matches(self, event: Event) -> bool:
        """检查事件是否匹配过滤器"""
        # 事件类型过滤
        if "event_types" in self.filters:
            if event.type not in self.filters["event_types"]:
                return False

        # 来源过滤
        if "sources" in self.filters:
            if event.source not in self.filters["sources"]:
                return False

        # 标签过滤（需要包含所有指定标签）
        if "tags" in self.filters:
            required_tags = set(self.filters["tags"])
            event_tags = set(event.tags)
            if not required_tags.issubset(event_tags):
                return False

        # 优先级范围
        if "min_priority" in self.filters:
            if event.priority < self.filters["min_priority"]:
                return False
        if "max_priority" in self.filters:
            if event.priority > self.filters["max_priority"]:
                return False

        return True

    async def __call__(self, event: Event):
        """执行回调"""
        if not self.active:
            return

        async with self.semaphore:
            try:
                await self.callback(event)
            except Exception as e:
                logger.error(f"Subscription callback failed: {e}")
                raise

    def cancel(self):
        """取消订阅"""
        self.active = False


class EventBus:
    """事件总线 - 核心系统"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or "~/.hermes/data/worldmonitor_events.db"
        self.persister = EventPersister(db_path)

        # 优先级队列：索引=优先级，值=asyncio.Queue
        self._queues: dict[int, asyncio.Queue] = {}
        self._running = False
        self._consumer_task: asyncio.Task | None = None

        # 订阅管理
        self._subscriptions: set[EventSubscription] = set()
        self._subscription_lock = asyncio.Lock()

        # 指标统计
        self.stats = {
            "published": 0,
            "processed": 0,
            "failed": 0,
            "retries": 0,
            "started_at": None
        }
        self._stats_lock = asyncio.Lock()

    async def start(self):
        """启动事件总线"""
        if self._running:
            return

        self._running = True
        self.stats["started_at"] = time.time()

        # 初始化优先级队列
        for priority in range(1, 11):
            self._queues[priority] = asyncio.Queue()

        # 启动消费者任务
        self._consumer_task = asyncio.create_task(self._consume_loop())

        # 加载并重试失败的事件
        await self._recover_failed_events()

        logger.info("EventBus started")

    async def stop(self):
        """停止事件总线"""
        self._running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        logger.info("EventBus stopped")

    async def publish(self, event: Event) -> bool:
        """发布事件"""
        try:
            # 持久化存储
            await self.persister.store(event)

            # 放入优先级队列
            priority = min(max(event.priority, 1), 10)
            await self._queues[priority].put(event)

            # 更新统计
            async with self._stats_lock:
                self.stats["published"] += 1

            logger.debug(f"Event published: {event.id} type={event.type}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    async def _consume_loop(self):
        """事件消费循环"""
        while self._running:
            try:
                # 从所有优先级队列消费（从高优先级开始）
                event = None
                for priority in sorted(self._queues.keys()):
                    if not self._queues[priority].empty():
                        try:
                            event = self._queues[priority].get_nowait()
                            break
                        except asyncio.QueueEmpty:
                            continue

                if event:
                    await self._process_event(event)
                else:
                    # 没有事件时等待
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                await asyncio.sleep(1)

    async def _process_event(self, event: Event):
        """处理单个事件"""
        try:
            # 检查是否应该重试或过期
            if event.is_expired(ttl_seconds=3600):  # 1小时过期
                logger.warning(f"Event expired: {event.id}")
                await self.persister.mark_processed(event.id)
                return

            # 触发所有匹配的订阅
            async with self._subscription_lock:
                subscriptions = list(self._subscriptions)

            tasks = []
            for sub in subscriptions:
                if sub.matches(event):
                    tasks.append(sub(event))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # 标记为已处理
            await self.persister.mark_processed(event.id)

            async with self._stats_lock:
                self.stats["processed"] += 1

            logger.debug(f"Event processed: {event.id}")

        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")

            async with self._stats_lock:
                self.stats["failed"] += 1

            # 处理失败：重试或标记
            if event.should_retry():
                event.increment_retry()
                await self.persister.store(event)
                await self._queues[event.priority].put(event)

                async with self._stats_lock:
                    self.stats["retries"] += 1

                logger.info(f"Event {event.id} retry {event.retry_count}/{event.max_retries}")
            else:
                await self.persister.mark_failed(event.id, str(e))
                logger.error(f"Event {event.id} failed permanently")

    async def _recover_failed_events(self):
        """恢复失败的事件进行重试"""
        try:
            pending = await self.persister.get_pending_events(limit=1000)
            for event in pending:
                priority = min(max(event.priority, 1), 10)
                await self._queues[priority].put(event)

            if pending:
                logger.info(f"Recovered {len(pending)} pending events")
        except Exception as e:
            logger.error(f"Failed to recover events: {e}")

    def subscribe(
        self,
        callback: Callable,
        filters: dict | None = None,
        max_concurrent: int = 10
    ) -> EventSubscription:
        """
        订阅事件
        
        Args:
            callback: 回调函数(event) -> await None
            filters: 过滤器 {'event_types': [...], 'sources': [...], 'tags': [...]}
            max_concurrent: 最大并发数
        
        Returns:
            EventSubscription 对象，用于取消订阅
        """
        subscription = EventSubscription(callback, filters, max_concurrent)
        self._subscriptions.add(subscription)
        logger.debug(f"New subscription added: {filters}")
        return subscription

    def unsubscribe(self, subscription: EventSubscription):
        """取消订阅"""
        subscription.cancel()
        self._subscriptions.discard(subscription)
        logger.debug("Subscription removed")

    async def get_statistics(self) -> dict:
        """获取总线统计"""
        stats = self.stats.copy()

        # 队列深度
        queue_depths = {}
        for priority, queue in self._queues.items():
            queue_depths[priority] = queue.qsize()

        stats["queues"] = queue_depths
        stats["subscriptions"] = len(self._subscriptions)

        # 持久化统计
        try:
            db_stats = await self.persister.get_statistics()
            stats["persistence"] = db_stats
        except Exception as e:
            logger.error(f"Failed to get persistence stats: {e}")

        return stats

    async def health_check(self) -> dict:
        """健康检查"""
        is_running = self._running
        error_count = 0

        try:
            await self.persister.get_statistics()
        except:
            error_count += 1

        return {
            "healthy": is_running and error_count == 0,
            "running": is_running,
            "db_error": error_count > 0,
            "uptime": time.time() - self.stats["started_at"] if self.stats["started_at"] else 0
        }


# 便利函数：创建全局事件总线实例
_global_bus: EventBus | None = None

async def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
        await _global_bus.start()
    return _global_bus

async def publish_event(event: Event) -> bool:
    """发布事件到全局总线"""
    bus = await get_event_bus()
    return await bus.publish(event)
