# Hermes Agent Enhanced -- API Reference

> Auto-generated: 2026-06-15 16:24:04
> Version: v0.17.0 (Round 11)

---

## Table of Contents

- [actor_base](#actor_base)
- [synapse_bus](#synapse_bus)
- [loop_engine](#loop_engine)
- [loop_checkpoint](#loop_checkpoint)
- [resilience_patterns](#resilience_patterns)
- [memory_federation](#memory_federation)
- [hermes_utils](#hermes_utils)
- [hermes_skill_evolver](#hermes_skill_evolver)
- [hermes_self_evolve_cluster](#hermes_self_evolve_cluster)
- [product_evolve](#product_evolve)
- [production_chain_v2](#production_chain_v2)
- [fabric_heartbeat](#fabric_heartbeat)
- [unified_collector](#unified_collector)
- [monitoring___init__](#monitoring___init__)
- [monitoring_telemetry](#monitoring_telemetry)
- [monitoring_health](#monitoring_health)
- [monitoring_metrics](#monitoring_metrics)
- [monitoring_alerts](#monitoring_alerts)
- [monitoring_dashboard](#monitoring_dashboard)

---

## monitoring___init__

**File:** `monitoring/__init__.py`

>Hermes Monitoring & Diagnostics Package

### `def initialize_monitoring(...)`
  - `config_path`: str
  - Returns: `tuple[Optional['HermesTelemetry'], Optional['HermesMetrics'], Optional['HealthChecker'], Any | None]`
  Initialize the complete monitoring stack.

## monitoring_alerts

**File:** `monitoring/alerts.py`

>Alerting System for Hermes

### `class AlertSeverity`
*Inherits from: Enum*

  Alert severity levels.

### `class AlertStatus`
*Inherits from: Enum*

  Alert status.

### `class Alert`

  Alert definition.

### `class AlertInstance`

  Active alert instance.

### `class Notification`

  Alert notification.

### `class AlertRuleEngine`

  Evaluates alert conditions and manages alert lifecycle.

#### `__init__(...)`
  - `self`
  - `metrics_manager`
  - `health_checker`

#### `register_alert(...)`
  - `self`
  - `alert`: Alert
  Register a new alert rule.

#### `unregister_alert(...)`
  - `self`
  - `alert_id`: str
  Unregister an alert rule.

#### `evaluate_all(...)`
  - `self`
  - Returns: `list[AlertInstance]`
  Evaluate all alert rules.

#### `acknowledge_alert(...)`
  - `self`
  - `alert_id`: str
  - `user`: str
  Acknowledge an active alert.

#### `silence_alert(...)`
  - `self`
  - `alert_id`: str
  - `duration`: int
  Silence an alert for specified duration.

#### `get_active_alerts(...)`
  - `self`
  - Returns: `list[AlertInstance]`
  Get all active (firing) alerts.

#### `get_alert_history(...)`
  - `self`
  - `hours`: int
  - Returns: `list[dict]`
  Get alert history (would typically come from persistent storage).

### `class NotificationManager`

  Manages alert notifications across channels.

#### `__init__(...)`
  - `self`

#### `send_notification(...)`
  - `self`
  - `alert_instance`: AlertInstance
  - `channels`: list[str]
  Send alert notification through specified channels.

### `def initialize_alerts(...)`
  - `metrics_manager`
  - `health_checker`
  Initialize alerting system.

### `def start_alert_evaluation(...)`
  - `interval`: int
  Start background alert evaluation.

## monitoring_dashboard

**File:** `monitoring/dashboard.py`

>Web Dashboard for Hermes Monitoring

### `class DashboardMetrics`

  Snapshot of dashboard metrics.

### `class ConnectionManager`

  Manages WebSocket connections for real-time updates.

#### `__init__(...)`
  - `self`

#### `connect(...)`
  - `self`
  - `websocket`: WebSocket

#### `disconnect(...)`
  - `self`
  - `websocket`: WebSocket

#### `broadcast(...)`
  - `self`
  - `message`: dict
  Broadcast message to all connected clients.

### `class HermesDashboard`

  Web dashboard for Hermes monitoring.
  Serves at http://localhost:3000 by default.

#### `__init__(...)`
  - `self`
  - `metrics_manager`
  - `health_checker`
  - `alert_manager`
  - `host`: str
  - `port`: int

#### `start(...)`
  - `self`
  Start dashboard server in background thread.

#### `stop(...)`
  - `self`
  Stop dashboard server.

### `def start_dashboard(...)`
  - `metrics`
  - `health`
  - `alerts`
  - `port`: int
  Convenience function to start dashboard.

## monitoring_health

**File:** `monitoring/health.py`

>Health Check System for Hermes

### `class ComponentStatus`
*Inherits from: Enum*

  Component health status.

### `class HealthCheckResult`

  Result of a health check.

#### `to_dict(...)`
  - `self`

### `class DependencyHealth`

  Health of a dependent service.

### `class HealthChecker`

  Central health check coordinator.
  Manages component checks, dependency tracking, and automatic recovery.

#### `__init__(...)`
  - `self`

#### `register_check(...)`
  - `self`
  - `name`: str
  - `check_func`: Callable[[], HealthCheckResult]
  Register a custom health check.

#### `register_dependency(...)`
  - `self`
  - `name`: str
  - `check_func`: Callable[[], bool]
  - `config`: dict
  Register an external dependency to monitor.

#### `add_listener(...)`
  - `self`
  - `listener`: Callable[[dict], None]
  Add a listener for health status changes.

#### `check_all(...)`
  - `self`
  - Returns: `list[HealthCheckResult]`
  Run all registered health checks.

#### `get_overall_status(...)`
  - `self`
  - `results`: list[HealthCheckResult]
  - Returns: `ComponentStatus`
  Calculate overall health status from results.

#### `start_monitoring(...)`
  - `self`
  Start the background health monitoring thread.

#### `stop_monitoring(...)`
  - `self`
  Stop background health monitoring.

#### `get_health_endpoint_response(...)`
  - `self`
  - Returns: `dict[str, Any]`
  Generate response for /health endpoints.

### `def start_health_monitoring(...)`
  Start the health monitoring system.

### `def stop_health_monitoring(...)`
  Stop the health monitoring system.

## monitoring_metrics

**File:** `monitoring/metrics.py`

>Metrics Collection System for Hermes

### `class MetricType`
*Inherits from: Enum*

  Metric types.

### `class MetricDefinition`

  Definition of a metric.

### `class HermesMetrics`

  Central metrics manager for Hermes.
  Provides Prometheus-compatible metrics and custom business metrics.

#### `__init__(...)`
  - `self`

#### `instance(...)`
  - `cls`
  - Returns: `'HermesMetrics'`
  Singleton pattern.

#### `register_counter(...)`
  - `self`
  - `name`: str
  - `description`: str
  - `labels`: list[str]
  - `unit`: str
  Register a counter metric.

#### `register_gauge(...)`
  - `self`
  - `name`: str
  - `description`: str
  - `labels`: list[str]
  - `unit`: str
  Register a gauge metric.

#### `register_histogram(...)`
  - `self`
  - `name`: str
  - `description`: str
  - `bucket_bounds`: list[float]
  - `labels`: list[str]
  - `unit`: str
  Register a histogram metric.

#### `register_summary(...)`
  - `self`
  - `name`: str
  - `description`: str
  - `max_age_seconds`: int
  - `labels`: list[str]
  Register a summary metric.

#### `increment_counter(...)`
  - `self`
  - `name`: str
  - `value`: int
  - `labels`: dict[str, str]
  Increment a counter.

#### `set_gauge(...)`
  - `self`
  - `name`: str
  - `value`: float
  - `labels`: dict[str, str]
  Set a gauge value.

#### `record_histogram(...)`
  - `self`
  - `name`: str
  - `value`: float
  - `labels`: dict[str, str]
  Record a histogram observation.

#### `record_request(...)`
  - `self`
  - `endpoint`: str
  - `method`: str
  - `status`: int
  - `duration_seconds`: float
  Record an HTTP request.

#### `record_error(...)`
  - `self`
  - `component`: str
  - `error_type`: str
  - `severity`: str
  Record an error.

#### `record_task_completion(...)`
  - `self`
  - `task_type`: str
  - `status`: str
  - `duration_seconds`: float
  Record task execution.

#### `record_memory_retrieval(...)`
  - `self`
  - `query_type`: str
  - `hit`: bool
  - `duration_seconds`: float
  Record memory retrieval.

#### `record_tool_call(...)`
  - `self`
  - `tool_name`: str
  - `status`: str
  - `duration_seconds`: float
  Record tool execution.

#### `record_model_request(...)`
  - `self`
  - `model`: str
  - `provider`: str
  - `streaming`: bool
  - `latency_seconds`: float
  - `input_tokens`: int
  - `output_tokens`: int
  Record model API request.

#### `update_concurrent_requests(...)`
  - `self`
  - `delta`: int
  Update active request count.

#### `update_system_metrics(...)`
  - `self`
  Update system resource metrics.

#### `generate_prometheus_output(...)`
  - `self`
  - Returns: `str`
  Generate metrics in Prometheus text format.

### `class RequestTimer`

  Context manager for timing operations.

#### `__init__(...)`
  - `self`
  - `metric_name`: str

### `class ActiveRequestCounter`

  Context manager for tracking concurrent requests.

#### `__init__(...)`
  - `self`

### `def track_request(...)`
  - `endpoint`: str
  - `method`: str
  Decorator to track HTTP requests.

### `def track_task(...)`
  - `task_type`: str
  Decorator to track task execution.

### `def track_tool(...)`
  - `tool_name`: str
  Decorator to track tool execution.

### `def start_system_metrics_collection(...)`
  - `interval`: int
  Start background thread to update system metrics.

## monitoring_telemetry

**File:** `monitoring/telemetry.py`

>OpenTelemetry Integration for Hermes Monitoring & Diagnostics

### `class HermesTelemetry`

  Main telemetry manager for Hermes.
  Handles OpenTelemetry setup, sampling, context propagation, and exporters.

#### `__init__(...)`
  - `self`
  - `config_path`: str

#### `instance(...)`
  - `cls`
  - `config_path`: str
  - Returns: `'HermesTelemetry'`
  Singleton pattern - get or create the telemetry instance.

#### `tracer(...)`
  - `self`
  - Returns: `Tracer`
  Get the tracer instance.

#### `meter(...)`
  - `self`
  - Returns: `Meter`
  Get the meter instance.

#### `start(...)`
  - `self`
  Start telemetry collection.

#### `shutdown(...)`
  - `self`
  Shutdown telemetry and flush pending data.

### `class TracedContext`

  Context manager for manual span creation and instrumentation.

#### `__init__(...)`
  - `self`
  - `name`: str
  - `attributes`: dict[str, Any]

### `def trace_function(...)`
  - `name`: str
  - `attributes`: dict[str, Any]
  Decorator to automatically trace function execution.

### `def trace_async_function(...)`
  - `name`: str
  - `attributes`: dict[str, Any]
  Decorator for async function tracing.

### `def inject_context(...)`
  - `headers`: dict[str, str]
  - Returns: `None`
  Inject trace context into headers for outbound requests.

### `def extract_context(...)`
  - `headers`: dict[str, str]
  - Returns: `None`
  Extract trace context from inbound headers.

### `def instrument_hermes_core(...)`
  Apply automatic instrumentation to Hermes core components.

## actor_base

**File:** `scripts/actor_base.py`

>Hermes Actor 基类 — 三省六部制的角色单元

### `class ActorStatus`
*Inherits from: Enum*

  Actor 生命周期状态

### `class ActorPriority`
*Inherits from: Enum*

  Actor 优先级

### `class ActorMetrics`

  Actor 性能指标

#### `record_call(...)`
  - `self`
  - `duration_ms`: float
  - `success`: bool
  - `error`: Optional[str]

#### `success_rate(...)`
  - `self`
  - Returns: `float`

#### `is_degraded(...)`
  - `self`
  - Returns: `bool`

#### `is_critical(...)`
  - `self`
  - Returns: `bool`

### `class StateBox`

  Actor 的隔离状态容器。
  每个 Actor 实例独有，不共享。

#### `get(...)`
  - `self`
  - `key`: str
  - `default`: Any
  - Returns: `Any`

#### `set(...)`
  - `self`
  - `key`: str
  - `value`: Any

#### `delete(...)`
  - `self`
  - `key`: str

#### `clear(...)`
  - `self`

#### `snapshot(...)`
  - `self`
  - Returns: `Dict[str, Any]`
  返回状态快照（深拷贝）

### `class Event`

  事件类型 — SynapseBus 中的基本通信单元

### `class HealthProbe`

  健康探针 — 定期检测 Actor 是否可用

#### `__init__(...)`
  - `self`
  - `check_fn`: Optional[Callable]
  - `interval`: int

#### `check(...)`
  - `self`
  - Returns: `bool`
  执行健康检查

#### `is_healthy(...)`
  - `self`
  - Returns: `bool`

### `class Actor`

  Hermes Actor 基类。
  
  所有 Agent/Skill/Tool 都可以包装为 Actor，注册到 SynapseBus。
  
  用法:
      class MySkillActor(Actor):
          def __init__(self):
              super().__init__("my-skill", ["data.fetch", "text.analyze"])
          
          def handle(self, event) -> Any:
              # 处理事件
              return result
      
      actor = MySkillActor()
      bus.register_actor(actor, ["data.fetch", "text.analyze"])

#### `__init__(...)`
  - `self`
  - `actor_id`: str
  - `name`: str
  - `capabilities`: List[str]
  - `description`: str
  - `priority`: ActorPriority
  - `tools`: List[str]
  - `max_concurrent`: int

#### `can_handle(...)`
  - `self`
  - `task_type`: str
  - Returns: `bool`
  检查是否能处理该类型任务

#### `handle(...)`
  - `self`
  - `event`: Event
  - Returns: `Any`
  处理事件 — 子类必须实现此方法。

#### `handle_with_metrics(...)`
  - `self`
  - `event`: Event
  - Returns: `Any`
  带性能指标的事件处理包装

#### `get_capabilities(...)`
  - `self`
  - Returns: `Set[str]`
  获取能力列表

#### `add_capability(...)`
  - `self`
  - `cap`: str
  添加能力标签

#### `remove_capability(...)`
  - `self`
  - `cap`: str
  移除能力标签

#### `suspend(...)`
  - `self`
  挂起 Actor（释放内存）

#### `resume(...)`
  - `self`
  恢复 Actor

#### `retire(...)`
  - `self`
  退役 Actor

#### `health_check(...)`
  - `self`
  - Returns: `bool`
  健康检查

#### `to_dict(...)`
  - `self`
  - Returns: `Dict[str, Any]`
  序列化 Actor 状态

### `class SkillActor`
*Inherits from: Actor*

  包装单个 skill 为 Actor

#### `__init__(...)`
  - `self`
  - `skill_name`: str
  - `skill_description`: str
  - `capabilities`: List[str]

#### `handle(...)`
  - `self`
  - `event`: Event
  - Returns: `Any`

### `class ToolActor`
*Inherits from: Actor*

  包装 Hermes 工具为 Actor

#### `__init__(...)`
  - `self`
  - `tool_name`: str
  - `capabilities`: List[str]

### `class AgentActor`
*Inherits from: Actor*

  包装整个 Agent 为 Actor

#### `__init__(...)`
  - `self`
  - `agent_id`: str
  - `model`: str
  - `capabilities`: List[str]
  - `memory_ref`: str

### `class PipelineActor`
*Inherits from: Actor*

  包装工作流为 Actor

#### `__init__(...)`
  - `self`
  - `pipeline_id`: str
  - `steps`: List[Dict]
  - `capabilities`: List[str]

## fabric_heartbeat

**File:** `scripts/fabric_heartbeat.py`

>Reflex Fabric 心跳维护脚本 — 直接连接 state.db,绕过 agents_company import 链

### `def main(...)`

## hermes_self_evolve_cluster

**File:** `scripts/hermes_self_evolve_cluster.py`

>Hermes 自进化集群 — 凌晨3点全自动执行

### `def log(...)`
  - `msg`: str

### `def log_section(...)`
  - `title`: str

### `def skill_evolution(...)`
  - Returns: `dict[str, Any]`
  技能自动进化 - 分析,合并,挖掘,生成

### `def memory_compress(...)`
  - Returns: `dict[str, Any]`
  记忆压缩 - 清理MEMORY.md过时记录,迁移到active_memory.db历史

### `def token_compress(...)`
  - Returns: `dict[str, Any]`
  对话Tokens压缩 - 压缩旧会话, 维护摘要索引

### `def consume_retro_candidates(...)`
  - Returns: `dict[str, Any]`
  消费复盘候选队列 — 复盘→Skill进化管道（非LLM版）

### `def skill_evolution_engine(...)`
  - Returns: `dict[str, Any]`
  证据驱动Skill进化 — 全流程（收集→分类→提案→报告）

### `def auto_tune_engine(...)`
  - Returns: `dict[str, Any]`
  自动调优引擎 — 参数自适应

### `def capability_evolve(...)`
  - Returns: `dict[str, Any]`
  能力自主进化 - 扫描Cron/DB/系统,调优参数,生成优化建议

### `def sango_evolve(...)`
  - Returns: `dict[str, Any]`
  三省六部自进化 - 更新拓扑权重,记录进化日志

### `def main(...)`

## hermes_skill_evolver

**File:** `scripts/hermes_skill_evolver.py`

>Hermes 证据驱动Skill进化引擎 v1.0

### `class EvidenceCollector`

  证据收集器 — 从state.db和复盘队列中收集

#### `collect_from_retrospectives(...)`
  - `self`
  - `max_days`: int
  - Returns: `list[dict]`
  从state.db的retrospectives表收集证据

#### `collect_from_candidates(...)`
  - `self`
  - Returns: `list[dict]`
  从复盘候选队列(retro_candidates.jsonl)收集证据

#### `collect_all(...)`
  - `self`
  - Returns: `list[dict]`
  一站式收集所有证据

### `class SkillProposalGenerator`

  Skill改进提案生成器 — 生成+评分+选优

#### `__init__(...)`
  - `self`

#### `generate_proposals(...)`
  - `self`
  - `candidates`: list[dict]
  - Returns: `list[dict]`
  为每个候选生成改进提案

#### `select_best(...)`
  - `self`
  - Returns: `dict | None`
  选出最优提案

### `class GuardedApplier`

  受保护Skill应用器 — SHA256校验→备份→结构检查→验证→回滚

#### `sha256_file(...)`
  - `path`: Path
  - Returns: `str`
  计算文件SHA256

#### `backup_skill(...)`
  - `skill_name`: str
  - Returns: `Path | None`
  在修改前备份SKILL.md

#### `apply_proposal(...)`
  - `skill_name`: str
  - `content`: str
  - Returns: `bool`
  安全应用提案（结构检查后写入）

### `def log(...)`
  - `msg`: str

### `def classify_evidence(...)`
  - `record`: dict
  - Returns: `str`
  将证据分类为 skill_update / skill_new / replay_benchmark / ignore

### `def mine_candidates(...)`
  - `evidence`: list[dict]
  - Returns: `list[dict]`
  分类所有证据并生成候选列表

### `def cmd_collect(...)`
  收集证据

### `def cmd_classify(...)`
  分类证据

### `def cmd_evolve(...)`
  生成+应用Skill改进

### `def cmd_all(...)`
  一站式全流程

### `def main(...)`

## hermes_utils

**File:** `scripts/hermes_utils.py`

>Hermes Utils -- 公共工具函数库

### `class ErrorMessages`

  统一错误消息，提供可操作的修复建议。

### `def get_hermes_logger(...)`
  - `name`: str
  - `log_dir`: str
  - Returns: `logging.Logger`
  获取或创建 Hermes 日志记录器（带缓存）。

### `def safe_to_dict(...)`
  - `obj`: Any
  - `recursive`: bool
  - Returns: `Any`
  安全地将对象转换为字典，处理 dataclass、Enum、datetime 等。

### `def populate_dataclass(...)`
  - `cls`: type[T]
  - `data`: Dict[str, Any]
  - Returns: `T`
  从字典填充 dataclass 实例，忽略多余字段。

### `def init_sqlite_db(...)`
  - `db_path`: str
  - `schema_sql`: Union[str, List[str]]
  - `logger`: logging.Logger
  - Returns: `bool`
  统一 SQLite 数据库初始化 -- 替代 8 处重复的 _init_db()。

### `def safe_sqlite_execute(...)`
  - `db_path`: str
  - `sql`: str
  - `params`: tuple
  - `fetch`: str
  - `write`: bool
  - Returns: `Any`
  安全执行 SQLite 操作。

### `def safe_json_read(...)`
  - `path`: str
  - `default`: Any
  - Returns: `Any`
  安全读取 JSON 文件。

### `def safe_json_write(...)`
  - `path`: str
  - `data`: Any
  - `indent`: int
  - Returns: `bool`
  安全写入 JSON 文件（原子写入）。

### `def ensure_dir(...)`
  - `path`: str
  - Returns: `str`
  确保目录存在。

### `def hash_content(...)`
  - `content`: str
  - `algorithm`: str
  - Returns: `str`
  计算内容哈希。

### `def retry_call(...)`
  - `func`: Callable
  - `max_attempts`: int
  - `base_delay`: float
  - `max_delay`: float
  - `exponential`: bool
  - `exceptions`: tuple
  - `logger`: logging.Logger
  - Returns: `Any`
  通用重试调用。

### `def utc_now(...)`
  - Returns: `datetime`
  返回当前的 UTC datetime。

### `def utc_now_iso(...)`
  - Returns: `str`
  返回当前的 UTC ISO 时间字符串。

### `def timestamp_ms(...)`
  - Returns: `int`
  返回当前 Unix 时间戳（毫秒）。

### `def safe_import(...)`
  - `module_name`: str
  - `fallback`: Any
  - `logger`: logging.Logger
  安全导入模块。

### `def truncate(...)`
  - `s`: str
  - `max_len`: int
  - `suffix`: str
  - Returns: `str`
  截断字符串。

### `def format_duration(...)`
  - `seconds`: float
  - Returns: `str`
  格式化持续时间。

## loop_checkpoint

**File:** `scripts/loop_checkpoint.py`

>Loop Checkpoint & Memory — Hermes Loop Engineering 检查点与记忆

### `class CheckpointEntry`

  单个检查点条目

#### `compute_checksum(...)`
  - `self`
  - Returns: `str`
  计算状态哈希用于完整性校验

#### `validate(...)`
  - `self`
  - Returns: `bool`
  验证检查点完整性

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

#### `from_dict(...)`
  - `cls`
  - `data`: dict
  - Returns: `'CheckpointEntry'`

### `class ActionRecord`

  操作记录 — 记录做了什么

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

#### `from_dict(...)`
  - `cls`
  - `data`: dict
  - Returns: `'ActionRecord'`

### `class ProgressReport`

  进度报告

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

#### `format_text(...)`
  - `self`
  - Returns: `str`
  生成人类可读的文本报告

### `class CheckpointStore`

  检查点存储 — 支持 JSON 文件和 SQLite 双模式
  
  JSON:   ~/.hermes/state/checkpoints/<loop_id>/<checkpoint_id>.json
  SQLite: ~/.hermes/state/checkpoints.db

#### `__init__(...)`
  - `self`
  - `base_dir`: str
  - `db_path`: str
  - `actions_db`: str
  - `max_checkpoints`: int
  - `retention_days`: int

#### `save_checkpoint(...)`
  - `self`
  - `entry`: CheckpointEntry
  - Returns: `str`
  保存检查点到 JSON 文件和 SQLite

#### `load_latest_checkpoint(...)`
  - `self`
  - `loop_id`: str
  - `session_id`: str
  - Returns: `Optional[CheckpointEntry]`
  加载最新检查点

#### `load_checkpoint_by_id(...)`
  - `self`
  - `checkpoint_id`: str
  - Returns: `Optional[CheckpointEntry]`
  按 ID 加载检查点

#### `list_checkpoints(...)`
  - `self`
  - `loop_id`: str
  - `session_id`: str
  - `limit`: int
  - Returns: `List[dict]`
  列出检查点

#### `record_action(...)`
  - `self`
  - `record`: ActionRecord
  - Returns: `str`
  记录操作

#### `get_actions(...)`
  - `self`
  - `session_id`: str
  - `limit`: int
  - Returns: `List[ActionRecord]`
  获取会话的操作记录

#### `get_failed_actions(...)`
  - `self`
  - `session_id`: str
  - Returns: `List[ActionRecord]`
  获取失败的操作记录

#### `record_human_required(...)`
  - `self`
  - `session_id`: str
  - `node_id`: str
  - `description`: str
  - `req_type`: str
  - Returns: `int`
  记录需要人工处理的事项

#### `resolve_human_required(...)`
  - `self`
  - `interaction_id`: int
  - `response`: str
  标记人工事项已解决

#### `get_pending_human(...)`
  - `self`
  - `session_id`: str
  - Returns: `List[dict]`
  获取待处理的人工事项

### `class LoopRecoveryEngine`

  Loop 恢复引擎 — 从检查点恢复中断的 loop
  
  恢复流程:
    1. 加载最新检查点
    2. 验证检查点完整性
    3. 分析已完成/失败/待处理节点
    4. 重建执行上下文
    5. 从未完成节点继续执行

#### `__init__(...)`
  - `self`
  - `checkpoint_store`: CheckpointStore

#### `can_recover(...)`
  - `self`
  - `loop_id`: str
  - `session_id`: str
  - Returns: `Tuple[bool, str]`
  检查是否可以从检查点恢复

#### `get_recovery_state(...)`
  - `self`
  - `loop_id`: str
  - `session_id`: str
  - Returns: `Optional[dict]`
  获取恢复状态 — 返回需要继续执行的上下文

#### `build_recovery_plan(...)`
  - `self`
  - `loop_id`: str
  - `session_id`: str
  - Returns: `Optional[dict]`
  生成恢复执行计划

### `class ProgressReporter`

  进度报告生成器 — 生成人类可读的进度摘要

#### `__init__(...)`
  - `self`
  - `checkpoint_store`: CheckpointStore

#### `generate_report(...)`
  - `self`
  - `loop_id`: str
  - `loop_name`: str
  - `session_id`: str
  - Returns: `ProgressReport`
  生成完整进度报告

#### `generate_session_summary(...)`
  - `self`
  - `session_id`: str
  - Returns: `str`
  生成纯文本会话摘要

### `def create_checkpoint_entry(...)`
  - `loop_id`: str
  - `session_id`: str
  - `checkpoint_type`: str
  - `completed_nodes`: List[str]
  - `failed_nodes`: List[dict]
  - `pending_nodes`: List[str]
  - `current_node_id`: str
  - `overall_progress`: float
  - `turn_count`: int
  - `elapsed_seconds`: float
  - `human_required`: List[dict]
  - Returns: `CheckpointEntry`
  快速创建检查点条目

### `def create_action_record(...)`
  - `session_id`: str
  - `node_id`: str
  - `action_type`: str
  - `action_name`: str
  - `success`: bool
  - Returns: `ActionRecord`
  快速创建操作记录

### `def main(...)`

## loop_engine

**File:** `scripts/loop_engine.py`

>Loop Engine — Hermes Loop Engineering 执行引擎

### `class LoopPhase`
*Inherits from: str, Enum*

  Loop 生命周期阶段

### `class TriggerType`
*Inherits from: str, Enum*

  触发类型

### `class TokenBudget`

  Token 预算追踪

#### `total_cost(...)`
  - `self`
  - Returns: `float`

#### `budget_exceeded(...)`
  - `self`
  - Returns: `bool`

#### `consume(...)`
  - `self`
  - `input_tokens`: int
  - `output_tokens`: int

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

### `class TaskNode`

  任务图中的单个节点

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

### `class TaskEdge`

  任务图边

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

### `class TaskGraph`

  任务 DAG 图

#### `get_node(...)`
  - `self`
  - `node_id`: str
  - Returns: `Optional[TaskNode]`

#### `get_dependencies(...)`
  - `self`
  - `node_id`: str
  - Returns: `List[str]`

#### `get_dependents(...)`
  - `self`
  - `node_id`: str
  - Returns: `List[str]`

#### `topological_sort(...)`
  - `self`
  - Returns: `List[str]`
  拓扑排序，返回执行顺序

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

#### `from_dict(...)`
  - `cls`
  - `data`: dict
  - Returns: `'TaskGraph'`

### `class TriggerConfig`

  触发器配置

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

#### `from_dict(...)`
  - `cls`
  - `data`: dict
  - Returns: `'TriggerConfig'`

### `class VerificationRule`

  验证规则定义

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

### `class LoopDefinition`

  Loop 完整定义

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

#### `from_dict(...)`
  - `cls`
  - `data`: dict
  - Returns: `'LoopDefinition'`

### `class ExecutionContext`

  子任务执行上下文

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

### `class ExecutionSandbox`

  执行沙箱 — 为每个子任务提供隔离的临时目录/worktree

#### `__init__(...)`
  - `self`
  - `base_temp_dir`: str
  - `use_worktree`: bool
  - `repo_path`: str

#### `create_context(...)`
  - `self`
  - `loop_id`: str
  - `node_id`: str
  - Returns: `ExecutionContext`
  为子任务创建隔离执行上下文

#### `cleanup_context(...)`
  - `self`
  - `session_id`: str
  清理隔离上下文

#### `cleanup_all(...)`
  - `self`

### `class TriggerWatcher`

  触发器监视器 — 管理不同触发源

#### `__init__(...)`
  - `self`

#### `setup_trigger(...)`
  - `self`
  - `loop_def`: LoopDefinition
  - `callback`: Callable
  - Returns: `bool`
  根据 Loop 定义设置触发器

#### `check_file_watch(...)`
  - `self`
  - Returns: `List[str]`
  检查文件变更，返回触发的 loop_id 列表

#### `stop_all(...)`
  - `self`
  停止所有触发器

#### `get_cron_expression(...)`
  - `self`
  - `loop_id`: str
  - Returns: `Optional[str]`
  获取 cron 表达式

### `class LoopExecutionResult`

  Loop 执行结果

#### `to_dict(...)`
  - `self`
  - Returns: `dict`

### `class LoopEngine`

  Loop 执行引擎 — Loop Engineering 核心。
  
  管理 Loop 的完整生命周期：wake → plan → execute → verify → record → sleep。
  
  支持回调注册实现可扩展性：
    - on_node_execute: 节点执行逻辑
    - on_node_verify: 节点验证逻辑
    - on_wake/plan/record/sleep/error: 各阶段钩子
  
  Attributes:
      registered_loops: 已注册的 Loop 定义字典。
      trigger_watcher: 触发器监视器。
      sandbox: 执行沙箱（隔离环境）。
      DB_PATH: 默认数据库路径。
  
  Example:
      >>> engine = LoopEngine()
      >>> engine.register_loop(loop_def)
      >>> result = await engine.run_loop("my_loop_id")

#### `__init__(...)`
  - `self`
  - `db_path`: str

#### `on_wake(...)`
  - `self`
  - `fn`: Callable

#### `on_plan(...)`
  - `self`
  - `fn`: Callable

#### `on_node_execute(...)`
  - `self`
  - `fn`: Callable
  注册节点执行回调: (ExecutionContext, TaskNode) -> dict

#### `on_node_verify(...)`
  - `self`
  - `fn`: Callable
  注册节点验证回调: (ExecutionContext, TaskNode, dict) -> bool

#### `on_record(...)`
  - `self`
  - `fn`: Callable

#### `on_sleep(...)`
  - `self`
  - `fn`: Callable

#### `on_error(...)`
  - `self`
  - `fn`: Callable

#### `register_loop(...)`
  - `self`
  - `loop_def`: Union[LoopDefinition, dict]
  注册 Loop 定义并设置触发器。

#### `unregister_loop(...)`
  - `self`
  - `loop_id`: str
  注销 Loop

#### `get_loop(...)`
  - `self`
  - `loop_id`: str
  - Returns: `Optional[LoopDefinition]`

#### `list_loops(...)`
  - `self`
  - Returns: `List[dict]`

#### `load_loops_from_db(...)`
  - `self`
  从数据库加载所有 Loop 定义

#### `run_loop(...)`
  - `self`
  - `loop_id`: str
  - `trigger_reason`: str
  - Returns: `LoopExecutionResult`
  完整执行一个 Loop — wake → plan → execute → verify → record → sleep。

#### `run_parallel(...)`
  - `self`
  - `loop_ids`: List[str]
  - `max_concurrent`: int
  - Returns: `Dict[str, LoopExecutionResult]`
  并行执行多个 Loop

#### `poll_file_watchers(...)`
  - `self`
  轮询文件监听器，触发相应的 Loop

#### `get_execution_history(...)`
  - `self`
  - `loop_id`: str
  - `limit`: int
  - Returns: `List[dict]`

#### `get_loop_events(...)`
  - `self`
  - `session_id`: str
  - Returns: `List[dict]`

#### `get_active_sessions(...)`
  - `self`
  - Returns: `Dict[str, str]`

#### `shutdown(...)`
  - `self`
  关闭引擎，清理资源

### `def create_loop(...)`
  - `name`: str
  - `trigger_type`: str
  - `cron_expression`: str
  - `nodes`: List[dict]
  - `edges`: List[dict]
  - `verification_rules`: List[dict]
  - `budget_cap`: int
  - `max_parallel`: int
  - Returns: `LoopDefinition`
  快速创建 Loop 定义的工厂函数。

### `def main(...)`
  CLI 入口 — 测试和手动触发

## memory_federation

**File:** `scripts/memory_federation.py`

>Memory Federation Protocol — 统一记忆访问层

### `class MemoryQuery`

  统一记忆查询

### `class MemoryItem`

  单一记忆条目

#### `to_dict(...)`
  - `self`
  - Returns: `Dict`

### `class MemoryResult`

  统一记忆响应

#### `to_dict(...)`
  - `self`
  - Returns: `Dict`

### `class MemoryData`

  写入记忆的数据

### `class MemoryAdapter`

  记忆适配器基类

#### `read(...)`
  - `self`
  - `query`: MemoryQuery
  - Returns: `MemoryResult`
  读取记忆

#### `write(...)`
  - `self`
  - `data`: MemoryData
  - Returns: `bool`
  写入记忆

#### `search(...)`
  - `self`
  - `text`: str
  - `limit`: int
  - Returns: `List[MemoryItem]`
  快捷搜索

#### `health(...)`
  - `self`
  - Returns: `bool`
  健康检查

### `class FTS5Adapter`
*Inherits from: MemoryAdapter*

  FTS5 全文搜索 — state.db 的消息全文索引

#### `__init__(...)`
  - `self`
  - `db_path`: str

#### `write(...)`
  - `self`
  - `data`: MemoryData
  - Returns: `bool`

#### `read(...)`
  - `self`
  - `query`: MemoryQuery
  - Returns: `MemoryResult`

### `class ActiveMemoryAdapter`
*Inherits from: MemoryAdapter*

  Active Memory 偏好引擎 — active_memory.py

#### `__init__(...)`
  - `self`

#### `read(...)`
  - `self`
  - `query`: MemoryQuery
  - Returns: `MemoryResult`

### `class IntelligenceAdapter`
*Inherits from: MemoryAdapter*

  intelligence.db 高价值情报作为记忆

#### `__init__(...)`
  - `self`

#### `write(...)`
  - `self`
  - `data`: MemoryData
  - Returns: `bool`

#### `read(...)`
  - `self`
  - `query`: MemoryQuery
  - Returns: `MemoryResult`

### `class RAGMemoryAdapter`
*Inherits from: MemoryAdapter*

  RAG 向量记忆 — main.sqlite vec0 索引

#### `__init__(...)`
  - `self`

#### `write(...)`
  - `self`
  - `data`: MemoryData
  - Returns: `bool`

#### `read(...)`
  - `self`
  - `query`: MemoryQuery
  - Returns: `MemoryResult`

### `class MemoryFederation`

  Memory Federation — 统一记忆访问入口。
  
  用法:
      mf = MemoryFederation()
      
      # 单源查询
      result = mf.query("Python异步编程", query_type="search")
      
      # 全源查询
      result = mf.query("我的偏好设置", query_type="all")
      
      # 写入记忆
      mf.remember("用户喜欢Rust语言")

#### `__init__(...)`
  - `self`
  - `max_workers`: int

#### `register(...)`
  - `self`
  - `adapter`: MemoryAdapter
  注册适配器

#### `unregister(...)`
  - `self`
  - `name`: str
  注销适配器

#### `query(...)`
  - `self`
  - `text`: str
  - `query_type`: str
  - `limit`: int
  - Returns: `MemoryResult`
  统一记忆查询。

#### `remember(...)`
  - `self`
  - `content`: str
  - `source`: str
  - `tags`: List[str]
  - Returns: `bool`
  写入记忆（异步写入所有支持的适配器）。

#### `search(...)`
  - `self`
  - `text`: str
  - `limit`: int
  - Returns: `List[Dict]`
  快捷搜索

#### `get_available_sources(...)`
  - `self`
  - Returns: `List[str]`
  获取可用源列表

#### `health_check(...)`
  - `self`
  - Returns: `Dict[str, bool]`
  全部适配器健康检查

### `def get_federation(...)`
  - Returns: `MemoryFederation`
  获取全局 Memory Federation 实例

### `def query(...)`
  - `text`: str
  - Returns: `Dict`
  快捷查询

### `def remember(...)`
  - `content`: str
  - Returns: `bool`
  快捷写入

## product_evolve

**File:** `scripts/product_evolve.py`

>Hermes 产品迭代闭环引擎 v1.0

### `def log(...)`
  - `msg`

### `def load_top_items(...)`
  - `limit`
  取最近7天ai_score_total>=60的前3条

### `def get_evolution_history(...)`
  读取产品演化历史,找到已有迭代的产品

### `def save_evolution_history(...)`
  - `history`

### `def run_evolve_cycle(...)`

## production_chain_v2

**File:** `scripts/production_chain_v2.py`

>Hermes 全自动智能生产链调度器 v2.0

### `class ProductionChainScheduler`

  生产链调度器 - 基于Multi-Agent引擎

#### `__init__(...)`
  - `self`

#### `create_product(...)`
  - `self`
  - `name`: str
  - `description`: str
  - Returns: `int`
  创建产品记录

#### `update_status(...)`
  - `self`
  - `product_id`: int
  - `status`: str
  - `phase`: str
  更新产品状态

#### `save_data(...)`
  - `self`
  - `product_id`: int
  - `field`: str
  - `data`
  保存JSON数据到产品字段

#### `phase_collect(...)`
  - `self`
  - `product_id`: int
  - `topics`: list
  - Returns: `bool`
  阶段1: 采集 - 调度市场调研+数据分析员工

#### `phase_analyze(...)`
  - `self`
  - `product_id`: int
  - Returns: `bool`
  阶段2: 分析 - 调度产品经理+市场总监+品牌策略

#### `phase_design(...)`
  - `self`
  - `product_id`: int
  - Returns: `bool`
  阶段3: 设计 - 调度设计主管+R&D

#### `phase_build(...)`
  - `self`
  - `product_id`: int
  - Returns: `bool`
  阶段4: 生产 - 调度项目开发部

#### `phase_test(...)`
  - `self`
  - `product_id`: int
  - Returns: `bool`
  阶段5: 验收 - 调度测试与交付部

#### `phase_deliver(...)`
  - `self`
  - `product_id`: int
  - Returns: `bool`
  阶段6: 交付 - 调度销售部+支持部

#### `run_full_chain(...)`
  - `self`
  - `product_name`: str
  - `topics`: list
  - Returns: `bool`
  运行完整生产链

### `def init_product_db(...)`
  初始化产品数据库

### `def log_pipeline(...)`
  - `product_id`: int
  - `msg`: str
  - `conn`
  记录管道日志

## resilience_patterns

**File:** `scripts/resilience_patterns.py`

>resilience_patterns.py — 商用级弹性模式实现（对标OPA/pybreaker/Hystrix/AWS IAM）

### `class CircuitState`
*Inherits from: Enum*

### `class CircuitBreakerOpenError`
*Inherits from: Exception*

### `class CircuitBreakerConfig`

### `class CircuitBreaker`

  熔断器 — 对标 Hystrix/pybreaker 实现。
  
  在连续失败超过阈值后自动打开电路，
  经过冷却期后进入半开状态探测恢复。
  
  Attributes:
      name: 熔断器名称，用于日志和指标标识。
      config: 熔断器配置。
      state: 当前电路状态 (CLOSED/OPEN/HALF_OPEN)。
      stats: 调用统计 {'total', 'success', 'failure', 'rejected'}。
  
  Example:
      >>> cb = CircuitBreaker("api", CircuitBreakerConfig(fail_max=5))
      >>> cb.call(lambda: requests.get("http://api/service"))

#### `__init__(...)`
  - `self`
  - `name`: str
  - `config`: CircuitBreakerConfig | None
  初始化熔断器。

#### `state(...)`
  - `self`

#### `call(...)`
  - `self`
  - `func`
  通过熔断器调用目标函数。

#### `get_metrics(...)`
  - `self`

### `class RetryConfig`

### `class MaxRetriesExceededError`
*Inherits from: Exception*

### `class RateLimiterConfig`

### `class SlidingWindowRateLimiter`

  滑动窗口限流器 — 对标 AWS WAF。
  
  基于时间戳滑动窗口实现请求频率控制。
  
  Attributes:
      config: 限流配置 (RateLimiterConfig)。
  
  Example:
      >>> limiter = SlidingWindowRateLimiter(RateLimiterConfig(max_requests=100))
      >>> limiter.allow()  # True 或 False

#### `__init__(...)`
  - `self`
  - `config`: RateLimiterConfig
  初始化限流器。

#### `allow(...)`
  - `self`
  - Returns: `bool`

#### `remaining(...)`
  - `self`
  - Returns: `int`

### `class TimeoutManager`

  超时管理器 — 对标 Hystrix Timeout。
  
  通过线程+事件实现同步函数的超时控制。
  
  Example:
      >>> result = TimeoutManager.sync_timeout(slow_function, 5.0, arg1, arg2)

#### `sync_timeout(...)`
  - `func`
  - `timeout_seconds`
  对同步函数执行超时控制。

### `class NoFallbackAvailableError`
*Inherits from: Exception*

### `class FallbackRegistry`

#### `__init__(...)`
  - `self`

#### `register(...)`
  - `self`
  - `key`
  - `func`

#### `set_default(...)`
  - `self`
  - `func`

#### `execute(...)`
  - `self`
  - `key`

### `class DecisionRecord`

#### `to_dict(...)`
  - `self`

### `class DecisionAuditLogger`

#### `__init__(...)`
  - `self`
  - `log_dir`

#### `log(...)`
  - `self`
  - `record`: DecisionRecord

#### `query(...)`
  - `self`
  - `rule_name`
  - `limit`

### `class MetricsSnapshot`

### `class MetricsCollector`

#### `__init__(...)`
  - `self`
  - `name`
  - `window`

#### `record(...)`
  - `self`
  - `ok`
  - `latency_ms`

#### `snapshot(...)`
  - `self`

### `class HotReloader`

#### `__init__(...)`
  - `self`
  - `watch_path`
  - `reload_cb`
  - `interval`

#### `start(...)`
  - `self`

#### `stop(...)`
  - `self`

### `class DryRunMode`

  干跑模式 — 对标 OPA dry-run。
  
  在不实际执行规则的情况下评估规则匹配情况，
  记录完整的决策审计日志。
  
  Attributes:
      enabled: 是否启用干跑模式。
      logger: DecisionAuditLogger 实例（可选）。

#### `__init__(...)`
  - `self`
  - `enabled`
  - `logger`

#### `evaluate(...)`
  - `self`
  - `rule_name`
  - `input_data`
  - `callback`

### `class UnifiedRuleEnforcer`

  统一规则执行器 — 主执行管道。
  
  集成熔断器、限流、重试、降级、审计、指标、干跑等全部弹性组件。
  
  Attributes:
      name: 执行器名称。
      circuit_breaker: 熔断器实例（可选）。
      rate_limiter_cfg: 限流配置（可选）。
      retry_config: 重试配置（可选）。
      fallbacks: FallbackRegistry 降级注册表。
      audit: DecisionAuditLogger 审计日志。
      metrics: MetricsCollector 指标收集器。
      dry_run: DryRunMode 干跑模式。
  
  Example:
      >>> engine = UnifiedRuleEnforcer("my_rules")
      >>> engine.register_rule("allow_admin", lambda d: {"allowed": d.get("role") == "admin"})
      >>> engine.circuit_breaker = CircuitBreaker("api", CircuitBreakerConfig())
      >>> result = engine.execute("allow_admin", {"role": "admin"})

#### `__init__(...)`
  - `self`
  - `name`
  初始化统一规则执行器。

#### `register_rule(...)`
  - `self`
  - `name`
  - `func`
  注册规则函数。

#### `execute(...)`
  - `self`
  - `rule_name`
  - `input_data`
  执行指定规则，通过弹性管道。

### `def retry_with_backoff(...)`
  - `func`
  - `config`
  带指数退避的重试机制。

## synapse_bus

**File:** `scripts/synapse_bus.py`

>SynapseBus — Hermes 事件驱动+ Actor 模型的核心总线

### `class MergeWindow`

  合并窗口 — 多路并行结果对齐。
  
  当多个 Actor 并行处理同一个 correlation_id 的事件时，
  按 timeout 等待所有结果到达，然后合并。
  
  用法:
      mw = MergeWindow(default_timeout=5.0)
      mw.register('corr-123', 3)  # 等待3个结果
      mw.add_result('corr-123', 'actor-1', result1)
      mw.add_result('corr-123', 'actor-2', result2)
      results = mw.wait('corr-123')  # 等待第3个或超时

#### `__init__(...)`
  - `self`
  - `default_timeout`: float

#### `register(...)`
  - `self`
  - `correlation_id`: str
  - `expected_count`: int
  - `timeout`: Optional[float]
  - `event_type`: str
  注册一个合并窗口

#### `add_result(...)`
  - `self`
  - `correlation_id`: str
  - `actor_id`: str
  - `result`: Any
  - `is_error`: bool
  添加一个 Actor 的处理结果

#### `wait(...)`
  - `self`
  - `correlation_id`: str
  - Returns: `Optional[Dict]`
  等待窗口完成或超时。

#### `get_pending_count(...)`
  - `self`
  - Returns: `int`
  获取等待中的窗口数

#### `cleanup_stale(...)`
  - `self`
  - `max_age`: float
  清理超时未完成的窗口

### `class BackpressureGauge`

  背压监控 — 监控 Actor 负载，防止过载。
  
  背压级别:
  0 - 正常
  1 - 轻度（建议降级非核心）
  2 - 中度（强制降级）
  3 - 严重（熔断）

#### `__init__(...)`
  - `self`
  - `max_pending`: int
  - `max_error_rate`: float

#### `record_pending(...)`
  - `self`
  - `actor_id`: str
  - `delta`: int

#### `record_complete(...)`
  - `self`
  - `actor_id`: str
  - `success`: bool

#### `get_level(...)`
  - `self`
  - `actor_id`: str
  - Returns: `int`
  获取 Actor 的背压级别

#### `get_global_level(...)`
  - `self`
  - Returns: `int`
  获取全局背压级别

#### `reset(...)`
  - `self`
  - `actor_id`: Optional[str]

### `class EventStore`

  事件存储 — 将事件记录到 state.db 的 event_log 表

#### `__init__(...)`
  - `self`
  - `db_path`: str

#### `log_event(...)`
  - `self`
  - `event`: Event

#### `complete_event(...)`
  - `self`
  - `correlation_id`: str
  - `result_summary`: str

#### `get_stats(...)`
  - `self`
  - `since_minutes`: int
  - Returns: `Dict`

### `class SynapseBus`

  SynapseBus — 事件驱动+ Actor 模型的混合总线。
  
  这是 Hermes 三省六部制的通信骨架。
  所有 Actor 通过此总线注册、通信、协同。
  
  用法:
      bus = SynapseBus()
      
      # 注册 Actor
      bus.register_actor(my_actor, ["data.fetch", "text.analyze"])
      
      # 发射事件（同步模式）
      results = bus.emit("data.fetch", {"url": "..."})
      
      # 发射事件（并发模式）
      results = bus.emit_async("data.fetch", {"url": "..."})
      
      # 获取 Actor
      actors = bus.list_actors("data.fetch")

#### `__init__(...)`
  - `self`
  - `max_workers`: int
  - `merge_timeout`: float

#### `register_actor(...)`
  - `self`
  - `actor`: Actor
  - `topics`: List[str]
  注册 Actor 到总线。

#### `deregister_actor(...)`
  - `self`
  - `actor_id`: str
  注销 Actor

#### `get_actor(...)`
  - `self`
  - `actor_id`: str
  - Returns: `Optional[Actor]`
  获取 Actor 实例

#### `list_actors(...)`
  - `self`
  - `topic`: Optional[str]
  - `status`: Optional[ActorStatus]
  - Returns: `List[Actor]`
  列出 Actor

#### `list_topics(...)`
  - `self`
  - Returns: `Dict[str, int]`
  列出所有 topic 和订阅者数量

#### `emit(...)`
  - `self`
  - `event_type`: str
  - `payload`: Any
  - `target_actors`: List[str]
  - `correlation_id`: str
  - `source_actor`: str
  - `priority`: int
  - `wait`: bool
  - `timeout`: Optional[float]
  - Returns: `List[Any]`
  发射事件（同步模式）。

#### `emit_concurrent(...)`
  - `self`
  - `event_type`: str
  - `payloads`: List[Any]
  - `mode`: str
  - `timeout`: Optional[float]
  - Returns: `List[Any]`
  并发发射多个事件（扇出模式）。

#### `emit_with_merge(...)`
  - `self`
  - `event_type`: str
  - `payloads`: Dict[str, Any]
  - `timeout`: Optional[float]
  - Returns: `Dict`
  发射多个事件并等待所有结果合并（fan-out/fan-in 模式）。

#### `on_event(...)`
  - `self`
  - `callback`: Callable
  注册事件回调（每次 emit 时调用）

#### `subscribe(...)`
  - `self`
  - `topic`: str
  - `actor_id`: str
  Actor 订阅 topic

#### `unsubscribe(...)`
  - `self`
  - `topic`: str
  - `actor_id`: str
  Actor 取消订阅

#### `set_xingbu(...)`
  - `self`
  - `xingbu_actor`: Actor
  设置刑部 Actor（异常接管）

#### `get_stats(...)`
  - `self`
  - Returns: `Dict`
  获取总线统计

#### `suspend_idle_actors(...)`
  - `self`
  - `max_idle_hours`: int
  挂起长时间未使用的 Actor

#### `cleanup_stale_windows(...)`
  - `self`
  清理超时的合并窗口

#### `shutdown(...)`
  - `self`
  关闭总线

### `def get_bus(...)`
  - Returns: `SynapseBus`
  获取全局 SynapseBus 实例

### `def emit(...)`
  - `event_type`: str
  - `payload`: Any
  - Returns: `List[Any]`
  快捷发射事件

### `def register_actor(...)`
  - `actor`: Actor
  - `topics`: List[str]
  快捷注册 Actor

## unified_collector

**File:** `scripts/unified_collector.py`

>Hermes Unified Collector v5 - All Platforms

### `def get_db(...)`

### `def init_db(...)`

### `def url_hash(...)`
  - `url`

### `def detect_language(...)`
  - `text`

### `def extract_tags(...)`
  - `title`
  - `content`

### `def is_collect_filtered(...)`
  - `title`
  - `content`
  - `source`
  - `platform`
  采集时即过滤：命中任意 active 黑名单关键词，直接丢弃不进库。

### `def insert_raw_item(...)`
  - `item`

### `def insert_batch(...)`
  - `items`

### `def fetch(...)`
  - `url`
  - `headers`
  - `timeout`
  - `post_data`

### `def parse_rss(...)`
  - `xml_text`

### `def collect_weibo_hot(...)`

### `def collect_weibo_military(...)`
  微博军事频道内容采集 — 通过搜索军事关键词获取

### `def collect_zhihu_hot(...)`

### `def collect_36kr(...)`

### `def collect_ithome(...)`

### `def collect_oschina(...)`

### `def collect_bilibili(...)`

### `def collect_bilibili_tech(...)`
  B站科技区内容采集 — 尝试API和页面爬取两种方式

### `def collect_toutiao(...)`

### `def collect_toutiao_military(...)`
  头条军事频道 — 采集军事/时政类内容

### `def collect_sogou_wechat(...)`

### `def collect_infoq_rss(...)`
  Collect InfoQ RSS - tech news

### `def collect_techmeme_rss(...)`
  Collect TechMeme RSS - tech news aggregator

### `def collect_freebuf_rss(...)`
  Collect FreeBuf RSS - Chinese security/tech news

### `def collect_arxiv_new(...)`
  Collect latest arXiv cs.AI papers - new working endpoint

### `def collect_hackernews(...)`

### `def collect_solidot(...)`

### `def collect_cnblogs(...)`

### `def collect_juejin(...)`

### `def collect_segmentfault(...)`

### `def collect_tencent_cloud(...)`

### `def collect_ifanr(...)`

### `def collect_tmtpost(...)`

### `def collect_huxiu(...)`
  虎嗅 — RSS feed

### `def collect_baidu(...)`

### `def collect_github_trending(...)`

### `def collect_huggingface(...)`

### `def collect_arxiv(...)`

### `def collect_reddit(...)`

### `def collect_devto(...)`

### `def collect_baidu_weibo_search(...)`

### `def collect_zhihu_questions(...)`

### `def collect_sina_tech(...)`

### `def collect_zhihu_topstory(...)`

### `def collect_zhihu_daily(...)`

### `def collect_tieba(...)`

### `def collect_kuaishou(...)`
  快手 — delegates to enhanced collector

### `def collect_platform(...)`
  - `name`
  - `fn`
  - `priority`

### `def collect_all(...)`
  - `parallel`

### `def get_platform_stats(...)`


---

*Generated by `generate_api_reference.py` on 2026-06-15 16:24:04*