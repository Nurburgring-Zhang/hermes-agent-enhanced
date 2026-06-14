"""
OpenClaw AI Smart Router - Configuration Loader
配置文件加载器 - 支持 YAML 配置文件、热重载、环境变量覆盖
"""

import os
import threading
import time
from pathlib import Path
from typing import Any

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .logger import get_logger
from .smart_router_types import RouterConfig


class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变更处理器"""

    def __init__(self, config_loader: "ConfigLoader"):
        self.config_loader = config_loader
        self.last_modified = time.time()

    def on_modified(self, event):
        """文件修改事件"""
        if event.src_path == self.config_loader.config_path:
            current_time = time.time()
            # 防止短时间重复触发
            if current_time - self.last_modified > 1:
                self.last_modified = current_time
                self.config_loader.reload_config()


class ConfigLoader:
    """配置加载器 - 支持热重载"""

    def __init__(
        self,
        config_path: str | None = None,
        auto_reload: bool = True,
        logger=None
    ):
        self.logger = logger or get_logger()
        self.config_path = self._resolve_config_path(config_path)
        self.auto_reload = auto_reload
        self._config: RouterConfig | None = None
        self._raw_config: dict = {}
        self._observers = []
        self._lock = threading.RLock()
        self._last_modified = 0

        # 加载初始配置
        self._load_config()

        # 启动文件监视
        if self.auto_reload and self.config_path:
            self._start_watching()

    def _resolve_config_path(self, config_path: str | None) -> str:
        """解析配置文件路径"""
        if config_path:
            path = Path(config_path).expanduser().resolve()
            if path.exists():
                return str(path)
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # 默认路径
        default_paths = [
            Path(os.getcwd()) / "openclaw-router-config.yaml",
            Path.home() / ".hermes" / "skills" / "openclaw-smart-router" / "config.yaml",
            Path("/etc") / "openclaw-router" / "config.yaml"
        ]

        for path in default_paths:
            if path.exists():
                return str(path)

        # 返回默认路径，即使不存在
        return str(default_paths[1])

    def _load_config(self) -> RouterConfig:
        """加载配置文件"""
        with self._lock:
            try:
                if not os.path.exists(self.config_path):
                    self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
                    self._config = RouterConfig()
                    return self._config

                with open(self.config_path, encoding="utf-8") as f:
                    self._raw_config = yaml.safe_load(f) or {}

                # 合并环境变量覆盖
                self._apply_env_overrides()

                # 转换为类型配置
                self._config = self._build_config_from_dict(self._raw_config)

                self._last_modified = os.path.getmtime(self.config_path)
                self.logger.info(f"Configuration loaded from {self.config_path}")
                return self._config

            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
                if self._config is None:
                    self._config = RouterConfig()
                return self._config

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # 环境变量覆盖示例
        env_vars = {
            "OPENCLAW_LOG_LEVEL": ("log_level", str),
            "OPENCLAW_ENABLE_CACHE": ("enable_cache", bool),
            "OPENCLAW_AUTO_UPGRADE": ("auto_upgrade_enabled", bool),
            "OPENCLAW_UPGRADE_THRESHOLD": ("upgrade_threshold", int),
            "OPENCLAW_CACHE_EXPIRATION": ("cache_expiration", int),
        }

        for env_var, (config_key, type_converter) in env_vars.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                try:
                    if type_converter is bool:
                        value = value.lower() in ("true", "1", "yes", "on")
                    else:
                        value = type_converter(value)
                    self._raw_config[config_key] = value
                    self.logger.debug(f"Applied env override: {config_key}={value}")
                except ValueError as e:
                    self.logger.warning(f"Invalid env var {env_var}={value}: {e}")

    def _build_config_from_dict(self, data: dict[str, Any]) -> RouterConfig:
        """从字典构建配置对象"""
        config_data = data.copy()

        # 处理模型配置
        if "models" in config_data:
            models_data = config_data["models"]
            # 这里需要根据 models.py 中的模型定义构建
            from .models import ModelTier, get_all_models
            all_models = get_all_models()

            # 如果提供的是模型ID列表
            if isinstance(models_data, list):
                configured_models = []
                for model_id in models_data:
                    try:
                        model = get_model_by_id(model_id)
                        configured_models.append(model)
                    except ValueError:
                        self.logger.warning(f"Unknown model ID: {model_id}, skipping")
                config_data["models"] = configured_models
            # 如果提供的是详细配置
            elif isinstance(models_data, dict):
                configured_models = []
                for tier_name, model_list in models_data.items():
                    try:
                        tier = ModelTier(tier_name.lower())
                        for model_id in model_list:
                            try:
                                model = get_model_by_id(model_id)
                                configured_models.append(model)
                            except ValueError:
                                self.logger.warning(f"Unknown model ID: {model_id}, skipping")
                    except ValueError:
                        self.logger.warning(f"Unknown tier: {tier_name}, skipping")
                config_data["models"] = configured_models
        else:
            # 默认所有模型
            config_data["models"] = get_all_models()

        # 确保默认模型在可用模型列表中
        default_models = [
            config_data.get("default_free_model"),
            config_data.get("default_standard_model"),
            config_data.get("default_premium_model")
        ]
        available_model_ids = [m.id for m in config_data["models"]]

        for default_id in default_models:
            if default_id and default_id not in available_model_ids:
                self.logger.warning(f"Default model {default_id} not in models list, will be added")
                try:
                    model = get_model_by_id(default_id)
                    config_data["models"].append(model)
                except ValueError:
                    pass

        return RouterConfig.from_dict(config_data)

    def reload_config(self):
        """热重载配置"""
        self.logger.info("Reloading configuration...")
        old_config = self._config
        new_config = self._load_config()

        # 配置对比日志
        if old_config:
            changes = []
            for key in ["auto_upgrade_enabled", "upgrade_threshold", "log_level"]:
                old_val = getattr(old_config, key)
                new_val = getattr(new_config, key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} -> {new_val}")

            if changes:
                self.logger.info(f"Configuration changes: {', '.join(changes)}")
            else:
                self.logger.info("No configuration changes detected")

        return new_config

    def get_config(self) -> RouterConfig:
        """获取当前配置（线程安全）"""
        with self._lock:
            return self._config

    def update_config(self, updates: dict[str, Any]):
        """动态更新配置（不会持久化到文件）"""
        with self._lock:
            current_dict = self._config.to_dict()
            current_dict.update(updates)
            self._config = self._build_config_from_dict(current_dict)
            self.logger.info(f"Configuration updated with {len(updates)} changes")

    def save_config(self):
        """保存当前配置到文件"""
        with self._lock:
            try:
                config_dict = self._config.to_dict()

                # 转换枚举为字符串
                if "models" in config_dict:
                    config_dict["models"] = [m.id for m in self._config.models]

                with open(self.config_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        config_dict,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False
                    )

                self.logger.info(f"Configuration saved to {self.config_path}")
            except Exception as e:
                self.logger.error(f"Failed to save config: {e}")

    def _start_watching(self):
        """启动文件监视"""
        try:
            observer = Observer()
            handler = ConfigChangeHandler(self)
            observer.schedule(handler, self.config_path, recursive=False)
            observer.start()
            self._observers.append(observer)
            self.logger.info(f"Started watching config file: {self.config_path}")
        except Exception as e:
            self.logger.warning(f"Failed to start config watcher: {e}")

    def stop_watching(self):
        """停止文件监视"""
        for observer in self._observers:
            observer.stop()
        for observer in self._observers:
            observer.join(timeout=2)
        self._observers.clear()
        self.logger.info("Stopped config watcher")

    def __del__(self):
        """清理资源"""
        self.stop_watching()


def load_config_from_file(config_path: str) -> RouterConfig:
    """从文件加载配置（一次性）"""
    loader = ConfigLoader(config_path, auto_reload=False)
    return loader.get_config()


def get_default_config() -> RouterConfig:
    """获取默认配置"""
    return RouterConfig()
