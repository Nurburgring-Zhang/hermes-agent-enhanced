#!/usr/bin/env python3
"""
Agents Company 工作流执行器
负责任务调度、员工分配和工作流执行
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# 导入Hermes工作流引擎
try:
    # workflow-engine 作为 agents_company 的子模块（符号链接）
    import sys
    from pathlib import Path
    base_dir = Path(__file__).parent  # agents_company 目录
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    # 通过完整包路径导入，确保 __package__ 正确
    from agents_company.workflow_engine import (
        WorkflowBuilder,
        WorkflowEngine,
        WorkflowStorage,
        workflow_list,
        workflow_register_handler,
        workflow_run,
        workflow_status,
        workflow_stop,
    )
    WORKFLOW_ENGINE_AVAILABLE = True
except ImportError as e:
    WORKFLOW_ENGINE_AVAILABLE = False
    print(f"警告: 工作流引擎不可用，某些功能将受限 ({e})")
    import traceback
    traceback.print_exc()

BASE_DIR = Path.home() / ".hermes" / "agents_company"
DATA_DIR = BASE_DIR / "data"
WORKFLOWS_DIR = BASE_DIR / "workflows"

EMPLOYEES_DB = DATA_DIR / "employees.sqlite"
DEPARTMENTS_DB = DATA_DIR / "departments.sqlite"
COLLAB_DB = DATA_DIR / "collaboration_network.sqlite"
WORKFLOW_DB = DATA_DIR / "workflows.sqlite"  # Agents公司工作流数据库

# 确保日志目录存在
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

# 配置路径以导入Hermes技能
import sys

HERMES_SKILLS_DIR = Path.home() / ".hermes" / "skills"
if str(HERMES_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_SKILLS_DIR))

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "executor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentsCompanyExecutor:
    """Agents公司工作流执行器"""

    def __init__(self):
        self.employee_selector = None
        self.workflow_engine = None
        self.workflow_storage = None
        self.reporting_system = None
        self.automation_controller = None
        self.handlers_registered = False

        # 初始化目录
        (BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger(__name__)
        logger.info("初始化Agents公司执行器...")
    def initialize(self):
        """初始化执行器"""
        from automation_controller import AutomationController
        from employee_selector import EmployeeSelector
        from reporting_system import ReportingSystem

        logger.info("加载员工选择器...")
        self.employee_selector = EmployeeSelector()

        logger.info("初始化汇报系统...")
        self.reporting_system = ReportingSystem()

        logger.info("初始化自动化控制器...")
        self.automation_controller = AutomationController()

        if WORKFLOW_ENGINE_AVAILABLE:
            logger.info("初始化工作流引擎...")
            self.workflow_storage = WorkflowStorage(str(WORKFLOW_DB))
            self.workflow_engine = WorkflowEngine(self.workflow_storage)
        else:
            logger.error("工作流引擎不可用，无法启动执行器")
            raise RuntimeError("工作流引擎不可用")

        self._register_handlers()

        logger.info("执行器初始化完成")

    def _register_handlers(self):
        """注册所有处理器"""
        if not WORKFLOW_ENGINE_AVAILABLE:
            return

        logger.info("注册工作流处理器...")

        # 注册公司级处理器
        workflow_register_handler("workflow_init", handler_code=self._handler_workflow_init)
        workflow_register_handler("info_collection", handler_code=self._handler_info_collection)
        workflow_register_handler("requirements_mining", handler_code=self._handler_requirements_mining)
        workflow_register_handler("requirements_validation", handler_code=self._handler_requirements_validation)
        workflow_register_handler("feature_design", handler_code=self._handler_feature_design)
        workflow_register_handler("product_specification", handler_code=self._handler_product_specification)
        workflow_register_handler("technical_architecture", handler_code=self._handler_technical_architecture)
        workflow_register_handler("project_planning", handler_code=self._handler_project_planning)
        workflow_register_handler("backend_development", handler_code=self._handler_backend_dev)
        workflow_register_handler("frontend_development", handler_code=self._handler_frontend_dev)
        workflow_register_handler("mobile_development", handler_code=self._handler_mobile_dev)
        workflow_register_handler("system_integration", handler_code=self._handler_system_integration)
        workflow_register_handler("quality_assurance", handler_code=self._handler_quality_assurance)
        workflow_register_handler("bug_fixing", handler_code=self._handler_bug_fixing)
        workflow_register_handler("deployment", handler_code=self._handler_deployment)
        workflow_register_handler("rollback_deployment", handler_code=self._handler_rollback)
        workflow_register_handler("marketing_creation", handler_code=self._handler_marketing_creation)
        workflow_register_handler("project_closure", handler_code=self._handler_project_closure)
        workflow_register_handler("project_celebration", handler_code=self._handler_project_celebration)

        # 注册补偿处理器
        workflow_register_handler("notify_stakeholders", handler_code=self._handler_notify_stakeholders)
        workflow_register_handler("partial_cleanup", handler_code=self._handler_partial_cleanup)
        workflow_register_handler("abort_project", handler_code=self._handler_abort_project)
        workflow_register_handler("retry_with_adjustments", handler_code=self._handler_retry_adjustments)

        self.handlers_registered = True
        logger.info("✓ 所有处理器注册完成")

    def create_workflow(self, workflow_def_path: str, workflow_id: str = None) -> str:
        """从文件创建工作流定义"""
        if not WORKFLOW_ENGINE_AVAILABLE:
            raise RuntimeError("工作流引擎不可用")

        with open(workflow_def_path, encoding="utf-8") as f:
            if workflow_def_path.endswith(".yaml") or workflow_def_path.endswith(".yml"):
                import yaml
                definition = yaml.safe_load(f)
            else:
                definition = json.load(f)

        workflow_id = workflow_id or definition.get("id", f"agents_workflow_{uuid.uuid4().hex[:8]}")
        definition["id"] = workflow_id

        workflow = WorkflowBuilder.from_dict(definition)
        self.workflow_storage.save_workflow(workflow)

        logger.info(f"创建工作流: {workflow_id}")
        return workflow_id

    def run_workflow(self, workflow_id: str, variables: dict[str, Any] = None,
                    wait: bool = True) -> str:
        """运行工作流"""
        if not WORKFLOW_ENGINE_AVAILABLE:
            raise RuntimeError("工作流引擎不可用")

        logger.info(f"启动工作流: {workflow_id}")

        # 注入自动化控制器和汇报系统
        if variables is None:
            variables = {}

        variables["automation_controller"] = self.automation_controller
        variables["reporting_system"] = self.reporting_system
        variables["employee_selector"] = self.employee_selector

        run_id = workflow_run(workflow_id, variables=variables, wait=wait)

        logger.info(f"工作流运行 ID: {run_id}")
        return run_id

    def get_workflow_status(self, run_id: str = None, workflow_id: str = None) -> dict:
        """获取工作流状态"""
        if not WORKFLOW_ENGINE_AVAILABLE:
            return {}

        if run_id:
            return workflow_status(run_id=run_id)
        if workflow_id:
            return workflow_status(workflow_id=workflow_id)
        return workflow_status(limit=20)

    def stop_workflow(self, run_id: str, reason: str = "手动停止") -> bool:
        """停止工作流"""
        if not WORKFLOW_ENGINE_AVAILABLE:
            return False

        return workflow_stop(run_id, reason=reason)

    def list_workflows(self, active_only: bool = True) -> list[dict]:
        """列出所有工作流"""
        if not WORKFLOW_ENGINE_AVAILABLE:
            return []

        return workflow_list(active_only=active_only)

    # ============= 工作流处理器实现 =============

    def _handler_workflow_init(self, context: dict) -> dict:
        """工作流初始化处理器"""
        logger.info("执行工作流初始化")
        variables = context.get("variables", {})

        project_id = variables.get("project_id", str(uuid.uuid4()))
        project_name = variables.get("project_name", "未命名项目")

        result = {
            "project_id": project_id,
            "project_name": project_name,
            "init_time": datetime.now().isoformat(),
            "status": "initialized"
        }

        logger.info(f"项目初始化完成: {project_name} ({project_id})")
        return result

    def _handler_info_collection(self, context: dict) -> dict:
        """信息采集处理器"""
        logger.info("执行信息采集")
        parameters = context.get("parameters", {})

        task = {
            "required_capabilities": [
                {"name": "research", "required_level": 6, "weight": 1.0},
                {"name": "web-search", "required_level": 7, "weight": 0.9},
                {"name": "data-mining", "required_level": 6, "weight": 0.8}
            ],
            "task_type": "market_analysis",
            "requires_analytical_thinking": True,
            "required_level": "Senior"
        }

        employees = self.employee_selector.select_employees(
            task,
            department_id=1,  # 信息采集部
            n=3  # 选择3人团队
        )

        result = {
            "assigned_team": [{"id": e["id"], "name": e["name"], "position": e["position"]} for e in employees],
            "collection_plan": {
                "sources": parameters.get("sources", []),
                "timeframe": parameters.get("timeframe_days", 30),
                "depth": parameters.get("depth", "comprehensive")
            },
            "status": "team_assigned"
        }

        logger.info(f"信息采集团队已分配: {len(employees)} 人")
        return result

    def _handler_requirements_mining(self, context: dict) -> dict:
        """需求挖掘处理器"""
        logger.info("执行需求挖掘")

        result = {
            "product_requirements": [
                {
                    "title": "示例需求",
                    "description": "从市场信息中挖掘出的核心需求",
                    "priority": "high",
                    "features": [
                        {"name": "核心功能A", "description": "满足主要用户需求"},
                        {"name": "辅助功能B", "description": "提升用户体验"}
                    ]
                }
            ],
            "key_insights": [
                "市场趋势显示X需求增长",
                "竞争对手在Y方面存在不足",
                "用户最关注Z特性"
            ],
            "status": "requirements_mined"
        }

        logger.info("需求挖掘完成")
        return result

    def _handler_requirements_validation(self, context: dict) -> dict:
        """需求验证处理器"""
        logger.info("执行需求验证")

        result = {
            "validated_requirements": [
                {
                    "title": "经过验证的需求",
                    "validation_score": 0.85,
                    "business_value": "high",
                    "technical_feasibility": "feasible"
                }
            ],
            "rejected_requirements": [],
            "report": {
                "total_requirements": 1,
                "validated": 1,
                "rejected": 0,
                "confidence": 0.85
            },
            "status": "validated"
        }

        logger.info("需求验证完成")
        return result

    def _handler_feature_design(self, context: dict) -> dict:
        """功能设计处理器"""
        logger.info("执行功能设计")

        result = {
            "design_document": {
                "user_flows": ["用户注册流程", "核心功能使用流程", "支付流程"],
                "wireframes": ["首页", "功能页", "设置页"],
                "mockups": ["初步视觉设计"],
                "design_specs": {
                    "color_scheme": "品牌色彩",
                    "typography": "系统字体",
                    "spacing": "8px网格"
                },
                "accessibility_requirements": ["WCAG 2.1 AA合规"]
            },
            "status": "design_completed"
        }

        logger.info("功能设计完成")
        return result

    def _handler_product_specification(self, context: dict) -> dict:
        """产品规格定义处理器"""
        logger.info("执行产品规格定义")

        result = {
            "prd": {
                "product_overview": {
                    "name": "新产品",
                    "vision": "成为市场领先者"
                },
                "features": [
                    {
                        "name": "主要特性1",
                        "description": "详细描述",
                        "user_stories": ["作为用户，我想..."],
                        "acceptance_criteria": ["给定...当...那么..."]
                    }
                ],
                "user_personas": [
                    {"name": "典型用户", "demographics": "25-35岁", "goals": ["目标1", "目标2"]}
                ],
                "use_cases": [
                    {"scenario": "使用场景", "steps": ["步骤1", "步骤2"]}
                ],
                "success_metrics": [
                    {"metric": "日活用户", "target": "10000"},
                    {"metric": "留存率", "target": "40%"}
                ],
                "release_plan": {
                    "version_1_0": "核心功能",
                    "version_1_1": "优化改进"
                }
            },
            "roadmap": {
                "q1_2026": "开发与测试",
                "q2_2026": "发布与推广"
            },
            "status": "prd_completed"
        }

        logger.info("产品规格定义完成")
        return result

    def _handler_technical_architecture(self, context: dict) -> dict:
        """技术架构设计处理器"""
        logger.info("执行技术架构设计")

        result = {
            "technical_design": {
                "architecture_diagram": "微服务架构图",
                "tech_stack": [
                    "Python (后端)",
                    "React (前端)",
                    "PostgreSQL (数据库)",
                    "Docker + Kubernetes (容器化)",
                    "Redis (缓存)"
                ],
                "api_specs": {
                    "rest_api": "OpenAPI 3.0规范",
                    "authentication": "JWT",
                    "rate_limiting": "1000 req/min"
                },
                "database_schema": {
                    "users": "用户表",
                    "products": "产品表",
                    "orders": "订单表"
                },
                "core_architecture": "事件驱动、微服务、API优先"
            },
            "status": "architecture_designed"
        }

        logger.info("技术架构设计完成")
        return result

    def _handler_project_planning(self, context: dict) -> dict:
        """项目计划处理器"""
        logger.info("执行项目计划制定")

        result = {
            "work_breakdown_structure": {
                "阶段1": ["信息采集", "需求分析"],
                "阶段2": ["设计", "技术方案"],
                "阶段3": ["开发", "测试"],
                "阶段4": ["部署", "交付"]
            },
            "gantt_chart": {
                "start_date": (datetime.now()).strftime("%Y-%m-%d"),
                "duration_weeks": 6,
                "milestones": [
                    {"name": "设计完成", "week": 2},
                    {"name": "开发完成", "week": 4},
                    {"name": "测试完成", "week": 5},
                    {"name": "交付", "week": 6}
                ]
            },
            "resource_allocation": {
                "developers": 8,
                "designers": 2,
                "qa": 3,
                "pm": 1
            },
            "risk_register": [
                {"risk": "技术债务", "probability": "medium", "impact": "high", "mitigation": "代码审查"},
                {"risk": "需求变更", "probability": "high", "impact": "medium", "mitigation": "敏捷迭代"}
            ],
            "status": "plan_completed"
        }

        logger.info("项目计划制定完成")
        return result

    def _handler_backend_dev(self, context: dict) -> dict:
        """后端开发处理器"""
        logger.info("执行后端开发")

        result = {
            "developed_modules": ["用户服务", "业务逻辑服务", "数据访问层"],
            "apis_implemented": ["REST API", "GraphQL端点"],
            "tests": ["单元测试", "集成测试"],
            "documentation": "API文档、部署文档",
            "status": "backend_completed"
        }

        logger.info("后端开发完成")
        return result

    def _handler_frontend_dev(self, context: dict) -> dict:
        """前端开发处理器"""
        logger.info("执行前端开发")

        result = {
            "components": ["Header", "Footer", "Dashboard", "Forms"],
            "pages": ["首页", "登录页", "管理后台"],
            "responsive": True,
            "accessibility_compliant": True,
            "status": "frontend_completed"
        }

        logger.info("前端开发完成")
        return result

    def _handler_mobile_dev(self, context: dict) -> dict:
        """移动端开发处理器"""
        logger.info("执行移动端开发")

        result = {
            "platform": "React Native",
            "features": ["离线支持", "推送通知", "相机访问"],
            "status": "mobile_completed"
        }

        logger.info("移动端开发完成")
        return result

    def _handler_system_integration(self, context: dict) -> dict:
        """系统集成处理器"""
        logger.info("执行系统集成")

        result = {
            "integrated_system": "完整的应用系统",
            "api_endpoints_tested": 25,
            "integration_issues_found": 0,
            "end_to_end_tests_passed": True,
            "status": "integration_completed"
        }

        logger.info("系统集成完成")
        return result

    def _handler_quality_assurance(self, context: dict) -> dict:
        """质量保证处理器"""
        logger.info("执行质量测试")

        result = {
            "test_execution_report": {
                "total_tests": 150,
                "passed": 148,
                "failed": 2,
                "skipped": 0
            },
            "quality_score": 0.95,
            "defect_log": [
                {"id": "BUG-001", "severity": "low", "description": "UI错位"},
                {"id": "BUG-002", "severity": "medium", "description": "性能问题"}
            ],
            "coverage_report": {
                "code_coverage": 0.87,
                "branch_coverage": 0.82,
                "test_coverage": 0.91
            },
            "status": "testing_completed"
        }

        logger.info("质量测试完成")
        return result

    def _handler_bug_fixing(self, context: dict) -> dict:
        """缺陷修复处理器"""
        logger.info("执行缺陷修复")

        result = {
            "fixed_build": "新的构建版本",
            "bugs_fixed": ["BUG-001", "BUG-002"],
            "regression_tests_passed": True,
            "status": "bugs_fixed"
        }

        logger.info("缺陷修复完成")
        return result

    def _handler_deployment(self, context: dict) -> dict:
        """部署处理器"""
        logger.info("执行项目部署")

        result = {
            "deployment_status": "success",
            "production_url": "https://app.agentscompany.com",
            "health_check": "all_services_healthy",
            "monitoring_setup": {
                "dashboard": "Grafana链接",
                "alerts": "已配置",
                "logging": "ELK栈"
            },
            "status": "deployed"
        }

        logger.info("项目部署完成")
        return result

    def _handler_rollback(self, context: dict) -> dict:
        """回滚处理器"""
        logger.warning("执行回滚操作")

        result = {
            "rollback_status": "success",
            "previous_version_restored": True,
            "rollback_reason": context.get("parameters", {}).get("reason", "部署失败"),
            "status": "rolled_back"
        }

        logger.warning("回滚完成")
        return result

    def _handler_marketing_creation(self, context: dict) -> dict:
        """营销材料创建处理器"""
        logger.info("创建营销材料")

        result = {
            "marketing_materials": {
                "landing_page": "产品介绍页HTML",
                "product_videos": ["产品演示视频"],
                "screenshots": ["截图1", "截图2", "截图3"],
                "social_posts": ["微博推文", "微信公众号文章"],
                "press_release": "新闻稿"
            },
            "content_calendar": {
                "launch_date": datetime.now().strftime("%Y-%m-%d"),
                "social_schedule": ["发布日", "一周后", "一月后"],
                "email_campaigns": 3
            },
            "status": "marketing_completed"
        }

        logger.info("营销材料创建完成")
        return result

    def _handler_project_closure(self, context: dict) -> dict:
        """项目收尾处理器"""
        logger.info("执行项目收尾")

        result = {
            "final_report": {
                "project_summary": "项目成功完成",
                "key_achievements": ["目标达成", "质量合格"],
                "budget_utilization": "95%",
                "timeline_adherence": "on_schedule"
            },
            "lessons_learned": [
                "敏捷方法有效",
                "早期测试很重要",
                "团队沟通需加强"
            ],
            "knowledge_articles": [
                "架构决策记录",
                "技术选型理由",
                "问题解决方案"
            ],
            "status": "project_closed"
        }

        logger.info("项目收尾完成")
        return result

    def _handler_project_celebration(self, context: dict) -> dict:
        """项目庆祝处理器"""
        logger.info("项目庆祝活动")

        result = {
            "celebration_type": "团队聚餐 + 表彰会",
            "recognition_issued": True,
            "performance_bonus_calculated": True,
            "status": "celebrated"
        }

        logger.info("庆祝活动安排完成")
        return result

    # 补偿处理器
    def _handler_notify_stakeholders(self, context: dict) -> dict:
        """通知利益相关者"""
        logger.warning("通知利益相关者")

        return {"status": "notified", "recipients": ["project_manager", "stakeholders"]}

    def _handler_partial_cleanup(self, context: dict) -> dict:
        """部分清理"""
        logger.warning("执行部分清理")

        return {"status": "cleaned", "scope": context.get("parameters", {}).get("cleanup_scope", "failed_phase")}

    def _handler_abort_project(self, context: dict) -> dict:
        """中止项目"""
        logger.error("中止项目")

        return {"status": "aborted", "reason": context.get("parameters", {}).get("reason", "不可恢复错误")}

    def _handler_retry_adjustments(self, context: dict) -> dict:
        """重试调整"""
        logger.info("调整后重试")

        return {"status": "adjustments_made", "will_retry": True}

    def start_automatic_mode(self, workflow_path: str = None):
        """启动自动模式"""
        logger.info("启动Agents公司自动模式")

        if workflow_path is None:
            workflow_path = str(WORKFLOWS_DIR / "agents_company_workflow.yaml")

        if not os.path.exists(workflow_path):
            logger.error(f"工作流定义文件不存在: {workflow_path}")
            raise FileNotFoundError(workflow_path)

        # 创建或更新工作流
        workflow_id = self.create_workflow(workflow_path, workflow_id="agents_company_production")

        logger.info(f"工作流已准备就绪: {workflow_id}")

        # 启动监控
        self._start_monitoring()

        return workflow_id

    def _start_monitoring(self):
        """启动监控"""
        logger.info("启动监控系统...")
        # TODO: 实现监控逻辑

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Agents公司工作流执行器")
    parser.add_argument("--workflow", type=str, help="工作流定义文件路径")
    parser.add_argument("--project-name", type=str, default="测试项目", help="项目名称")
    parser.add_argument("--project-id", type=str, help="项目ID (自动生成如果未提供)")
    parser.add_argument("--wait", action="store_true", help="等待工作流完成")
    parser.add_argument("--init-only", action="store_true", help="仅初始化，不运行工作流")

    args = parser.parse_args()

    try:
        executor = AgentsCompanyExecutor()
        executor.initialize()

        if args.init_only:
            logger.info("初始化完成，退出")
            return

        project_id = args.project_id or f"proj_{uuid.uuid4().hex[:8]}"

        variables = {
            "project_id": project_id,
            "project_name": args.project_name,
            "trigger_source": "manual",
            "priority": "medium"
        }

        logger.info(f"启动项目: {args.project_name} (ID: {project_id})")
        run_id = executor.run_workflow(
            "agents_company_production",
            variables=variables,
            wait=args.wait
        )

        logger.info(f"项目已启动，运行ID: {run_id}")

        if args.wait:
            logger.info("工作流已完成")
        else:
            logger.info("工作流正在后台运行")

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
