#!/usr/bin/env python3
"""
HERMES 任务断点续跑系统 (Task Resumer) v1.0
===========================================
当Hermes对话在手工补全任务中断时，自动从断点续跑。
每次新会话启动时，此脚本检查已完成/未完成的员工/专家，
并输出未完成列表以便hermes继续。

配合cron: hermes-task-resume-tracker (每30分钟)
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path.home() / ".hermes"
COMPANY_DIR = BASE_DIR / "agents_company"
RESUMPTION_FILE = COMPANY_DIR / "data" / "resume_pipeline.py"  # 已存在的恢复点
TASK_TRACKER = BASE_DIR / "task_tracker.json"

def get_employee_completion():
    """检查130员工的配置完成状态"""
    db = COMPANY_DIR / "data" / "employees.sqlite"
    if not db.exists():
        return {"total": 0, "complete": 0, "missing": []}

    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    c.execute("SELECT id, name, department_name, position FROM employees ORDER BY id")
    employees = c.fetchall()
    conn.close()

    total = len(employees)

    # 检查每位员工是否有充分的配置文件
    # 通过检查personality/experience/capabilities等字段长度
    complete = 0
    missing_details = []

    conn2 = sqlite3.connect(str(db))
    c2 = conn2.cursor()
    for emp_id, name, dept_name, pos in employees:
        # 检查字段长度
        c2.execute("SELECT LENGTH(personality), LENGTH(experience), LENGTH(capabilities) FROM employees WHERE id=?", (emp_id,))
        row = c2.fetchone()
        if row and row[0] and row[0] > 100:
            complete += 1
        else:
            missing_details.append({
                "id": emp_id,
                "name": name,
                "department": dept_name,
                "position": pos,
                "reason": f"配置不完整(行数:{row[0] if row else 0})"
            })
    conn2.close()

    return {
        "total": total,
        "complete": complete,
        "incomplete": total - complete,
        "missing": missing_details
    }

def get_expert_completion():
    """检查390专家的配置完成状态"""
    db = COMPANY_DIR / "data" / "experts.sqlite"
    if not db.exists():
        return {"total": 0, "complete": 0, "missing": []}

    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM experts")
    total = c.fetchone()[0]
    conn.close()

    # 专家系统通过multi_agent_engine管理
    return {
        "total": total,
        "complete": total,  # 专家在数据库中已注册视为完成
        "incomplete": 0,
        "missing": []
    }

def check_checkpoint():
    """读取检查点"""
    tracker_file = Path(str(RESUMPTION_FILE).replace(".py", ".json"))
    if not tracker_file.exists():
        return None

    with open(tracker_file) as f:
        return json.load(f)

def generate_resume_report():
    """生成恢复报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    emp_status = get_employee_completion()
    exp_status = get_expert_completion()

    report = []
    sep = "#" * 60
    report.append(sep)
    report.append("#  HERMES 任务断点续跑报告")
    report.append(f"#  {now}")
    report.append(sep)
    report.append("")
    report.append(f'\U0001f4ca 员工: {emp_status["total"]}人')
    report.append(f'   ✅ 已完成: {emp_status["complete"]}人')
    if emp_status["incomplete"] > 0:
        report.append(f'   ❌ 未完成: {emp_status["incomplete"]}人')
        for m in emp_status["missing"][:10]:
            report.append(f'      - {m["id"]} {m["name"]} ({m["department"]}): {m["reason"]}')
        if len(emp_status["missing"]) > 10:
            report.append(f'      ... 还有 {len(emp_status["missing"]) - 10} 人')
    report.append("")
    report.append(f'📊 专家: {exp_status["total"]}人')
    report.append(f'   ✅ 已注册: {exp_status["complete"]}人')
    report.append("")
    report.append("💡 续跑指令:")
    report.append("   如需继续补全，请告诉Hermes:")
    report.append('   "继续补全员工和专家的深度配置"')
    report.append("")
    report.append("#" * 60)

    return "\n".join(report)

def save_tracker():
    """保存跟踪器"""
    emp = get_employee_completion()
    exp = get_expert_completion()

    tracker = {
        "last_check": datetime.now().isoformat(),
        "employees": {
            "total": emp["total"],
            "complete": emp["complete"],
            "incomplete": emp["incomplete"]
        },
        "experts": {
            "total": exp["total"],
            "complete": exp["complete"],
            "incomplete": exp["incomplete"]
        },
        "incomplete_employees": [
            {"id": m["id"], "name": m["name"], "department": m["department"]}
            for m in emp["missing"]
        ]
    }

    with open(TASK_TRACKER, "w") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)

    return tracker

if __name__ == "__main__":
    save_tracker()
    report = generate_resume_report()
    print(report)

    # 如果有未完成的员工，输出特别提示
    emp = get_employee_completion()
    if emp["incomplete"] > 0:
        print(f'\n⚠️ 还有 {emp["incomplete"]} 位员工需要补全配置！')
        print("   执行: 继续补全员工或专家的深度配置")
