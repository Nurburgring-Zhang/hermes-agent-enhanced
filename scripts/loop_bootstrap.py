#!/usr/bin/env python3
"""
Loop Bootstrap — Hermes Loop Engineering 引导器
================================================
启动时注册3个核心loop到LoopEngine，并提供每轮检查接口供eternal_loop调用。

核心Loops:
  a. health_check_loop  — 每30分钟健康检查 (调用 guardian.py heal)
  b. evolution_loop     — 每1小时进化检查 (调用 evo_daemon_launcher.py)
  c. guardian_loop      — 每15分钟守护检查 (快速状态检查)

每个loop调用已有的LoopEngine和CheckpointStore记录执行状态。
日志输出到 ~/.hermes/logs/loops/

格林主人最高指令: Loop Engineering引擎必须被真实触发运行。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── 路径设置 ───────────────────────────────────────────────────

HERMES = Path.home() / ".hermes"
SCRIPTS = HERMES / "scripts"
LOOPS_LOG_DIR = HERMES / "logs" / "loops"
CHECKPOINT_DB = HERMES / "state" / "loop_checkpoints.db"

# 确保scripts在路径中
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))

LOOPS_LOG_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)


# ─── 日志 ───────────────────────────────────────────────────────

def loop_log(msg: str, loop_name: str = "bootstrap"):
    """结构化loop日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{loop_name}] {msg}"
    print(line)
    log_file = LOOPS_LOG_DIR / f"loop_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── CheckpointStore ────────────────────────────────────────────

