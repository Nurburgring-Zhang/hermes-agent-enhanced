#!/usr/bin/env python3
"""
Agents Company 自动运行脚本
启动全自动化生产流程
"""

import argparse
import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path.home() / ".hermes" / "agents_company"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "run.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_full_production(project_name: str, project_id: str = None, workflow: str = None, wait: bool = True):
    """运行完整的生产流程"""
    logger.info("=" * 80)
    logger.info("启动 Agents Company 全自动化生产")
    logger.info(f"项目名称: {project_name}")
    logger.info("=" * 80)

    try:
        from agents_company_executor import AgentsCompanyExecutor
        from employee_selector import EmployeeSelector

        # 1. 初始化执行器
        logger.info("\n[1/4] 初始化执行器...")
        executor = AgentsCompanyExecutor()
        executor.initialize()
        logger.info("✓ 执行器初始化完成")

        # 2. 准备变量
        logger.info("\n[2/4] 准备项目变量...")
        variables = {
            "project_id": project_id or f"proj_{Path(project_name).stem}",
            "project_name": project_name,
            "trigger_source": "manual",
            "priority": "high",
            "target_deadline": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }
        logger.info(f"  项目ID: {variables['project_id']}")
        logger.info(f"  目标完成日期: {variables['target_deadline']}")

        # 3. 加载工作流
        logger.info("\n[3/4] 加载工作流...")
        if workflow is None:
            workflow = str(BASE_DIR / "workflows" / "agents_company_workflow.yaml")

        if not os.path.exists(workflow):
            logger.error(f"工作流文件不存在: {workflow}")
            return False

        # 注册自定义工作流
        workflow_id = "agents_company_production"
        executor.create_workflow(workflow, workflow_id=workflow_id)
        logger.info(f"✓ 工作流已加载: {workflow_id}")

        # 4. 启动监控面板（后台）
        logger.info("\n[4/4] 启动监控系统...")
        try:
            import subprocess
            dashboard_proc = subprocess.Popen(
                [sys.executable, str(BASE_DIR / "company_dashboard.py"), "--port", "4000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info("✓ 监控面板已启动 (http://localhost:4000)")
        except Exception as e:
            logger.warning(f"⚠ 无法启动监控面板: {e}")

        # 5. 运行工作流
        logger.info("\n" + "=" * 80)
        logger.info("开始执行工作流...")
        logger.info("=" * 80 + "\n")

        run_id = executor.run_workflow(workflow_id, variables=variables, wait=wait)

        if wait:
            logger.info("\n" + "=" * 80)
            logger.info("✅ 工作流执行完成")
            logger.info(f"运行ID: {run_id}")
            logger.info("=" * 80)
        else:
            logger.info("\n" + "=" * 80)
            logger.info("🚀 工作流已启动（异步模式）")
            logger.info(f"运行ID: {run_id}")
            logger.info("监控面板: http://localhost:4000")
            logger.info("=" * 80)

        return True

    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.info("请确保已经运行初始化脚本:")
        logger.info("  python ~/.hermes/agents_company/init_company.py")
        return False

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        return False

def run_openclaw_production(openclaw_path: str = "D:\\openclaw"):
    """运行OpenClaw产品自动生产"""
    logger.info("=" * 80)
    logger.info("OpenClaw 产品自动生产流程")
    logger.info("=" * 80)

    openclaw_dir = Path(openclaw_path)

    if not openclaw_dir.exists():
        logger.error(f"OpenClaw目录不存在: {openclaw_dir}")
        return False

    # 扫描产品目录
    logger.info(f"\n扫描产品目录: {openclaw_dir}")

    product_files = list(openclaw_dir.rglob("*.product.json"))
    logger.info(f"发现 {len(product_files)} 个产品定义文件")

    if not product_files:
        logger.warning("未发现产品定义文件，跳过生产流程")
        return True

    # 对每个产品启动生产工作流
    for product_file in product_files:
        product_name = product_file.stem
        logger.info(f"\n处理产品: {product_name}")

        # 运行生产工作流
        run_full_production(
            project_name=f"OpenClaw_{product_name}_更新",
            project_id=f"openclaw_{product_name}_{datetime.now().strftime('%Y%m%d')}",
            wait=False  # 异步，不阻塞
        )

    logger.info("\n✓ 所有产品已加入生产队列")
    return True

def main():
    """主函数"""
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Agents Company 自动运行脚本")
    parser.add_argument("--project-name", type=str, help="项目名称")
    parser.add_argument("--project-id", type=str, help="项目ID (自动生成如果未提供)")
    parser.add_argument("--workflow", type=str, help="工作流定义文件路径")
    parser.add_argument("--async", dest="wait", action="store_false",
                       help="异步运行 (不等待完成)")
    parser.add_argument("--openclaw", action="store_true",
                       help="启动OpenClaw自动生产")
    parser.add_argument("--openclaw-path", type=str, default="D:\\openclaw",
                       help="OpenClaw目录路径")
    parser.add_argument("--monitor-only", action="store_true",
                       help="仅启动监控面板")

    args = parser.parse_args()

    if args.monitor_only:
        logger.info("仅启动监控面板...")
        os.system(f"python {BASE_DIR / 'company_dashboard.py'}")
        return

    if args.openclaw:
        run_openclaw_production(args.openclaw_path)
        return

    if not args.project_name:
        # 交互式输入
        print("\n" + "=" * 80)
        print("Agents Company 项目启动")
        print("=" * 80 + "\n")

        project_name = input("请输入项目名称 (或按Enter使用示例项目): ").strip()
        if not project_name:
            project_name = f"示例项目_{datetime.now().strftime('%Y%m%d_%H%M')}"
            print(f"使用项目名称: {project_name}")

        wait_input = input("是否等待工作流完成? (y/n, 默认: y): ").strip().lower()
        wait = wait_input != "n"

        run_full_production(
            project_name=project_name,
            project_id=args.project_id,
            workflow=args.workflow,
            wait=wait
        )
    else:
        run_full_production(
            project_name=args.project_name,
            project_id=args.project_id,
            workflow=args.workflow,
            wait=args.wait
        )

if __name__ == "__main__":
    main()
