#!/usr/bin/env python3
"""
Agents Company 智能员工分配器
根据任务需求和员工能力进行智能匹配
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path.home() / ".hermes" / "agents_company"
DATA_DIR = BASE_DIR / "data"

EMPLOYEES_DB = DATA_DIR / "employees.sqlite"
DEPARTMENTS_DB = DATA_DIR / "departments.sqlite"
COLLAB_DB = DATA_DIR / "collaboration_network.sqlite"

class EmployeeSelector:
    """智能员工选择器"""

    def __init__(self):
        self.employees = {}
        self.departments = {}
        self.collaboration_network = {}
        self._load_data()

    def _load_data(self):
        """从数据库加载所有数据"""
        # 加载部门
        conn = sqlite3.connect(DEPARTMENTS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM departments")
        for row in cursor.fetchall():
            dept_id = row["id"]
            self.departments[dept_id] = {
                "name": row["name"],
                "description": row["description"],
                "responsibilities": json.loads(row["responsibilities"]),
                "required_capabilities": json.loads(row["required_capabilities"]),
                "output_schema": json.loads(row["output_schema"]),
                "quality_criteria": json.loads(row["quality_criteria"]),
                "automation_level": row["automation_level"]
            }
        conn.close()

        # 加载员工
        conn = sqlite3.connect(EMPLOYEES_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees")
        for row in cursor.fetchall():
            emp_id = row["id"]
            self.employees[emp_id] = {
                "id": emp_id,
                "name": row["name"],
                "english_name": row["english_name"],
                "department_id": row["department_id"],
                "position": row["position"],
                "level": row["level"],
                "personality": json.loads(row["personality"]),
                "capabilities": json.loads(row["capabilities"]),
                "performance": json.loads(row["performance"]),
                "collaboration": json.loads(row["collaboration"]),
                "agent_config": json.loads(row["agent_config"])
            }
        conn.close()

        # 加载协作网络
        conn = sqlite3.connect(COLLAB_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM collaboration_edges")
        for row in cursor.fetchall():
            emp_id = row["employee_id"]
            collab_id = row["collaborator_id"]
            if emp_id not in self.collaboration_network:
                self.collaboration_network[emp_id] = {}
            self.collaboration_network[emp_id][collab_id] = {
                "projects_together": row["projects_together"],
                "success_rate": row["success_rate"],
                "trust_score": row["trust_score"],
                "communication_rating": row["communication_rating"],
                "last_collaboration": row["last_collaboration"]
            }
        conn.close()

        print(f"✓ 加载了 {len(self.employees)} 名员工, {len(self.departments)} 个部门, {len(self.collaboration_network)} 个协作关系")

    def select_employees(self, task: dict[str, Any], department_id: int, n: int = 1,
                         existing_team: list[str] = None) -> list[dict[str, Any]]:
        """
        智能选择员工

        Args:
            task: 任务需求字典，包含required_capabilities, task_type等
            department_id: 部门ID
            n: 需要选择的员工数量
            existing_team: 已存在的团队成员ID列表（用于协作网络考虑）

        Returns:
            选中的员工列表（按匹配度排序）
        """
        # 过滤出部门的候选人
        candidates = [
            emp for emp in self.employees.values()
            if emp["department_id"] == department_id
        ]

        if not candidates:
            raise ValueError(f"部门 {department_id} 没有可用员工")

        # 计算每个候选人的匹配分数
        scored_candidates = []
        for emp in candidates:
            score = self._calculate_match_score(emp, task, existing_team or [])
            scored_candidates.append((emp, score))

        # 按分数排序（降序）
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # 返回前n个
        return [emp for emp, score in scored_candidates[:n]]

    def _calculate_match_score(self, employee: dict, task: dict[str, Any],
                               existing_team: list[str]) -> float:
        """
        计算员工与任务的匹配分数

        权重分配：
        - 技能匹配度: 40%
        - 经验相关性: 30%
        - 历史成功率: 20%
        - 协作网络: 10%
        """
        score = 0.0

        # 1. 技能匹配度 (40%)
        score += self._skill_match_score(employee, task) * 0.4

        # 2. 经验相关性 (30%)
        score += self._experience_relevance(employee, task) * 0.3

        # 3. 历史成功率 (20%)
        score += self._performance_score(employee) * 0.2

        # 4. 协作网络 (10%)
        score += self._collaboration_score(employee, existing_team) * 0.1

        # 5. 性格匹配调整（任务类型）
        if task.get("requires_creativity", False):
            score += employee["personality"]["big5"]["openness"] * 0.05
        if task.get("requires_teamwork", False):
            score += employee["personality"]["big5"]["agreeableness"] * 0.05
        if task.get("requires_leadership", False):
            score += employee["personality"]["big5"]["extraversion"] * 0.03

        # 6. 级别匹配（优先级）
        required_level = task.get("required_level", "Mid")
        level_scores = {"Junior": 0.5, "Mid": 0.7, "Senior": 0.85, "Lead": 0.95, "Principal": 1.0, "Director": 0.9}
        level_score = level_scores.get(employee["level"], 0.7)
        score += level_score * 0.02

        return min(score, 1.0)  # 分数上限1.0

    def _skill_match_score(self, employee: dict, task: dict) -> float:
        """计算技能匹配度"""
        required_skills = task.get("required_capabilities", [])

        if not required_skills:
            return 0.5  # 如果没有指定技能要求，给中等分数

        # 员工技能字典
        emp_skills = {s["name"]: s["level"] for s in employee["capabilities"]}

        total_score = 0.0
        total_weight = 0.0

        for skill_req in required_skills:
            skill_name = skill_req["name"]
            required_level = skill_req.get("required_level", 1)
            weight = skill_req.get("weight", 1.0)

            if skill_name in emp_skills:
                emp_level = emp_skills[skill_name]
                # 标准化到0-1：如果员工级别>=要求级别，得满分；否则按比例
                skill_score = min(emp_level / required_level, 1.0)
            else:
                skill_score = 0.0

            total_score += skill_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _experience_relevance(self, employee: dict, task: dict) -> float:
        """计算经验相关性"""
        # 员工完成的项目数
        projects_completed = employee["performance"]["projects_completed"]
        success_rate = employee["performance"]["success_rate"]

        # 基础分数：项目经验
        if projects_completed >= 20:
            exp_score = 0.9
        elif projects_completed >= 10:
            exp_score = 0.7
        elif projects_completed >= 5:
            exp_score = 0.5
        elif projects_completed >= 1:
            exp_score = 0.3
        else:
            exp_score = 0.1

        # 成功率调整
        exp_score *= success_rate

        # 任务类型相关性（基于职位）
        task_type = task.get("task_type", "")
        position_match = self._position_task_match(employee["position"], task_type)
        exp_score *= position_match

        return exp_score

    def _position_task_match(self, position: str, task_type: str) -> float:
        """职位与任务类型匹配度"""
        # 简化的匹配矩阵
        position_categories = {
            "架构师": ["tech_architecture", "system_design", "code_review"],
            "高级工程师": ["development", "implementation", "debugging"],
            "产品经理": ["product_spec", "requirements", "prioritization"],
            "项目经理": ["planning", "coordination", "tracking"],
            "测试工程师": ["testing", "qa", "validation"],
            "DevOps工程师": ["deployment", "infrastructure", "ci_cd"],
            "设计师": ["design", "ui_ux", "prototyping"],
        }

        for pos_key, types in position_categories.items():
            if pos_key in position:
                if task_type in types:
                    return 1.0
                if any(t in task_type for t in types):
                    return 0.8

        return 0.5  # 默认中等匹配

    def _performance_score(self, employee: dict) -> float:
        """计算历史表现分数"""
        perf = employee["performance"]

        # 综合评分
        success_rate = perf["success_rate"]
        avg_rating = perf["avg_rating"] / 5.0  # 归一化到0-1
        quality_score = perf.get("quality_score", 0.8)

        # 加权平均
        perf_score = (success_rate * 0.5 + avg_rating * 0.3 + quality_score * 0.2)

        return perf_score

    def _collaboration_score(self, employee: dict, existing_team: list[str]) -> float:
        """计算与现有团队的协作分数"""
        if not existing_team:
            return 0.5  # 如果没有团队成员，给中等分数

        emp_id = employee["id"]
        collab_network = self.collaboration_network.get(emp_id, {})

        total_score = 0.0
        relevant_collabs = 0

        for team_member_id in existing_team:
            if team_member_id in collab_network:
                collab = collab_network[team_member_id]
                # 协作分数 = (合作项目数/10 + 信任度 + 沟通评分) / 3
                collab_score = (
                    min(collab["projects_together"] / 10.0, 1.0) +
                    collab["trust_score"] +
                    collab["communication_rating"]
                ) / 3.0
                total_score += collab_score
                relevant_collabs += 1

        if relevant_collabs > 0:
            return total_score / relevant_collabs
        return 0.3  # 如果没有协作历史，给较低分数

    def select_team_for_task(self, task: dict[str, Any], department_id: int,
                            team_size: int = 1) -> list[dict[str, Any]]:
        """
        为任务选择整个团队（考虑团队内部协作）

        Args:
            task: 任务需求
            department_id: 部门ID
            team_size: 团队大小

        Returns:
            选中的团队成员列表
        """
        if team_size == 1:
            return self.select_employees(task, department_id, 1)

        # 对于团队选择，使用启发式方法：
        # 1. 选择最佳员工作为负责人
        # 2. 选择与负责人协作好的其他员工
        # 3. 确保技能覆盖

        selected_team = []

        # 第一步：选择负责人（分数最高的）
        candidates = self.select_employees(task, department_id, n=min(10, len(self.employees)))
        leader = candidates[0]
        selected_team.append(leader)
        leader_id = leader["id"]

        # 第二步：选择团队成员（与负责人协作好的）
        collab_scores = []
        leader_collabs = self.collaboration_network.get(leader_id, {})

        for emp in self.employees.values():
            if emp["department_id"] != department_id:
                continue
            if emp["id"] == leader_id:
                continue
            if emp in selected_team:
                continue

            if emp["id"] in leader_collabs:
                trust_score = leader_collabs[emp["id"]]["trust_score"]
                collab_scores.append((emp, trust_score))
            else:
                collab_scores.append((emp, 0.3))  # 没有协作历史，给低分

        # 按协作分数排序
        collab_scores.sort(key=lambda x: x[1], reverse=True)

        # 添加团队成员直到达到目标大小
        for emp, score in collab_scores:
            if len(selected_team) >= team_size:
                break
            selected_team.append(emp)

        return selected_team

    def get_best_employee_for_role(self, role_name: str, department_name: str = None) -> dict | None:
        """为指定角色找到最佳员工"""
        # 找到部门ID
        dept_id = None
        if department_name:
            for d_id, d in self.departments.items():
                if d["name"] == department_name:
                    dept_id = d_id
                    break
        else:
            # 尝试从职位名称推断部门
            role_lower = role_name.lower()
            for d_id, d in self.departments.items():
                if any(keyword in role_lower for keyword in ["开发", "工程", "技术"]):
                    if "研发" in d["name"] or "工程" in d["name"]:
                        dept_id = d_id
                        break

        if not dept_id:
            return None

        # 查找职位匹配且级别最高的员工
        candidates = []
        for emp in self.employees.values():
            if emp["department_id"] == dept_id:
                if role_name.lower() in emp["position"].lower():
                    candidates.append(emp)

        if not candidates:
            return None

        # 按级别和表现排序
        candidates.sort(key=lambda e: (
            ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"].index(e["level"]),
            e["performance"]["success_rate"]
        ), reverse=True)

        return candidates[0]

    def get_employee_by_id(self, emp_id: str) -> dict | None:
        """根据ID获取员工信息"""
        return self.employees.get(emp_id)

    def get_department_employees(self, department_id: int) -> list[dict]:
        """获取部门所有员工"""
        return [emp for emp in self.employees.values() if emp["department_id"] == department_id]

    def get_employee_stats(self) -> dict[str, Any]:
        """获取员工统计信息"""
        stats = {
            "total_employees": len(self.employees),
            "by_department": {},
            "by_level": {},
            "avg_experience": 0.0,
            "avg_success_rate": 0.0
        }

        level_counts = dict.fromkeys(LEVELS, 0)
        total_exp = 0
        total_success = 0

        for emp in self.employees.values():
            # 按部门统计
            dept_name = self.departments[emp["department_id"]]["name"]
            stats["by_department"][dept_name] = stats["by_department"].get(dept_name, 0) + 1

            # 按级别统计
            level_counts[emp["level"]] += 1

            # 经验（项目数）
            total_exp += emp["performance"]["projects_completed"]
            total_success += emp["performance"]["success_rate"]

        stats["by_level"] = level_counts
        stats["avg_experience"] = total_exp / len(self.employees) if self.employees else 0
        stats["avg_success_rate"] = total_success / len(self.employees) if self.employees else 0

        return stats

# 便捷函数
def select_employee_for_task(task: dict[str, Any], department_id: int,
                           existing_team: list[str] = None) -> dict[str, Any]:
    """为单个任务选择一个员工"""
    selector = EmployeeSelector()
    results = selector.select_employees(task, department_id, n=1, existing_team=existing_team)
    return results[0] if results else None

def select_team_for_task(task: dict[str, Any], department_id: int, team_size: int) -> list[dict]:
    """为任务选择团队"""
    selector = EmployeeSelector()
    return selector.select_team_for_task(task, department_id, team_size)

if __name__ == "__main__":
    # 测试
    print("测试员工分配器...")

    selector = EmployeeSelector()

    # 查看统计
    stats = selector.get_employee_stats()
    print("\n员工统计:")
    print(f"  总数: {stats['total_employees']}")
    print(f"  平均经验项目数: {stats['avg_experience']:.1f}")
    print(f"  平均成功率: {stats['avg_success_rate']:.2%}")
    print("  部门分布:")
    for dept, count in stats["by_department"].items():
        print(f"    {dept}: {count}")

    # 测试选择一个员工
    test_task = {
        "required_capabilities": [
            {"name": "system-architecture", "required_level": 8, "weight": 1.0},
            {"name": "backend-dev", "required_level": 7, "weight": 0.8},
            {"name": "database-design", "required_level": 6, "weight": 0.6}
        ],
        "task_type": "tech_architecture",
        "requires_creativity": True,
        "requires_teamwork": True,
        "required_level": "Senior"
    }

    print("\n测试选择研发部员工进行技术架构任务:")
    selected = selector.select_employees(test_task, department_id=5, n=3)
    for i, emp in enumerate(selected, 1):
        print(f"  {i}. {emp['name']} ({emp['position']}, {emp['level']}) - 分数匹配")

    print("\n✓ 员工分配器测试完成")
