#!/usr/bin/env python3
"""
Agents Company 汇报系统
负责任务进度汇报、状态通知和日志管理
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

BASE_DIR = Path.home() / ".hermes" / "agents_company"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

REPORT_DB = DATA_DIR / "reports.sqlite"

class ReportType(Enum):
    """汇报类型枚举"""
    PROGRESS = "progress"           # 进度汇报
    COMPLETION = "completion"       # 完成汇报
    ISSUE = "issue"                 # 问题汇报
    COLLABORATION = "collaboration" # 协作请求
    MILESTONE = "milestone"         # 里程碑达成
    RISK = "risk"                   # 风险预警
    QUALITY = "quality"             # 质量报告

class ReportPriority(Enum):
    """汇报优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Report:
    """汇报数据结构"""
    report_id: str
    task_id: str
    employee_id: str
    employee_name: str
    department: str
    report_type: str
    priority: str
    timestamp: str
    progress: dict[str, Any] | None
    output: dict[str, Any] | None
    next_actions: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    collaboration_requests: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self):
        return asdict(self)

class ReportingSystem:
    """汇报系统主类"""

    def __init__(self):
        self.db_path = REPORT_DB
        self.websocket_clients = []  # WebSocket客户端列表
        self.notification_channels = {}  # 通知渠道配置

        # 初始化数据库
        self._init_database()

        # 加载通知配置
        self._load_notification_config()

        logger = logging.getLogger(__name__)
        logger.info("汇报系统初始化完成")

    def _init_database(self):
        """初始化汇报数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 汇报记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                department TEXT NOT NULL,
                report_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                progress TEXT,  -- JSON
                output TEXT,    -- JSON
                next_actions TEXT,  -- JSON
                issues TEXT,    -- JSON
                collaboration_requests TEXT,  -- JSON
                metadata TEXT   -- JSON
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task ON reports(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee ON reports(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON reports(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type_priority ON reports(report_type, priority)")

        # 汇报订阅表（谁需要接收哪些汇报）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                subscriber_id TEXT NOT NULL,  -- 员工ID或角色
                report_types TEXT NOT NULL,   -- JSON数组
                departments TEXT NOT NULL,    -- JSON数组，关注哪些部门
                priority_filter TEXT,         -- 最低优先级
                notification_channels TEXT NOT NULL,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _load_notification_config(self):
        """加载通知渠道配置"""
        config_path = BASE_DIR / "config" / "notifications.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                self.notification_channels = json.load(f)
        else:
            # 默认配置
            self.notification_channels = {
                "web_dashboard": {"enabled": True, "type": "websocket"},
                "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
                "discord": {"enabled": False, "webhook_url": ""},
                "email": {"enabled": False, "smtp_server": "", "recipients": []},
                "log": {"enabled": True, "level": "INFO"}
            }

    def create_report(self,
                     task_id: str,
                     employee_id: str,
                     employee_name: str,
                     department: str,
                     report_type: ReportType,
                     priority: ReportPriority = ReportPriority.MEDIUM,
                     progress: dict = None,
                     output: dict = None,
                     next_actions: list[dict] = None,
                     issues: list[dict] = None,
                     collaboration_requests: list[dict] = None,
                     metadata: dict = None) -> str:
        """
        创建汇报

        Returns:
            汇报ID
        """
        report_id = f"rep_{uuid.uuid4().hex[:12]}"

        if next_actions is None:
            next_actions = []
        if issues is None:
            issues = []
        if collaboration_requests is None:
            collaboration_requests = []
        if metadata is None:
            metadata = {}

        report = Report(
            report_id=report_id,
            task_id=task_id,
            employee_id=employee_id,
            employee_name=employee_name,
            department=department,
            report_type=report_type.value,
            priority=priority.value,
            timestamp=datetime.now().isoformat(),
            progress=progress,
            output=output,
            next_actions=next_actions,
            issues=issues,
            collaboration_requests=collaboration_requests,
            metadata=metadata
        )

        # 保存到数据库
        self._save_report(report)

        # 触发实时推送
        self._push_to_websocket(report)

        # 触发通知（根据订阅配置）
        self._trigger_notifications(report)

        logger = logging.getLogger(__name__)
        logger.info(f"创建汇报: {report_id} - {report_type.value} - {priority.value}")

        return report_id

    def _save_report(self, report: Report):
        """保存汇报到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO reports
            (report_id, task_id, employee_id, employee_name, department,
             report_type, priority, timestamp, progress, output,
             next_actions, issues, collaboration_requests, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.report_id, report.task_id, report.employee_id, report.employee_name,
            report.department, report.report_type, report.priority, report.timestamp,
            json.dumps(report.progress, ensure_ascii=False) if report.progress else None,
            json.dumps(report.output, ensure_ascii=False) if report.output else None,
            json.dumps(report.next_actions, ensure_ascii=False),
            json.dumps(report.issues, ensure_ascii=False),
            json.dumps(report.collaboration_requests, ensure_ascii=False),
            json.dumps(report.metadata, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

    def _push_to_websocket(self, report: Report):
        """推送到WebSocket客户端"""
        if not self.websocket_clients:
            return

        message = {
            "type": "report",
            "report": report.to_dict()
        }

        # 移除断开的客户端
        self.websocket_clients = [client for client in self.websocket_clients if client.is_connected]

        # 广播消息
        for client in self.websocket_clients:
            try:
                client.send(json.dumps(message))
            except:
                pass  # 客户端断开会自动清理

    def _trigger_notifications(self, report: Report):
        """触发通知渠道"""
        # 根据优先级决定通知渠道
        priority_levels = {
            ReportPriority.LOW.value: ["web_dashboard", "log"],
            ReportPriority.MEDIUM.value: ["web_dashboard", "log"],
            ReportPriority.HIGH.value: ["web_dashboard", "log", "telegram", "discord"],
            ReportPriority.CRITICAL.value: ["web_dashboard", "log", "telegram", "discord", "email"]
        }

        channels = priority_levels.get(report.priority, ["web_dashboard", "log"])

        for channel in channels:
            if channel in self.notification_channels and self.notification_channels[channel]["enabled"]:
                self._send_notification(channel, report)

    def _send_notification(self, channel: str, report: Report):
        """发送通知到指定渠道"""
        logger = logging.getLogger(__name__)

        if channel == "log":
            log_level = logging.INFO
            if report.priority == ReportPriority.HIGH.value:
                log_level = logging.WARNING
            elif report.priority == ReportPriority.CRITICAL.value:
                log_level = logging.ERROR

            logger.log(log_level, f"[{report.department}] {report.employee_name}: {report.report_type} - {report.progress}")

        elif channel == "telegram":
            # TODO: 实现Telegram通知
            pass

        elif channel == "discord":
            # TODO: 实现Discord通知
            pass

        elif channel == "email":
            # TODO: 实现邮件通知
            pass

    def get_reports(self,
                   task_id: str = None,
                   employee_id: str = None,
                   report_type: str = None,
                   priority: str = None,
                   start_time: str = None,
                   end_time: str = None,
                   limit: int = 100) -> list[dict]:
        """查询汇报"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM reports WHERE 1=1"
        params = []

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if employee_id:
            query += " AND employee_id = ?"
            params.append(employee_id)
        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        reports = []
        for row in rows:
            report_dict = dict(row)
            # 解析JSON字段
            for field in ["progress", "output", "next_actions", "issues", "collaboration_requests", "metadata"]:
                if report_dict.get(field):
                    report_dict[field] = json.loads(report_dict[field])
            reports.append(report_dict)

        conn.close()
        return reports

    def get_task_reports(self, task_id: str) -> list[dict]:
        """获取任务的所有汇报"""
        return self.get_reports(task_id=task_id)

    def get_employee_reports(self, employee_id: str, limit: int = 50) -> list[dict]:
        """获取员工的所有汇报"""
        return self.get_reports(employee_id=employee_id, limit=limit)

    def get_department_reports(self, department: str, limit: int = 100) -> list[dict]:
        """获取部门的所有汇报"""
        reports = self.get_reports(limit=limit)
        return [r for r in reports if r["department"] == department]

    def get_recent_reports(self, hours: int = 24) -> list[dict]:
        """获取最近指定小时内的汇报"""
        from datetime import timedelta
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        return self.get_reports(start_time=start_time, end_time=end_time)

    def subscribe_to_reports(self,
                           subscriber_id: str,
                           report_types: list[str],
                           departments: list[str],
                           priority_filter: str = "medium",
                           channels: list[str] = None) -> str:
        """
        订阅汇报通知

        Args:
            subscriber_id: 订阅者ID（员工ID或角色标识）
            report_types: 感兴趣的汇报类型列表
            departments: 关注的部门列表
            priority_filter: 最低优先级（低于此级别的不会通知）
            channels: 通知渠道列表

        Returns:
            订阅ID
        """
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"

        if channels is None:
            channels = ["web_dashboard", "log"]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO report_subscriptions
            (subscription_id, subscriber_id, report_types, departments,
             priority_filter, notification_channels)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            subscription_id, subscriber_id, json.dumps(report_types),
            json.dumps(departments), priority_filter, json.dumps(channels)
        ))

        conn.commit()
        conn.close()

        logger = logging.getLogger(__name__)
        logger.info(f"创建订阅: {subscriber_id} -> {subscription_id}")

        return subscription_id

    def generate_daily_summary(self, date: str = None) -> dict[str, Any]:
        """
        生成日报摘要

        Args:
            date: 日期（ISO格式），默认为今天

        Returns:
            日报数据
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 获取当天的汇报
        start_time = f"{date}T00:00:00"
        end_time = f"{date}T23:59:59"

        reports = self.get_reports(start_time=start_time, end_time=end_time, limit=1000)

        summary = {
            "date": date,
            "total_reports": len(reports),
            "by_type": {},
            "by_priority": {},
            "by_department": {},
            "critical_issues": [],
            "completed_tasks": [],
            "active_employees": set()
        }

        for report in reports:
            # 按类型统计
            rtype = report["report_type"]
            summary["by_type"][rtype] = summary["by_type"].get(rtype, 0) + 1

            # 按优先级统计
            priority = report["priority"]
            summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1

            # 按部门统计
            dept = report["department"]
            summary["by_department"][dept] = summary["by_department"].get(dept, 0) + 1

            # 活跃员工
            summary["active_employees"].add(report["employee_id"])

            # 关键问题
            if report["priority"] == ReportPriority.CRITICAL.value:
                summary["critical_issues"].append(report)

            # 完成任务
            if report["report_type"] == ReportType.COMPLETION.value:
                summary["completed_tasks"].append(report)

        summary["active_employees"] = len(summary["active_employees"])

        return summary

    def generate_project_report(self, task_id: str) -> dict[str, Any]:
        """生成项目报告"""
        reports = self.get_task_reports(task_id)

        if not reports:
            return {"error": "没有找到项目汇报"}

        project_report = {
            "task_id": task_id,
            "total_reports": len(reports),
            "start_time": reports[-1]["timestamp"],  # 最早的汇报
            "end_time": reports[0]["timestamp"],     # 最新的汇报
            "employees_involved": list(set(r["employee_id"] for r in reports)),
            "departments_involved": list(set(r["department"] for r in reports)),
            "issues_count": sum(1 for r in reports if r["report_type"] == ReportType.ISSUE.value),
            "completions": sum(1 for r in reports if r["report_type"] == ReportType.COMPLETION.value),
            "milestones": [r for r in reports if r["report_type"] == ReportType.MILESTONE.value],
            "latest_status": reports[0]
        }

        return project_report

    def add_websocket_client(self, client):
        """添加WebSocket客户端"""
        self.websocket_clients.append(client)

    def remove_websocket_client(self, client):
        """移除WebSocket客户端"""
        if client in self.websocket_clients:
            self.websocket_clients.remove(client)

# 便捷函数
_reporting_system = None

def get_reporting_system() -> ReportingSystem:
    """获取或创建汇报系统单例"""
    global _reporting_system
    if _reporting_system is None:
        _reporting_system = ReportingSystem()
    return _reporting_system

def create_report(**kwargs) -> str:
    """快速创建汇报"""
    rs = get_reporting_system()
    return rs.create_report(**kwargs)

def get_reports(**kwargs) -> list[dict]:
    """快速查询汇报"""
    rs = get_reporting_system()
    return rs.get_reports(**kwargs)

if __name__ == "__main__":
    # 测试
    import logging

    logging.basicConfig(level=logging.INFO)

    rs = ReportingSystem()

    # 创建测试汇报
    report_id = rs.create_report(
        task_id="test_task_001",
        employee_id="emp_001",
        employee_name="张三",
        department="研发部",
        report_type=ReportType.PROGRESS,
        priority=ReportPriority.HIGH,
        progress={
            "current_step": "技术架构设计",
            "completion_percentage": 75,
            "estimated_finish": (datetime.now() + timedelta(hours=2)).isoformat()
        },
        output={
            "deliverable_type": "technical_design",
            "content": "系统架构设计文档...",
            "quality_score": 8.5,
            "confidence": 0.92
        },
        next_actions=[
            {"type": "notify", "target": "项目管理部", "message": "技术方案已完成"},
            {"type": "assign", "target": "项目开发部", "task": "start_development"}
        ]
    )

    print(f"创建的汇报ID: {report_id}")

    # 查询汇报
    reports = rs.get_reports(task_id="test_task_001")
    print(f"查询到 {len(reports)} 条汇报")

    # 生成日报
    summary = rs.generate_daily_summary()
    print(f"日报摘要: {json.dumps(summary, ensure_ascii=False, indent=2)}")