class CheckpointStore:
    """
    Loop Engineering 检查点存储。
    为每个loop的执行提供持久化状态追踪：
      - 记录每次循环执行 (checkpoint entry)
      - 追踪成功/失败状态
      - 支持恢复中断的loop
      - 基于 SQLite 持久化
    """

    DB_PATH = str(CHECKPOINT_DB)

    def __init__(self, db_path: str = None):
        import sqlite3
        self.db_path = db_path or self.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS loop_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL UNIQUE,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL,
                    success INTEGER DEFAULT 0,
                    error_message TEXT,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS loop_checkpoint_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS loop_state (
                    loop_id TEXT PRIMARY KEY,
                    last_checkpoint_id TEXT,
                    last_run_at TEXT,
                    total_runs INTEGER DEFAULT 0,
                    total_successes INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    consecutive_failures INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cp_loop ON loop_checkpoints(loop_id, started_at);
                CREATE INDEX IF NOT EXISTS idx_cp_events ON loop_checkpoint_events(checkpoint_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def create_checkpoint(self, loop_id: str, phase: str = "start") -> str:
        """创建新检查点，返回checkpoint_id"""
        checkpoint_id = f"cp_{uuid.uuid4().hex[:16]}"
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO loop_checkpoints
                   (loop_id, checkpoint_id, phase, status, started_at)
                   VALUES (?, ?, ?, 'running', ?)""",
                (loop_id, checkpoint_id, phase, now)
            )
            conn.execute(
                """INSERT OR REPLACE INTO loop_state
                   (loop_id, last_checkpoint_id, last_run_at, total_runs, updated_at)
                   VALUES (
                       ?, ?, ?,
                       COALESCE((SELECT total_runs FROM loop_state WHERE loop_id = ?), 0) + 1,
                       datetime('now')
                   )""",
                (loop_id, checkpoint_id, now, loop_id)
            )
            conn.commit()
        finally:
            conn.close()
        return checkpoint_id

    def complete_checkpoint(self, loop_id: str, checkpoint_id: str,
                            success: bool, error: str = "",
                            metadata: dict = None):
        """标记检查点完成"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            # 计算持续时间
            row = conn.execute(
                "SELECT started_at FROM loop_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,)
            ).fetchone()
            duration = None
            if row and row["started_at"]:
                try:
                    started = datetime.fromisoformat(row["started_at"])
                    duration = (datetime.now() - started).total_seconds()
                except Exception:
                    pass

            conn.execute(
                """UPDATE loop_checkpoints
                   SET status = ?, completed_at = ?, duration_seconds = ?,
                       success = ?, error_message = ?, metadata_json = ?
                   WHERE checkpoint_id = ?""",
                ("completed" if success else "failed", now, duration,
                 1 if success else 0, error[:500] if error else "",
                 json.dumps(metadata or {}, ensure_ascii=False),
                 checkpoint_id)
            )

            # 更新loop状态
            if success:
                conn.execute(
                    """UPDATE loop_state
                       SET total_successes = total_successes + 1,
                           consecutive_failures = 0,
                           updated_at = datetime('now')
                       WHERE loop_id = ?""",
                    (loop_id,)
                )
            else:
                conn.execute(
                    """UPDATE loop_state
                       SET total_failures = total_failures + 1,
                           consecutive_failures = consecutive_failures + 1,
                           updated_at = datetime('now')
                       WHERE loop_id = ?""",
                    (loop_id,)
                )
            conn.commit()
        finally:
            conn.close()

    def record_event(self, loop_id: str, checkpoint_id: str,
                     event_type: str, event_data: dict = None):
        """记录检查点事件"""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO loop_checkpoint_events
                   (loop_id, checkpoint_id, event_type, event_data)
                   VALUES (?, ?, ?, ?)""",
                (loop_id, checkpoint_id, event_type,
                 json.dumps(event_data or {}, ensure_ascii=False))
            )
            conn.commit()
        finally:
            conn.close()

    def get_last_checkpoint(self, loop_id: str) -> Optional[Dict]:
        """获取最近一次检查点"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT * FROM loop_checkpoints
                   WHERE loop_id = ? ORDER BY started_at DESC LIMIT 1""",
                (loop_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_loop_state(self, loop_id: str) -> Optional[Dict]:
        """获取loop运行状态"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM loop_state WHERE loop_id = ?", (loop_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_recent_checkpoints(self, loop_id: str, limit: int = 10) -> List[Dict]:
        """获取最近的检查点列表"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM loop_checkpoints
                   WHERE loop_id = ? ORDER BY started_at DESC LIMIT ?""",
                (loop_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def is_due(self, loop_id: str, interval_minutes: int) -> Tuple[bool, float]:
        """检查loop是否到期需要执行。返回 (到期?, 距上次执行秒数)"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT last_run_at FROM loop_state WHERE loop_id = ?",
                (loop_id,)
            ).fetchone()
            if not row or not row["last_run_at"]:
                return True, float("inf")
            last_run = datetime.fromisoformat(row["last_run_at"])
            elapsed = (datetime.now() - last_run).total_seconds()
            return elapsed >= (interval_minutes * 60), elapsed
        finally:
            conn.close()


# ─── Loop 执行器 — 调用真实脚本 ─────────────────────────────────

def _run_script(script_name: str, args: str = "", timeout: int = 120) -> Tuple[bool, str]:
    """运行现有Hermes脚本，返回 (成功?, 输出)"""
    script_path = SCRIPTS / script_name
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    cmd = f"cd {HERMES} && python3 scripts/{script_name} {args}".strip()
    try:
        r = subprocess.run(
            cmd.split(), capture_output=True, text=True,
            timeout=timeout, cwd=str(HERMES)
        )
        output = (r.stdout or "")[:2000]
        if r.stderr:
            output += "\n[STDERR]: " + (r.stderr or "")[:500]
        return r.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout}s"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def execute_health_check(engine: "LoopEngine", store: CheckpointStore) -> Dict:
    """执行 health_check_loop"""
    loop_id = "health_check_loop"
    cp_id = store.create_checkpoint(loop_id, "execute")
    loop_log("🏥 健康检查循环启动...", "health_check")
    store.record_event(loop_id, cp_id, "health_check_start")

    try:
        # 使用已有的 LoopEngine 执行
        loop_def = engine.registered_loops.get(loop_id)
        if loop_def:
            result = await engine.run_loop(loop_id, "cron")
            success = result.success
        else:
            # 降级：直接运行 guardian.py heal
            success, output = _run_script("guardian.py", "heal", timeout=120)
            loop_log(f"  guardian.py heal → {'OK' if success else 'FAILED'}", "health_check")

        metadata = {
            "executor": "guardian.py heal" if not engine.registered_loops.get(loop_id) else "loop_engine",
            "timestamp": datetime.now().isoformat(),
        }
        store.complete_checkpoint(loop_id, cp_id, success=success, metadata=metadata)
        store.record_event(loop_id, cp_id,
                          "health_check_complete" if success else "health_check_failed",
                          metadata)
        loop_log(f"🏥 健康检查完成: {'✅ OK' if success else '❌ FAILED'}", "health_check")
        return {"loop_id": loop_id, "success": success, "checkpoint_id": cp_id}
    except Exception as e:
        store.complete_checkpoint(loop_id, cp_id, success=False,
                                  error=str(e))
        loop_log(f"🏥 健康检查异常: {e}", "health_check")
        return {"loop_id": loop_id, "success": False, "error": str(e)}


async def execute_evolution(engine: "LoopEngine", store: CheckpointStore) -> Dict:
    """执行 evolution_loop"""
    loop_id = "evolution_loop"
    cp_id = store.create_checkpoint(loop_id, "execute")
    loop_log("🔮 进化检查循环启动...", "evolution")
    store.record_event(loop_id, cp_id, "evolution_start")

    try:
        loop_def = engine.registered_loops.get(loop_id)
        if loop_def:
            result = await engine.run_loop(loop_id, "cron")
            success = result.success
        else:
            success, output = _run_script("evo_daemon_launcher.py", "--quiet", timeout=300)
            loop_log(f"  evo_daemon_launcher.py → {'OK' if success else 'FAILED'}", "evolution")

        metadata = {
            "executor": "evo_daemon_launcher.py" if not engine.registered_loops.get(loop_id) else "loop_engine",
            "timestamp": datetime.now().isoformat(),
        }
        store.complete_checkpoint(loop_id, cp_id, success=success, metadata=metadata)
        store.record_event(loop_id, cp_id,
                          "evolution_complete" if success else "evolution_failed",
                          metadata)
        loop_log(f"🔮 进化检查完成: {'✅ OK' if success else '❌ FAILED'}", "evolution")
        return {"loop_id": loop_id, "success": success, "checkpoint_id": cp_id}
    except Exception as e:
        store.complete_checkpoint(loop_id, cp_id, success=False, error=str(e))
        loop_log(f"🔮 进化检查异常: {e}", "evolution")
        return {"loop_id": loop_id, "success": False, "error": str(e)}


async def execute_guardian(engine: "LoopEngine", store: CheckpointStore) -> Dict:
    """执行 guardian_loop — 快速守护检查"""
    loop_id = "guardian_loop"
    cp_id = store.create_checkpoint(loop_id, "execute")
    loop_log("🛡️ 守护检查循环启动...", "guardian")
    store.record_event(loop_id, cp_id, "guardian_start")

    try:
        loop_def = engine.registered_loops.get(loop_id)
        if loop_def:
            result = await engine.run_loop(loop_id, "cron")
            success = result.success
        else:
            # 快速状态检查: 检查守护日志 + 心跳文件
            success = True
            checks = {}

            # 检查心跳文件存在
            heartbeat = HERMES / "cron" / "eternal_heartbeat.txt"
            if heartbeat.exists():
                try:
                    hb_time = datetime.fromisoformat(heartbeat.read_text().strip())
                    hb_age = (datetime.now() - hb_time).total_seconds()
                    checks["heartbeat_age_s"] = hb_age
                    if hb_age > 600:  # 超过10分钟
                        checks["heartbeat_stale"] = True
                        loop_log(f"  ⚠️ 心跳过期: {hb_age:.0f}秒", "guardian")
                    else:
                        checks["heartbeat_ok"] = True
                except Exception:
                    checks["heartbeat_error"] = "无法解析心跳时间"
                    success = False
            else:
                checks["heartbeat_missing"] = True
                success = False
                loop_log(f"  ❌ 心跳文件缺失", "guardian")

            # 检查guardian日志
            guardian_log = HERMES / "logs" / f"guardian_{datetime.now().strftime('%Y%m%d')}.log"
            if guardian_log.exists():
                checks["guardian_log_size"] = guardian_log.stat().st_size
                try:
                    last_lines = guardian_log.read_text()[-500:]
                    if "ERROR" in last_lines or "❌" in last_lines:
                        checks["guardian_errors"] = True
                        loop_log(f"  ⚠️ guardian日志有异常", "guardian")
                except Exception:
                    pass

            loop_log(f"  守护状态检查: {'✅ OK' if success else '❌ 有问题'}", "guardian")

        metadata = {
            "checks": checks if 'checks' in dir() else {},
            "timestamp": datetime.now().isoformat(),
        }
        store.complete_checkpoint(loop_id, cp_id, success=success, metadata=metadata)
        store.record_event(loop_id, cp_id,
                          "guardian_complete" if success else "guardian_warning",
                          metadata)
        loop_log(f"🛡️ 守护检查完成: {'✅ OK' if success else '⚠️ 警告'}", "guardian")
        return {"loop_id": loop_id, "success": success, "checkpoint_id": cp_id}
    except Exception as e:
        store.complete_checkpoint(loop_id, cp_id, success=False, error=str(e))
        loop_log(f"🛡️ 守护检查异常: {e}", "guardian")
        return {"loop_id": loop_id, "success": False, "error": str(e)}


# ─── Loop 定义工厂 ──────────────────────────────────────────────

def create_health_check_loop() -> dict:
    """创建 health_check_loop 定义"""
    return {
        "loop_id": "health_check_loop",
        "name": "Health Check Loop",
        "description": "每30分钟系统健康检查：自愈、磁盘空间、日志轮转、守护状态",
        "trigger": {
            "trigger_type": "cron",
            "cron_expression": "*/30 * * * *",
            "cron_timezone": "Asia/Shanghai",
        },
        "task_graph": {
            "nodes": [
                {
                    "id": "check_disk",
                    "name": "Check Disk Space",
                    "node_type": "verification",
                    "tool_name": "health_check_disk",
                    "success_criteria": [
                        {"type": "state_check", "check": "disk_usage < 90%"}
                    ],
                    "max_retries": 2,
                    "weight": 0.3,
                },
                {
                    "id": "check_heartbeat",
                    "name": "Check Heartbeat Files",
                    "node_type": "verification",
                    "tool_name": "health_check_heartbeat",
                    "depends_on": [],
                    "success_criteria": [
                        {"type": "existence", "check": "heartbeat_recent"}
                    ],
                    "weight": 0.3,
                },
                {
                    "id": "run_heal",
                    "name": "Execute Self-Healing",
                    "node_type": "action",
                    "tool_name": "guardian_heal",
                    "depends_on": ["check_disk", "check_heartbeat"],
                    "success_criteria": [
                        {"type": "state_check", "check": "heal_completed"}
                    ],
                    "max_retries": 3,
                    "weight": 0.4,
                },
            ],
            "edges": [
                {"from_node": "check_disk", "to_node": "run_heal", "edge_type": "dependency"},
                {"from_node": "check_heartbeat", "to_node": "run_heal", "edge_type": "dependency"},
            ],
        },
        "verification_rules": [
            {"id": "v_health", "name": "All Health Checks Pass",
             "rule_type": "test_pass", "severity": "error"},
        ],
        "memory_config": {
            "store_type": "sqlite",
            "max_checkpoints": 100,
            "retention_days": 30,
        },
        "max_parallel_tasks": 4,
    }


def create_evolution_loop() -> dict:
    """创建 evolution_loop 定义"""
    return {
        "loop_id": "evolution_loop",
        "name": "Evolution Loop",
        "description": "每1小时进化检查：V3守护进程、技能自进化、记忆集成",
        "trigger": {
            "trigger_type": "cron",
            "cron_expression": "0 * * * *",
            "cron_timezone": "Asia/Shanghai",
        },
        "task_graph": {
            "nodes": [
                {
                    "id": "check_skills",
                    "name": "Check Skill Versions",
                    "node_type": "verification",
                    "tool_name": "evolution_check_skills",
                    "success_criteria": [
                        {"type": "state_check", "check": "skill_inventory_valid"}
                    ],
                    "weight": 0.2,
                },
                {
                    "id": "run_evo_daemon",
                    "name": "Run V3 Evolution Daemon",
                    "node_type": "action",
                    "tool_name": "evo_daemon_cycle",
                    "depends_on": ["check_skills"],
                    "success_criteria": [
                        {"type": "state_check", "check": "evo_cycle_completed"}
                    ],
                    "max_retries": 2,
                    "weight": 0.5,
                },
                {
                    "id": "integrate_memory",
                    "name": "Memory Integration",
                    "node_type": "action",
                    "tool_name": "memory_integration",
                    "depends_on": ["run_evo_daemon"],
                    "success_criteria": [
                        {"type": "state_check", "check": "memory_integrated"}
                    ],
                    "weight": 0.3,
                },
            ],
            "edges": [
                {"from_node": "check_skills", "to_node": "run_evo_daemon", "edge_type": "dependency"},
                {"from_node": "run_evo_daemon", "to_node": "integrate_memory", "edge_type": "dependency"},
            ],
        },
        "verification_rules": [
            {"id": "v_evo", "name": "Evolution Cycle Complete",
             "rule_type": "test_pass", "severity": "error"},
        ],
        "memory_config": {
            "store_type": "sqlite",
            "max_checkpoints": 100,
            "retention_days": 30,
        },
        "max_parallel_tasks": 2,
    }


def create_guardian_loop() -> dict:
    """创建 guardian_loop 定义"""
    return {
        "loop_id": "guardian_loop",
        "name": "Guardian Loop",
        "description": "每15分钟守护检查：心跳验证、日志检查、状态快照",
        "trigger": {
            "trigger_type": "cron",
            "cron_expression": "*/15 * * * *",
            "cron_timezone": "Asia/Shanghai",
        },
        "task_graph": {
            "nodes": [
                {
                    "id": "verify_heartbeat",
                    "name": "Verify Heartbeat",
                    "node_type": "verification",
                    "tool_name": "guardian_check_heartbeat",
                    "success_criteria": [
                        {"type": "existence", "check": "heartbeat_valid"}
                    ],
                    "weight": 0.4,
                },
                {
                    "id": "check_logs",
                    "name": "Check Recent Logs",
                    "node_type": "verification",
                    "tool_name": "guardian_check_logs",
                    "success_criteria": [
                        {"type": "state_check", "check": "no_recent_critical_errors"}
                    ],
                    "weight": 0.3,
                },
                {
                    "id": "snapshot_state",
                    "name": "Take State Snapshot",
                    "node_type": "action",
                    "tool_name": "guardian_snapshot",
                    "depends_on": ["verify_heartbeat"],
                    "success_criteria": [
                        {"type": "state_check", "check": "snapshot_saved"}
                    ],
                    "weight": 0.3,
                },
            ],
            "edges": [
                {"from_node": "verify_heartbeat", "to_node": "snapshot_state", "edge_type": "dependency"},
            ],
        },
        "verification_rules": [
            {"id": "v_guardian", "name": "Guardian Checks Pass",
             "rule_type": "test_pass", "severity": "warning"},
        ],
        "memory_config": {
            "store_type": "sqlite",
            "max_checkpoints": 200,
            "retention_days": 7,
        },
        "max_parallel_tasks": 3,
    }


# ─── 引导器主类 ─────────────────────────────────────────────────

class LoopBootstrap:
    """
    Loop Engineering 引导器。
    注册3个核心loop，提供 periodic_check() 方法供 eternal_loop 每轮调用。
    """

    def __init__(self):
        self.engine: Optional["LoopEngine"] = None
        self.store: CheckpointStore = CheckpointStore()
        self._loop_definitions: Dict[str, dict] = {}
        self._initialized = False

    def init_engine(self):
        """初始化LoopEngine并注册3个核心loop"""
        try:
            from loop_engine import LoopEngine, LoopDefinition
            self.engine = LoopEngine()
            self._register_all_loops()
            self._initialized = True
            loop_log("✅ LoopEngine 初始化成功，已注册3个核心loop", "bootstrap")
            return True
        except ImportError as e:
            loop_log(f"⚠️ LoopEngine导入失败: {e}，将使用降级模式（直接调用脚本）", "bootstrap")
            # 降级模式：记录loop定义但不通过LoopEngine执行
            self._loop_definitions = {
                "health_check_loop": create_health_check_loop(),
                "evolution_loop": create_evolution_loop(),
                "guardian_loop": create_guardian_loop(),
            }
            self._initialized = True
            return False

    def _register_all_loops(self):
        """注册所有核心loop到LoopEngine"""
        loop_defs = [
            create_health_check_loop(),
            create_evolution_loop(),
            create_guardian_loop(),
        ]
        for ld in loop_defs:
            self.engine.register_loop(ld)
            self._loop_definitions[ld["loop_id"]] = ld
            loop_log(f"  📋 已注册: {ld['name']} ({ld['loop_id']})", "bootstrap")

    async def _check_and_run(self, loop_id: str, interval_minutes: int,
                             executor_fn) -> Optional[Dict]:
        """检查loop是否到期，如果到期则执行"""
        is_due, elapsed = self.store.is_due(loop_id, interval_minutes)
        if is_due:
            if elapsed == float("inf"):
                loop_log(f"🆕 {loop_id} 首次运行", "bootstrap")
            else:
                loop_log(f"⏰ {loop_id} 距上次运行 {elapsed/60:.1f}分钟，触发执行", "bootstrap")
            return await executor_fn(self.engine, self.store)
        return None

    async def periodic_check(self) -> Dict[str, Any]:
        """
        每轮循环检查 — 供 eternal_loop 调用。
        检查3个核心loop是否需要执行，并执行到期的loop。
        非阻塞：只触发到期的loop。

        Returns:
            dict: {"loops_checked": int, "loops_executed": int, "results": list}
        """
        if not self._initialized:
            self.init_engine()

        results = []
        executed = 0

        loop_log(f"🔍 周期检查开始...", "bootstrap")

        # 1. guardian_loop — 每15分钟
        r = await self._check_and_run(
            "guardian_loop", 15, execute_guardian
        )
        if r:
            results.append(r)
            executed += 1

        # 2. health_check_loop — 每30分钟
        r = await self._check_and_run(
            "health_check_loop", 30, execute_health_check
        )
        if r:
            results.append(r)
            executed += 1

        # 3. evolution_loop — 每60分钟
        r = await self._check_and_run(
            "evolution_loop", 60, execute_evolution
        )
        if r:
            results.append(r)
            executed += 1

        if executed == 0:
            loop_log(f"  无到期loop，跳过执行", "bootstrap")
        else:
            loop_log(f"  执行了 {executed} 个loop", "bootstrap")

        return {
            "loops_checked": 3,
            "loops_executed": executed,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    def run_all_now(self) -> List[Dict]:
        """
        强制执行所有3个loop（忽略时间间隔）。
        用于首次启动验证或手动触发。
        """
        results = []
        loop_log("🚀 强制执行所有核心loop...", "bootstrap")

        # 同步包装异步执行
        async def _run_all():
            r1 = await execute_guardian(self.engine, self.store)
            r2 = await execute_health_check(self.engine, self.store)
            r3 = await execute_evolution(self.engine, self.store)
            return [r1, r2, r3]

        try:
            # 尝试获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _run_all())
                        results = future.result(timeout=600)
                else:
                    results = asyncio.run(_run_all())
            except RuntimeError:
                results = asyncio.run(_run_all())
        except Exception as e:
            loop_log(f"❌ 全量执行异常: {e}", "bootstrap")
            results = [{"error": str(e)}]

        # 打印状态汇总
        loop_log("=" * 50, "bootstrap")
        loop_log("📊 Loop执行状态汇总:", "bootstrap")
        for r in results:
            lid = r.get("loop_id", "unknown")
            ok = r.get("success", False)
            cpid = r.get("checkpoint_id", "?")
            err = r.get("error", "")
            status_icon = "✅" if ok else "❌"
            err_str = f" — {err}" if err else ""
            loop_log(f"  {status_icon} {lid}: checkpoint={cpid}{err_str}", "bootstrap")

        # 打印CheckpointStore统计
        for lid in ["guardian_loop", "health_check_loop", "evolution_loop"]:
            state = self.store.get_loop_state(lid)
            if state:
                loop_log(
                    f"  📈 {lid}: 总运行{state.get('total_runs',0)}次 "
                    f"成功{state.get('total_successes',0)}次 "
                    f"失败{state.get('total_failures',0)}次",
                    "bootstrap"
                )

        loop_log("=" * 50, "bootstrap")
        return results

    def get_status(self) -> Dict:
        """获取所有loop的状态信息"""
        status = {}
        for loop_id in ["guardian_loop", "health_check_loop", "evolution_loop"]:
            state = self.store.get_loop_state(loop_id)
            last_cp = self.store.get_last_checkpoint(loop_id)
            is_due, elapsed = self.store.is_due(loop_id,
                15 if loop_id == "guardian_loop" else
                30 if loop_id == "health_check_loop" else 60)

            status[loop_id] = {
                "state": state,
                "last_checkpoint": last_cp,
                "is_due": is_due,
                "seconds_since_last_run": elapsed,
                "minutes_since_last_run": round(elapsed/60, 1) if elapsed != float("inf") else "never",
            }
        return status


# ─── CLI入口 ─────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Hermes Loop Bootstrap — Loop Engineering引导器"
    )
    parser.add_argument(
        "action", nargs="?", default="run",
        choices=["run", "check", "status", "force", "init"],
        help="动作: run(执行到期loop), check(周期检查-供eternal_loop调用), "
             "status(查看状态), force(强制执行所有loop), init(仅初始化注册)"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")

    args = parser.parse_args()
    bootstrap = LoopBootstrap()

    # 先初始化引擎
    engine_ok = bootstrap.init_engine()
    if not args.quiet:
        loop_log(f"Loop Bootstrap v1.0 — 引擎状态: {'LoopEngine' if engine_ok else '降级(直接调用脚本)'}", "bootstrap")

    if args.action == "init":
        loop_log("✅ 初始化完成，3个核心loop已注册", "bootstrap")
        bootstrap.get_status()

    elif args.action == "status":
        loop_log("📊 查询Loop状态...", "bootstrap")
        status = bootstrap.get_status()
        for lid, info in status.items():
            state = info.get("state", {})
            last_cp = info.get("last_checkpoint", {})
            print(f"\n  --- {lid} ---")
            if state:
                print(f"  总运行: {state.get('total_runs', 0)} | "
                      f"成功: {state.get('total_successes', 0)} | "
                      f"失败: {state.get('total_failures', 0)} | "
                      f"连续失败: {state.get('consecutive_failures', 0)}")
            if last_cp:
                print(f"  最后检查点: {last_cp.get('checkpoint_id', '?')} "
                      f"状态={last_cp.get('status', '?')} "
                      f"成功={last_cp.get('success', 0)}")
            print(f"  距上次运行: {info.get('minutes_since_last_run', '?')}分钟 | "
                  f"到期: {'是' if info.get('is_due') else '否'}")

    elif args.action == "check":
        # periodic_check — 供 eternal_loop 调用
        result = asyncio.run(bootstrap.periodic_check())
        if not args.quiet:
            print(f"loops_checked={result['loops_checked']} "
                  f"loops_executed={result['loops_executed']}")

    elif args.action == "force":
        # 强制执行所有loop（用于首次验证和手动触发）
        results = bootstrap.run_all_now()

    elif args.action == "run":
        # 默认：周期检查 + 强制执行首次（如果从未运行过）
        # 先检查哪些从未运行过，强制执行它们
        any_never_run = False
        for loop_id in ["guardian_loop", "health_check_loop", "evolution_loop"]:
            state = bootstrap.store.get_loop_state(loop_id)
            if not state or state.get("total_runs", 0) == 0:
                any_never_run = True
                break

        if any_never_run:
            if not args.quiet:
                loop_log("🆕 检测到首次运行，强制执行所有loop...", "bootstrap")
            results = bootstrap.run_all_now()
        else:
            result = asyncio.run(bootstrap.periodic_check())
            if not args.quiet:
                print(f"loops_checked={result['loops_checked']} "
                      f"loops_executed={result['loops_executed']}")

    return 0


# ─── 供 eternal_loop 导入的函数 ──────────────────────────────────

# 全局单例
_bootstrap_instance: Optional[LoopBootstrap] = None


def get_bootstrap() -> LoopBootstrap:
    """获取或创建 LoopBootstrap 单例"""
    global _bootstrap_instance
    if _bootstrap_instance is None:
        _bootstrap_instance = LoopBootstrap()
    return _bootstrap_instance


def check_loops_sync():
    """
    同步版本 — 供 eternal_loop 直接调用。
    检查并执行所有到期loop。不抛出异常。
    """
    try:
        bootstrap = get_bootstrap()
        if not bootstrap._initialized:
            bootstrap.init_engine()
        result = asyncio.run(bootstrap.periodic_check())
        return result
    except Exception as e:
        loop_log(f"check_loops_sync 异常: {e}", "bootstrap")
        return {"error": str(e), "loops_checked": 0, "loops_executed": 0}


def bootstrap_force_run():
    """
    强制执行所有loop（首次启动用）。
    """
    try:
        bootstrap = get_bootstrap()
        if not bootstrap._initialized:
            bootstrap.init_engine()
        return bootstrap.run_all_now()
    except Exception as e:
        loop_log(f"bootstrap_force_run 异常: {e}", "bootstrap")
        return [{"error": str(e)}]


if __name__ == "__main__":
    sys.exit(main())
