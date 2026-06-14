"""
WorldMonitor Event Processor - 事件处理管道
支持：过滤、转换、路由、聚合
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from event_bus import Event, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    """处理上下文"""
    event: Event
    metadata: dict[str, Any] = field(default_factory=dict)
    pipeline_state: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default=None):
        """获取元数据"""
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any):
        """设置元数据"""
        self.metadata[key] = value


class Processor(ABC):
    """处理器基类"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.name = self.config.get("name", self.__class__.__name__)

    @abstractmethod
    async def process(self, context: ProcessingContext) -> Event | None:
        """处理事件，返回处理后的事件或 None（丢弃）"""

    async def __call__(self, event: Event) -> Event | None:
        """调用处理器"""
        if not self.enabled:
            return event

        context = ProcessingContext(event=event)
        try:
            result = await self.process(context)
            return result
        except Exception as e:
            logger.error(f"Processor {self.name} failed: {e}")
            return event  # 出错时返回原事件


class FilterProcessor(Processor):
    """过滤器处理器"""

    async def process(self, context: ProcessingContext) -> Event | None:
        event = context.event
        filters = self.config.get("filters", {})

        # 关键词过滤
        if "keywords" in filters:
            keywords = filters["keywords"]
            mode = filters.get("keyword_mode", "any")  # any/all

            event_text = json.dumps(event.data).lower()
            matched = any(k.lower() in event_text for k in keywords)

            if mode == "all" and not matched:
                return None
            if mode == "any" and matched:
                pass  # 通过
            elif mode == "any" and not matched:
                return None

        # 正则过滤
        if "regex" in filters:
            pattern = filters["regex"]
            event_text = json.dumps(event.data)
            if not re.search(pattern, event_text):
                return None

        # 字段存在性检查
        if "required_fields" in filters:
            for field in filters["required_fields"]:
                if field not in event.data:
                    return None

        # 数值范围
        if "range_filters" in filters:
            for field, (min_val, max_val) in filters["range_filters"].items():
                if field in event.data:
                    val = event.data[field]
                    if isinstance(val, (int, float)):
                        if min_val is not None and val < min_val:
                            return None
                        if max_val is not None and val > max_val:
                            return None

        return event


class TransformerProcessor(Processor):
    """数据转换处理器"""

    async def process(self, context: ProcessingContext) -> Event | None:
        event = context.event
        transforms = self.config.get("transforms", [])

        data = event.data.copy()

        for transform in transforms:
            t_type = transform.get("type")

            if t_type == "extract":
                # 提取字段
                path = transform.get("path", "").split(".")
                value = data
                for p in path:
                    if isinstance(value, dict) and p in value:
                        value = value[p]
                    else:
                        value = None
                        break
                if value is not None:
                    data[transform.get("output_field", "extracted")] = value

            elif t_type == "rename":
                # 重命名字段
                old = transform.get("from")
                new = transform.get("to")
                if old in data:
                    data[new] = data.pop(old)

            elif t_type == "format":
                # 格式化
                template = transform.get("template")
                if template:
                    try:
                        data["formatted"] = template.format(**data)
                    except:
                        pass

            elif t_type == "add_fields":
                # 添加固定字段
                for k, v in transform.get("fields", {}).items():
                    data[k] = v

            elif t_type == "compute":
                # 计算字段
                expression = transform.get("expression")
                if expression:
                    try:
                        # 简单的表达式求值（生产环境用ast.literal_eval或安全的eval）
                        data[transform.get("output", "computed")] = eval(expression, {}, data)
                    except:
                        pass

            elif t_type == "normalize":
                # 规范化
                field = transform.get("field")
                if field and field in data:
                    # 如：小写化、去除空格
                    if transform.get("to_lowercase"):
                        data[field] = str(data[field]).lower()
                    if transform.get("strip"):
                        data[field] = str(data[field]).strip()

        # 创建新事件
        new_event = Event(
            id=event.id,
            source=event.source,
            type=event.type,
            data=data,
            timestamp=event.timestamp,
            priority=self._adjust_priority(event.priority),
            tags=event.tags + transform.get("add_tags", []),
            retry_count=event.retry_count,
            max_retries=event.max_retries
        )

        return new_event

    def _adjust_priority(self, current: int) -> int:
        """调整优先级"""
        adjust = self.config.get("priority_adjust", 0)
        return max(1, min(10, current + adjust))


