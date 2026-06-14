"""
OpenClaw AI Smart Router - Cache System
缓存系统 - 支持LRU淘汰、过期清理、容量限制
"""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    timestamp: float
    ttl: float  # Time To Live in seconds
    access_count: int = 0
    last_access: float = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:  # 永不过期
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_access = time.time()


class LRUCache:
    """LRU 缓存实现"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                self._cache.pop(key)
                return None

            # 更新访问信息
            entry.touch()
            self._cache.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl: float = 3600):
        """设置缓存值"""
        with self._lock:
            # 清理过期项
            self._cleanup_expired()

            # 如果缓存已满，移除最久未使用的
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)

            # 添加新条目
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )
            self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """删除缓存键"""
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在（不过期）"""
        with self._lock:
            if key not in self._cache:
                return False
            entry = self._cache[key]
            if entry.is_expired():
                self._cache.pop(key)
                return False
            return True

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

    def keys(self) -> list:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())

    def values(self) -> list:
        """获取所有值"""
        with self._lock:
            return [entry.value for entry in self._cache.values()]

    def items(self) -> list:
        """获取所有键值对"""
        with self._lock:
            return list(self._cache.items())

    def _cleanup_expired(self):
        """清理过期条目"""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            self._cache.pop(key, None)

    def cleanup(self) -> int:
        """清理并返回清理的数量"""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                self._cache.pop(key, None)
            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_access = sum(entry.access_count for entry in self._cache.values())
            hit_count = sum(1 for entry in self._cache.values() if entry.access_count > 0)

            # 计算命中率
            hit_rate = hit_count / total_access if total_access > 0 else 0.0

            # 获取最热的键
            sorted_entries = sorted(
                self._cache.values(),
                key=lambda e: e.access_count,
                reverse=True
            )
            hot_keys = [(k, self._cache[k].access_count) for k in self._cache.keys()][:10]

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_access": total_access,
                "hit_count": hit_count,
                "hit_rate": round(hit_rate, 4),
                "hot_keys": hot_keys[:5]
            }


class SmartRouterCache:
    """智能路由缓存 - 包装LRU缓存，提供更高级功能"""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 3600,
        enabled: bool = True
    ):
        self.enabled = enabled
        self.default_ttl = default_ttl
        self._analysis_cache = LRUCache(max_size=max_size)
        self._lock = threading.RLock()

    def get_analysis(self, instruction: str) -> Any | None:
        """获取分析结果缓存"""
        if not self.enabled:
            return None
        return self._analysis_cache.get(instruction)

    def set_analysis(self, instruction: str, analysis: Any, ttl: float | None = None):
        """缓存分析结果"""
        if not self.enabled:
            return
        self._analysis_cache.set(instruction, analysis, ttl or self.default_ttl)

    def get_routing_decision(self, instruction_hash: str) -> Any | None:
        """获取路由决策缓存（可选实现）"""
        if not self.enabled:
            return None
        # 可以用另一个缓存
        return None

    def set_routing_decision(self, instruction_hash: str, decision: Any):
        """缓存路由决策（可选实现）"""
        if not self.enabled:
            return

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._analysis_cache.clear()

    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        with self._lock:
            return self._analysis_cache.cleanup()

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            analysis_stats = self._analysis_cache.get_stats()
            return {
                "analysis_cache": analysis_stats,
                "total_cached_items": analysis_stats["size"],
                "enabled": self.enabled
            }

    def enable(self):
        """启用缓存"""
        self.enabled = True

    def disable(self):
        """禁用缓存"""
        self.enabled = False

    def set_enabled(self, enabled: bool):
        """设置缓存启用状态"""
        self.enabled = enabled

    def get_ttl(self) -> float:
        """获取默认TTL"""
        return self.default_ttl

    def set_ttl(self, ttl: float):
        """设置默认TTL"""
        self.default_ttl = ttl

    def prefetch(self, instructions: list):
        """预缓存多个指令的分析结果（批量操作）"""
        # 这里可以实现批量预缓存逻辑


def create_cache(max_size: int = 1000, default_ttl: float = 3600, enabled: bool = True) -> SmartRouterCache:
    """创建缓存实例"""
    return SmartRouterCache(max_size, default_ttl, enabled)
