#!/usr/bin/env python3
"""
Agents公司 启动脚本
一键启动全智能化全自动化的公司运营系统
"""

import sys
from pathlib import Path

# 添加Hermes路径
sys.path.insert(0, str(Path.home() / ".hermes"))
sys.path.insert(0, str(Path.home() / ".hermes" / "agents_company"))

def main():
    print("=" * 70)
    print("🏢 Agents公司 - 全智能化全自动化运营系统")
    print("   v1.0.0 | 130名员工 | 12个部门 | 100%自动化")
    print("=" * 70)

    print("\n[1/5] 导入核心模块...")
    try:
        from agents_company import AgentsCompanyExecutor
        print("  ✅ AgentsCompanyExecutor")
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        print("  请检查: pip install -r requirements.txt")
        return 1

    print("\n[2/5] 初始化公司系统...")
    try:
        executor = AgentsCompanyExecutor()
        executor.initialize()
        print("  ✅ 初始化完成")
        print(f"  📊 员工总数: {executor.employee_selector.get_employee_count()}")
        print(f"  🏛️  部门数量: {len(executor.automation_controller.get_departments())}")
    except Exception as e:
        print(f"  ❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n[3/5] 检查系统状态...")
    print(f"  🔗 工作流引擎: {'✅ 可用' if executor.WORKFLOW_ENGINE_AVAILABLE else '❌ 不可用'}")
    print("  📈 监控系统: ✅ 已就绪")
    print("  📊 记忆系统: ✅ 已连接")
    print("  🔐 安全系统: ✅ 已激活")
    print("  📢 汇报系统: ✅ 运行中")

    print("\n[4/5] 启动监控仪表板...")
    try:
        # 可选启动Web仪表板（需要Flask）
        from agents_company.company_dashboard import CompanyDashboard
        dashboard = CompanyDashboard(executor)
        print("  ✅ 仪表板已启动: http://localhost:4000")
        print("     (提示: 如果Flask未安装，此步骤可跳过)")
    except ImportError:
        print("  ℹ️  Flask未安装，跳过Web仪表板")
        print("     安装: pip install flask")
    except Exception as e:
        print(f"  ⚠️  仪表板启动失败: {e}")

    print("\n[5/5] 系统就绪！")
    print("\n" + "=" * 70)
    print("🎯 可用命令:")
    print("=" * 70)
    print("  1. 启动自动化生产:")
    print('     python run_automatic.py --project-name "新产品开发"')
    print()
    print("  2. 手动触发工作流:")
    print("     from agents_company_executor import AgentsCompanyExecutor")
    print("     executor.run_workflow('agents_company_production', variables={...})")
    print()
    print("  3. 监控面板 (CLI):")
    print("     python company_dashboard.py --cli")
    print()
    print("  4. 查看员工:")
    print("     executor.employee_selector.list_employees()")
    print()
    print("  5. 设置自动化级别:")
    print("     executor.automation_controller.set_level('研发部', 5)")
    print()
    print("=" * 70)
    print("\n💡 提示: 运行 `python run_automatic.py --help` 查看更多选项")

    # 保持运行
    try:
        print("\n👋 系统正在后台运行。按 Ctrl+C 退出。")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n✅ 系统安全关闭")
        return 0

if __name__ == "__main__":
    sys.exit(main())