class RouterProcessor(Processor):
    """路由器处理器 - 根据规则路由事件"""

    async def process(self, context: ProcessingContext) -> Event | None:
        event = context.event
        routes = self.config.get("routes", [])

        for route in routes:
            match_type = route.get("match_type", "all")
            conditions = route.get("conditions", {})
            matched = True

            # 匹配事件类型
            if "event_types" in conditions:
                if event.type not in conditions["event_types"]:
                    matched = False

            # 匹配来源
            if "sources" in conditions:
                if event.source not in conditions["sources"]:
                    matched = False

            # 匹配标签
            if "tags" in conditions:
                required = set(conditions["tags"])
                if not required.issubset(set(event.tags)):
                    matched = False

            # 匹配数据字段
            if "data_contains" in conditions:
                for k, v in conditions["data_contains"].items():
                    if k not in event.data or event.data[k] != v:
                        matched = False

            # 匹配条件
            if matched:
                # 执行路由动作
                action = route.get("action", "pass")

                if action == "modify":
                    # 修改事件
                    modifications = route.get("modifications", {})
                    for k, v in modifications.items():
                        if callable(v):
                            event.data[k] = v(event.data)
                        else:
                            event.data[k] = v

                    # 更新优先级
                    if "priority" in route:
                        event.priority = route["priority"]

                    # 添加标签
                    if "add_tags" in route:
                        event.tags.extend(route["add_tags"])

                    return event

                if action == "drop":
                    return None

                if action == "route":
                    # 设置路由元数据
                    context.set("routed_to", route.get("target", "default"))
                    context.set("routing_key", route.get("key", event.type))

                elif action == "high_priority":
                    event.priority = EventPriority.HIGH
                    return event

        return event


class AggregatorProcessor(Processor):
    """聚合器处理器 - 去重、计数、趋势分析"""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.window_size = self.config.get("window_seconds", 300)  # 5分钟窗口
        self.max_events = self.config.get("max_events", 1000)

        # 去重存储
        self._dedup_cache: dict[str, float] = {}  # key -> timestamp
        self._counters: dict[str, Counter] = defaultdict(Counter)
        self._timestamps: dict[str, list[float]] = defaultdict(list)

        # 统计
        self.total_processed = 0
        self.total_dropped = 0

    async def process(self, context: ProcessingContext) -> Event | None:
        event = context.event
        agg_config = self.config.get("aggregation", {})

        # 去重
        if agg_config.get("deduplicate", False):
            dedup_key = self._make_dedup_key(event, agg_config)
            if dedup_key:
                now = time.time()
                if dedup_key in self._dedup_cache:
                    # 检查是否在窗口内
                    if now - self._dedup_cache[dedup_key] < self.window_size:
                        self.total_dropped += 1
                        return None  # 重复事件，丢弃

                self._dedup_cache[dedup_key] = now

                # 清理过期的缓存
                expired = [k for k, t in self._dedup_cache.items() if now - t > self.window_size]
                for k in expired:
                    del self._dedup_cache[k]

        # 计数聚合
        if agg_config.get("count", False):
            group_by = agg_config.get("group_by", ["source", "type"])

            # 构建分组键
            group_key_parts = []
            for field in group_by:
                if field == "source":
                    group_key_parts.append(event.source)
                elif field == "type":
                    group_key_parts.append(event.type)
                elif field in event.data:
                    group_key_parts.append(str(event.data[field]))
                elif field in event.tags:
                    group_key_parts.append(f"tag:{field}")

            group_key = "|".join(group_key_parts) if group_key_parts else "default"

            self._counters[group_key][event.type] += 1
            self._timestamps[group_key].append(event.timestamp)

            # 限制大小
            if len(self._timestamps[group_key]) > self.max_events:
                self._timestamps[group_key] = self._timestamps[group_key][-self.max_events:]

            # 添加到事件数据
            event.data["_aggregation"] = {
                "group_key": group_key,
                "count": self._counters[group_key][event.type],
                "window_size": self.window_size
            }

        # 趋势分析
        if agg_config.get("trends", False):
            trend_key = f"{event.source}:{event.type}"
            now = time.time()

            # 记录时间戳
            self._timestamps[trend_key].append(now)

            # 清理过期
            cutoff = now - self.window_size
            self._timestamps[trend_key] = [
                t for t in self._timestamps[trend_key]
                if t > cutoff
            ]

            # 计算趋势
            rate = len(self._timestamps[trend_key]) / self.window_size if self.window_size > 0 else 0

            event.data["_trend"] = {
                "events_per_second": rate,
                "events_in_window": len(self._timestamps[trend_key]),
                "window_seconds": self.window_size
            }

        self.total_processed += 1
        return event

    def _make_dedup_key(self, event: Event, agg_config: dict) -> str | None:
        """生成去重键"""
        fields = agg_config.get("dedup_fields", ["id"])

        if "id" in fields:
            return event.id

        parts = []
        for field in fields:
            if field == "source":
                parts.append(event.source)
            elif field == "type":
                parts.append(event.type)
            elif field in event.data:
                parts.append(str(event.data[field]))

        return "|".join(parts) if parts else None

    def get_statistics(self) -> dict:
        """获取聚合统计"""
        return {
            "total_processed": self.total_processed,
            "total_dropped": self.total_dropped,
            "cache_size": len(self._dedup_cache),
            "group_counts": {k: dict(c) for k, c in self._counters.items()}
        }


