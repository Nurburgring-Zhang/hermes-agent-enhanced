#!/usr/bin/env python3
"""
Agents Company 自动化控制器
管理各部门和环节的自动化级别，控制自动执行策略
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

BASE_DIR = Path.home() / ".hermes" / "agents_company"
DATA_DIR = BASE_DIR / "data"

AUTOMATION_DB = DATA_DIR / "automation_control.sqlite"

class AutomationLevel(Enum):
    """自动化级别枚举"""
    MANUAL = 1          # L1: 完全手动，需人工确认每一步
    SEMI_AUTO = 2      # L2: 系统建议，需人工批准
    CONDITIONAL = 3    # L3: 满足条件自动执行（如风险<5%）
    FULL_AUTO = 4      # L4: 全自动执行，人工可查看日志
    AUTONOMOUS = 5     # L5: 智能自治，自决策 + 自优化

class DecisionContext:
    """决策上下文"""
    def __init__(self, **kwargs):
        self.department_id = kwargs.get("department_id")
        self.step_id = kwargs.get("step_id")
        self.task = kwargs.get("task", {})
        self.employee = kwargs.get("employee", {})
        self.conditions = kwargs.get("conditions", {})
        self.risk_level = kwargs.get("risk_level", "low")
        self.quality_score = kwargs.get("quality_score", 1.0)
        self.time_pressure = kwargs.get("time_pressure", "normal")
        self.resource_availability = kwargs.get("resource_availability", "sufficient")
        self.user_preference = kwargs.get("user_preference", "auto")  # auto|semi|manual

class AutomationController:
    """自动化控制器"""

    # 默认部门自动化级别配置
    DEFAULT_AUTOMATION_LEVELS = {
        1: 5,  # 信息采集部 - L5
        2: 4,  # 运营部 - L4
        3: 4,  # 设计部 - L4
        4: 4,  # 产品部 - L4
        5: 5,  # 研发部 - L5
        6: 4,  # 项目管理部 - L4
        7: 5,  # 项目开发部 - L5
        8: 3,  # 项目支持部 - L3
        9: 4,  # 工程部 - L4
        10: 3, # 测试与交付部 - L3
        11: 4, # 宣传媒体部 - L4
        12: 3, # 支持部 - L3
    }

    def __init__(self):
        self.db_path = AUTOMATION_DB
        self.config = {}
        self.rules = []
        self.overrides = {}  # 具体任务/员工的覆盖

        # 初始化数据库
        self._init_database()

        # 加载配置
        self._load_config()

        logger = logging.getLogger(__name__)
        logger.info("自动化控制器初始化完成")

    def _init_database(self):
        """初始化自动化控制数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 自动化级别配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_config (
                entity_type TEXT NOT NULL,  -- department|step|employee|task_type
                entity_id TEXT NOT NULL,   -- 部门ID/步骤ID/员工ID/任务类型
                automation_level INTEGER NOT NULL,  -- 1-5
                conditions TEXT,           -- JSON：触发此级别的条件
                overrides TEXT,            -- JSON：特殊情况覆盖
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_type, entity_id)
            )
        """)

        # 自动化规则表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                condition TEXT NOT NULL,   -- Python表达式
                action TEXT NOT NULL,     -- allow|deny|defer|escalate
                priority INTEGER DEFAULT 100,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 执行日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_logs (
                log_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                decision TEXT NOT NULL,    -- auto|manual|escalated
                automation_level INTEGER,
                context TEXT,              -- JSON
                reason TEXT,
                operator TEXT,             -- 如果人工介入，记录操作员
                duration_ms INTEGER
            )
        """)

        conn.commit()
        conn.close()

    def _load_config(self):
        """加载自动化配置"""
        # 从数据库加载
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 加载部门配置
        self.config["departments"] = {}
        cursor.execute("SELECT * FROM automation_config WHERE entity_type = ?", ("department",))
        for row in cursor.fetchall():
            dept_id = int(row["entity_id"])
            self.config["departments"][dept_id] = {
                "level": row["automation_level"],
                "conditions": json.loads(row["conditions"]) if row["conditions"] else {},
                "overrides": json.loads(row["overrides"]) if row["overrides"] else {}
            }

        # 加载步骤配置
        self.config["steps"] = {}
        cursor.execute("SELECT * FROM automation_config WHERE entity_type = ?", ("step",))
        for row in cursor.fetchall():
            step_id = row["entity_id"]
            self.config["steps"][step_id] = {
                "level": row["automation_level"],
                "conditions": json.loads(row["conditions"]) if row["conditions"] else {},
                "overrides": json.loads(row["overrides"]) if row["overrides"] else {}
            }

        conn.close()

        # 如果没有配置，使用默认值
        if not self.config["departments"]:
            self._initialize_default_config()

        # 加载规则
        self._load_rules()

        logger = logging.getLogger(__name__)
        logger.info(f"加载配置: {len(self.config['departments'])} 个部门, {len(self.config['steps'])} 个步骤")

    def _initialize_default_config(self):
        """初始化默认配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 部门默认配置
        for dept_id, level in self.DEFAULT_AUTOMATION_LEVELS.items():
            cursor.execute("""
                INSERT OR REPLACE INTO automation_config
                (entity_type, entity_id, automation_level, conditions, overrides)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "department", str(dept_id), level,
                json.dumps({}), json.dumps({})
            ))

        conn.commit()
        conn.close()

        # 更新内存配置
        self._load_config()

    def _load_rules(self):
        """加载自动化规则"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM automation_rules WHERE enabled = 1 ORDER BY priority")
        self.rules = [dict(row) for row in cursor.fetchall()]

        conn.close()

    def should_execute_auto(self, context: DecisionContext) -> tuple[bool, str, int]:
        """
        决定是否自动执行

        Returns:
            (should_auto, decision, level)
            - should_auto: 是否自动执行
            - decision: 决策类型 ('auto', 'manual', 'escalated', 'deferred')
            - level: 使用的自动化级别
        """
        start_time = datetime.now()

        # 1. 检查用户偏好
        if context.user_preference == "manual":
            self._log_decision(context, "manual", 1, "用户强制手动模式")
            return False, "manual", 1

        # 2. 获取部门/步骤配置的自动化级别
        dept_level = self.config["departments"].get(
            context.department_id,
            {"level": AutomationLevel.SEMI_AUTO.value}
        )["level"]

        # 3. 应用条件检查
        conditional_result = self._evaluate_conditions(context, dept_level)
        if not conditional_result["can_auto"]:
            self._log_decision(context, "deferred", dept_level, conditional_result["reason"])
            return False, "deferred", dept_level

        # 4. 应用规则引擎
        rule_decision = self._apply_rules(context, dept_level)
        if rule_decision["action"] == "deny":
            self._log_decision(context, "manual", dept_level, rule_decision["reason"])
            return False, "manual", dept_level
        if rule_decision["action"] == "escalate":
            self._log_decision(context, "escalated", dept_level, rule_decision["reason"])
            return False, "escalated", dept_level
        if rule_decision["action"] == "defer":
            self._log_decision(context, "deferred", dept_level, rule_decision["reason"])
            return False, "deferred", dept_level

        # 5. 根据级别决定是否自动
        if dept_level >= AutomationLevel.AUTONOMOUS.value or dept_level >= AutomationLevel.FULL_AUTO.value:
            should_auto = True
            decision = "auto"
        elif dept_level >= AutomationLevel.CONDITIONAL.value:
            # L3: 低风险自动，高风险需确认
            should_auto = context.risk_level in ["low", "medium"]
            decision = "auto" if should_auto else "manual"
        elif dept_level >= AutomationLevel.SEMI_AUTO.value:
            # L2: 高质量自动，低质量需确认
            should_auto = context.quality_score >= 0.85
            decision = "auto" if should_auto else "manual"
        else:
            # L1: 全部手动
            should_auto = False
            decision = "manual"

        # 6. 记录日志
        duration = (datetime.now() - start_time).total_seconds() * 1000
        self._log_decision(context, decision, dept_level, f"级别{dept_level}决策", duration_ms=int(duration))

        return should_auto, decision, dept_level

    def _evaluate_conditions(self, context: DecisionContext, automation_level: int) -> dict[str, Any]:
        """评估自动执行条件"""
        conditions = []

        # 检查风险条件
        if context.risk_level == "critical" and automation_level < 5:
            return {"can_auto": False, "reason": "高风险任务，需要人工审核"}

        # 检查资源可用性
        if context.resource_availability == "insufficient" and automation_level < 4:
            return {"can_auto": False, "reason": "资源不足，需要人工协调"}

        # 检查时间压力
        if context.time_pressure == "urgent":
            # 紧急任务可以自动执行（如果级别够高）
            if automation_level < 3:
                return {"can_auto": False, "reason": "紧急任务但自动化级别不足"}

        # 检查步骤特定条件
        step_config = self.config["steps"].get(context.step_id, {})
        step_conditions = step_config.get("conditions", {})

        if "min_automation_level" in step_conditions:
            if automation_level < step_conditions["min_automation_level"]:
                return {"can_auto": False, "reason": f"步骤需要自动化级别{step_conditions['min_automation_level']}"}

        return {"can_auto": True, "reason": "条件满足"}

    def _apply_rules(self, context: DecisionContext, automation_level: int) -> dict[str, str]:
        """应用自动化规则"""
        for rule in self.rules:
            try:
                # 评估规则条件
                condition_result = self._evaluate_rule_condition(rule["condition"], context)

                if condition_result:
                    logger = logging.getLogger(__name__)
                    logger.info(f"规则触发: {rule['name']} - {rule['action']} - {rule['reason']}")
                    return {
                        "action": rule["action"],
                        "reason": rule["description"]
                    }
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"规则评估失败: {rule['rule_id']} - {e}")

        return {"action": "allow", "reason": "无规则限制"}

    def _evaluate_rule_condition(self, condition: str, context: DecisionContext) -> bool:
        """评估规则条件（简化版）"""
        # 这里应该是一个安全的表达式求值器
        # 简化实现：只检查几个预定义条件

        condition_lower = condition.lower()

        if "risk" in condition_lower and "critical" in condition_lower:
            return context.risk_level == "critical"

        if "quality" in condition_lower and "low" in condition_lower:
            return context.quality_score < 0.7

        if "department" in condition_lower:
            # 检查部门ID
            dept_str = str(context.department_id)
            return dept_str in condition

        return False  # 默认不触发

    def _log_decision(self, context: DecisionContext, decision: str, level: int,
                     reason: str, duration_ms: int = None):
        """记录决策日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        log_id = f"log_{uuid.uuid4().hex[:12]}"

        cursor.execute("""
            INSERT INTO automation_logs
            (log_id, timestamp, entity_type, entity_id, decision,
             automation_level, context, reason, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, datetime.now().isoformat(),
            context.step_id or "unknown",
            context.step_id or "unknown",
            decision, level,
            json.dumps({
                "department_id": context.department_id,
                "risk_level": context.risk_level,
                "quality_score": context.quality_score,
                "user_preference": context.user_preference
            }, ensure_ascii=False),
            reason,
            duration_ms
        ))

        conn.commit()
        conn.close()

    def set_department_level(self, department_id: int, level: int, reason: str = ""):
        """设置部门的自动化级别"""
        if level not in [l.value for l in AutomationLevel]:
            raise ValueError(f"无效的自动化级别: {level}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO automation_config
            (entity_type, entity_id, automation_level, conditions, overrides, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "department", str(department_id), level,
            json.dumps({}), json.dumps({}),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        # 更新内存配置
        if department_id not in self.config["departments"]:
            self.config["departments"][department_id] = {}
        self.config["departments"][department_id]["level"] = level

        logger = logging.getLogger(__name__)
        logger.info(f"设置部门 {department_id} 自动化级别为 {level}: {reason}")

    def set_step_level(self, step_id: str, level: int, conditions: dict = None):
        """设置步骤的自动化级别"""
        if level not in [l.value for l in AutomationLevel]:
            raise ValueError(f"无效的自动化级别: {level}")

        if conditions is None:
            conditions = {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO automation_config
            (entity_type, entity_id, automation_level, conditions, overrides, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "step", step_id, level,
            json.dumps(conditions, ensure_ascii=False),
            json.dumps({}),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        # 更新内存配置
        self.config["steps"][step_id] = {
            "level": level,
            "conditions": conditions,
            "overrides": {}
        }

        logger = logging.getLogger(__name__)
        logger.info(f"设置步骤 {step_id} 自动化级别为 {level}")

    def add_rule(self, name: str, condition: str, action: str, description: str = "", priority: int = 100):
        """添加自动化规则"""
        if action not in ["allow", "deny", "defer", "escalate"]:
            raise ValueError(f"无效的操作: {action}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        rule_id = f"rule_{uuid.uuid4().hex[:12]}"

        cursor.execute("""
            INSERT INTO automation_rules
            (rule_id, name, description, condition, action, priority, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_id, name, description, condition, action, priority, True
        ))

        conn.commit()
        conn.close()

        # 重新加载规则
        self._load_rules()

        logger = logging.getLogger(__name__)
        logger.info(f"添加规则: {name} - {condition} -> {action}")

    def get_statistics(self, hours: int = 24) -> dict[str, Any]:
        """获取自动化统计"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(hours=hours)).isoformat()

        # 总体决策统计
        cursor.execute("""
            SELECT decision, COUNT(*) as count
            FROM automation_logs
            WHERE timestamp >= ?
            GROUP BY decision
        """, (since,))
        decisions = {row["decision"]: row["count"] for row in cursor.fetchall()}

        # 按级别统计
        cursor.execute("""
            SELECT automation_level, COUNT(*) as count
            FROM automation_logs
            WHERE timestamp >= ?
            GROUP BY automation_level
        """, (since,))
        by_level = {row["automation_level"]: row["count"] for row in cursor.fetchall()}

        # 平均决策时长
        cursor.execute("""
            SELECT AVG(duration_ms) as avg_duration
            FROM automation_logs
            WHERE timestamp >= ? AND duration_ms IS NOT NULL
        """, (since,))
        avg_duration = cursor.fetchone()["avg_duration"] or 0

        conn.close()

        return {
            "period": f"最近{hours}小时",
            "decisions": decisions,
            "by_automation_level": by_level,
            "avg_decision_time_ms": round(avg_duration, 2),
            "total_decisions": sum(decisions.values())
        }

    def get_current_config(self) -> dict[str, Any]:
        """获取当前配置"""
        return {
            "departments": self.config["departments"],
            "steps": self.config["steps"],
            "rules": self.rules
        }

# 便捷函数
_automation_controller = None

def get_automation_controller() -> AutomationController:
    """获取或创建自动化控制器单例"""
    global _automation_controller
    if _automation_controller is None:
        _automation_controller = AutomationController()
    return _automation_controller

def should_execute_auto(context: DecisionContext) -> tuple[bool, str, int]:
    """快速检查是否自动执行"""
    controller = get_automation_controller()
    return controller.should_execute_auto(context)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    controller = AutomationController()

    # 查看当前配置
    config = controller.get_current_config()
    print(f"当前配置: {json.dumps(config, ensure_ascii=False, indent=2)}")

    # 测试决策
    test_context = DecisionContext(
        department_id=5,  # 研发部
        step_id="phase3_dev_backend",
        task={"type": "development"},
        risk_level="low",
        quality_score=0.9,
        user_preference="auto"
    )

    should_auto, decision, level = controller.should_execute_auto(test_context)
    print(f"\n测试决策: 自动={should_auto}, 决策={decision}, 级别={level}")

    # 获取统计
    stats = controller.get_statistics()
    print(f"\n统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