class Pipeline:
    """事件处理管道"""

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", "default")
        self.processors: list[Processor] = []
        self.enabled = config.get("enabled", True)
        self._build_processors()

    def _build_processors(self):
        """构建处理器链"""
        processor_configs = self.config.get("processors", [])

        for p_config in processor_configs:
            p_type = p_config.get("type")

            if p_type == "filter":
                processor = FilterProcessor(p_config)
            elif p_type == "transformer":
                processor = TransformerProcessor(p_config)
            elif p_type == "router":
                processor = RouterProcessor(p_config)
            elif p_type == "aggregator":
                processor = AggregatorProcessor(p_config)
            else:
                logger.warning(f"Unknown processor type: {p_type}")
                continue

            self.processors.append(processor)

    async def process(self, event: Event) -> Event | None:
        """处理事件"""
        if not self.enabled:
            return event

        context = ProcessingContext(event=event)

        for processor in self.processors:
            result = await processor(context.event)

            if result is None:
                # 事件被丢弃
                return None

            context.event = result

        return context.event


class PipelineManager:
    """管道管理器"""

    def __init__(self):
        self.pipelines: dict[str, Pipeline] = {}
        self._event_sinks: dict[str, list[Callable]] = defaultdict(list)

    def register_pipeline(self, pipeline: Pipeline):
        """注册管道"""
        self.pipelines[pipeline.name] = pipeline
        logger.info(f"Pipeline registered: {pipeline.name}")

    def unregister_pipeline(self, name: str):
        """注销管道"""
        if name in self.pipelines:
            del self.pipelines[name]

    async def process(self, event: Event, pipeline_names: list[str] | None = None) -> Event | None:
        """通过指定管道处理事件"""
        if pipeline_names is None:
            # 所有管道
            for pipeline in self.pipelines.values():
                if pipeline.enabled:
                    event = await pipeline.process(event)
                    if event is None:
                        return None
        else:
            # 指定管道
            for name in pipeline_names:
                if name in self.pipelines:
                    pipeline = self.pipelines[name]
                    if pipeline.enabled:
                        event = await pipeline.process(event)
                        if event is None:
                            return None

        return event

    def add_sink(self, pipeline_name: str, sink: Callable):
        """添加事件接收器（管道处理后）"""
        self._event_sinks[pipeline_name].append(sink)

    async def emit_to_sinks(self, pipeline_name: str, event: Event):
        """发送到所有接收器"""
        for sink in self._event_sinks.get(pipeline_name, []):
            try:
                if asyncio.iscoroutinefunction(sink):
                    await sink(event)
                else:
                    sink(event)
            except Exception as e:
                logger.error(f"Sink callback failed: {e}")

    def get_statistics(self) -> dict:
        """获取所有管道统计"""
        stats = {
            "pipelines": {},
            "total_sinks": sum(len(s) for s in self._event_sinks.values())
        }
        for name, pipeline in self.pipelines.items():
            # 这里可以扩展每个处理器的统计
            stats["pipelines"][name] = {
                "enabled": pipeline.enabled,
                "processor_count": len(pipeline.processors)
            }
        return stats
