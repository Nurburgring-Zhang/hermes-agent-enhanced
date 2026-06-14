#!/usr/bin/env python3
"""
Agents Company 初始化脚本
创建完整的数字员工系统：数据库、员工、工作流、处理器等
"""

import datetime
import json
import random
import sqlite3
from pathlib import Path

# 确保工作目录
BASE_DIR = Path.home() / ".hermes" / "agents_company"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 数据库路径
EMPLOYEES_DB = DATA_DIR / "employees.sqlite"
DEPARTMENTS_DB = DATA_DIR / "departments.sqlite"
COLLAB_DB = DATA_DIR / "collaboration_network.sqlite"

#员工数量
TOTAL_EMPLOYEES = 130
DEPARTMENTS_COUNT = 12

# 技能库
ALL_SKILLS = {
    "programming": ["python", "javascript", "java", "go", "rust", "c++", "typescript", "swift", "kotlin", "php"],
    "web": ["react", "vue", "angular", "node.js", "django", "flask", "fastapi", "spring", "laravel", "rails"],
    "mobile": ["ios", "android", "flutter", "react-native", "kotlin", "swift"],
    "data": ["sql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch", "neo4j", "cassandra"],
    "ml_ai": ["tensorflow", "pytorch", "scikit-learn", "openai", "huggingface", "computer-vision", "nlp", "recommendation"],
    "devops": ["docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible", "jenkins", "gitlab", "circleci"],
    "testing": ["pytest", "selenium", "cypress", "jest", "junit", "postman", "newman", "load-testing", "security-testing"],
    "management": ["agile", "scrum", "kanban", "waterfall", "risk-management", "resource-planning", "budgeting"],
    "creative": ["ui-design", "ux-design", "graphic-design", "video-editing", "animation", "prototyping", "figma", "sketch"],
    "communication": ["technical-writing", "documentation", "presentation", "negotiation", "conflict-resolution", "team-building"],
}

# MBTI类型
MBTI_TYPES = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]

# 职位等级
LEVELS = ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"]

# 部门定义
DEPARTMENTS = [
    {
        "id": 1,
        "name": "信息采集部",
        "description": "收集外部市场需求和技术趋势，监控竞争对手动态",
        "responsibilities": ["市场调研", "技术趋势分析", "竞品分析", "用户需求采集", "行业报告生成"],
        "required_capabilities": ["research", "analytics", "web-search", "data-mining", "market-analysis"],
        "output_schema": {
            "market_report": {"trends": [], "technologies": [], "competitors": [], "opportunities": []},
            "insights": {"key_findings": [], "recommendations": [], "priority_ranking": []}
        },
        "quality_criteria": {"completeness": 0.9, "accuracy": 0.95, "timeliness": 0.85},
        "automation_level": 5
    },
    {
        "id": 2,
        "name": "运营部",
        "description": "从信息流挖掘需求，转换为产品需求规格书",
        "responsibilities": ["需求分析", "用户故事编写", "产品规格定义", "优先级排序", "需求验证"],
        "required_capabilities": ["product-management", "user-research", "requirements-engineering", "business-analysis"],
        "output_schema": {
            "product_requirements": [
                {"title": "", "description": "", "priority": "high|medium|low", "features": [], "acceptance_criteria": []}
            ]
        },
        "quality_criteria": {"clarity": 0.9, "completeness": 0.85, "feasibility": 0.8},
        "automation_level": 4
    },
    {
        "id": 3,
        "name": "设计部",
        "description": "产品需求转换为产品功能设计文档",
        "responsibilities": ["功能设计", "用户体验设计", "交互设计", "界面设计", "设计系统维护"],
        "required_capabilities": ["ui-design", "ux-design", "interaction-design", "prototyping", "design-system"],
        "output_schema": {
            "design_document": {
                "user_flows": [],
                "wireframes": [],
                "mockups": [],
                "design_specs": {},
                "accessibility_requirements": []
            }
        },
        "quality_criteria": {"usability": 0.9, "consistency": 0.95, "accessibility": 0.9},
        "automation_level": 4
    },
    {
        "id": 4,
        "name": "产品部",
        "description": "功能设计转换为产品形态规格 (PRD)",
        "responsibilities": ["产品规划", "PRD编写", "功能规格定义", "产品路线图", "版本规划"],
        "required_capabilities": ["product-strategy", "roadmap-planning", "prd-writing", "market-strategy", "metrics-analysis"],
        "output_schema": {
            "product_spec": {
                "product_overview": {},
                "features": [],
                "user_personas": [],
                "use_cases": [],
                "success_metrics": [],
                "release_plan": {}
            }
        },
        "quality_criteria": {"strategy_alignment": 0.9, "completeness": 0.85, "clarity": 0.9},
        "automation_level": 4
    },
    {
        "id": 5,
        "name": "研发部",
        "description": "产品形态转换为技术方案和核心代码",
        "responsibilities": ["系统架构设计", "技术选型", "代码实现", "代码审查", "技术文档"],
        "required_capabilities": ["system-architecture", "backend-dev", "frontend-dev", "database-design", "api-design"],
        "output_schema": {
            "technical_design": {
                "architecture_diagram": "",
                "tech_stack": [],
                "api_specs": {},
                "database_schema": {},
                "core_architecture": ""
            },
            "core_code": {"modules": [], "interfaces": [], "algorithms": []}
        },
        "quality_criteria": {"scalability": 0.9, "maintainability": 0.95, "performance": 0.85},
        "automation_level": 5
    },
    {
        "id": 6,
        "name": "项目管理部",
        "description": "制定开发计划（WBS、甘特图）",
        "responsibilities": ["项目规划", "WBS分解", "甘特图制作", "资源分配", "风险管理"],
        "required_capabilities": ["project-management", "wbs", "gantt", "risk-management", "resource-planning"],
        "output_schema": {
            "project_plan": {
                "wbs": [],
                "gantt_chart": {},
                "resource_allocation": {},
                "milestones": [],
                "dependencies": []
            }
        },
        "quality_criteria": {"completeness": 0.9, "realism": 0.85, "clarity": 0.9},
        "automation_level": 4
    },
    {
        "id": 7,
        "name": "项目开发部",
        "description": "执行开发任务",
        "responsibilities": ["功能开发", "单元测试", "代码集成", "技术难题解决", "代码优化"],
        "required_capabilities": ["full-stack-dev", "backend-dev", "frontend-dev", "mobile-dev", "api-integration"],
        "output_schema": {
            "developed_features": [
                {"feature_id": "", "code_files": [], "tests": [], "documentation": "", "status": "completed|in-progress|blocked"}
            ]
        },
        "quality_criteria": {"code_quality": 0.9, "test_coverage": 0.8, "documentation": 0.85},
        "automation_level": 5
    },
    {
        "id": 8,
        "name": "项目支持部",
        "description": "提供资源协调、风险应对支持",
        "responsibilities": ["资源协调", "问题解决", "风险缓解", "跨部门沟通", "进度跟踪"],
        "required_capabilities": ["coordination", "problem-solving", "risk-management", "communication", "conflict-resolution"],
        "output_schema": {
            "support_report": {
                "issues_identified": [],
                "solutions_proposed": [],
                "resources_allocated": {},
                "risk_mitigation": [],
                "status_updates": []
            }
        },
        "quality_criteria": {"responsiveness": 0.9, "effectiveness": 0.85, "coordination": 0.9},
        "automation_level": 3
    },
    {
        "id": 9,
        "name": "工程部",
        "description": "提供技术基础设施和工具链",
        "responsibilities": ["基础设施管理", "工具链维护", "CI/CD流水线", "环境配置", "技术债务管理"],
        "required_capabilities": ["infrastructure", "devops", "tooling", "ci-cd", "cloud-architecture"],
        "output_schema": {
            "infrastructure_status": {
                "environments": {},
                "tools_available": [],
                "ci_cd_pipelines": [],
                "capacity_metrics": {},
                "maintenance_tasks": []
            }
        },
        "quality_criteria": {"reliability": 0.95, "efficiency": 0.9, "scalability": 0.85},
        "automation_level": 4
    },
    {
        "id": 10,
        "name": "测试与交付部",
        "description": "测试、修复、交付项目",
        "responsibilities": ["质量保证", "测试执行", "缺陷管理", "交付部署", "用户验收测试"],
        "required_capabilities": ["qa", "test-automation", "performance-testing", "security-testing", "deployment"],
        "output_schema": {
            "test_results": {
                "test_cases": [],
                "pass_rate": 0.0,
                "defects": [],
                "coverage": 0.0,
                "quality_score": 0.0
            },
            "delivery_package": {"build_artifacts": [], "deployment_scripts": [], "release_notes": ""}
        },
        "quality_criteria": {"thoroughness": 0.9, "accuracy": 0.95, "completeness": 0.85},
        "automation_level": 3
    },
    {
        "id": 11,
        "name": "宣传媒体部",
        "description": "为成品制作营销材料",
        "responsibilities": ["营销内容创建", "视觉设计", "视频制作", "文案撰写", "社交媒体内容"],
        "required_capabilities": ["content-creation", "video-production", "graphic-design", "copywriting", "social-media"],
        "output_schema": {
            "marketing_materials": {
                "landing_page": "",
                "videos": [],
                "images": [],
                "copy": {},
                "social_posts": []
            }
        },
        "quality_criteria": {"creativity": 0.9, "brand_consistency": 0.95, "engagement": 0.85},
        "automation_level": 4
    },
    {
        "id": 12,
        "name": "支持部",
        "description": "HR、财务、行政等通用支持",
        "responsibilities": ["人力资源管理", "财务管理", "行政管理", "合规审计", "员工福利"],
        "required_capabilities": ["hr", "finance", "administration", "compliance", "payroll"],
        "output_schema": {
            "support_services": {
                "hr_records": {},
                "financial_reports": {},
                "admin_tasks": [],
                "compliance_status": {},
                "employee_satisfaction": 0.0
            }
        },
        "quality_criteria": {"accuracy": 0.95, "timeliness": 0.9, "compliance": 0.95},
        "automation_level": 3
    }
]

# 中文姓名生成
SURNAMES = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "郑"]
GIVEN_NAMES = [
    "伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀兰", "霞",
    "平", "刚", "桂英", "颖", "建", "建华", "建国", "桂兰", "欣", "琳", "华", "志强", "建军", "桂芳", "志明", "颖慧", "建平", "建华",
    "鹏", "婷婷", "欢", "刚", "红", "慧", "刚", "晶", "博", "慧", "文", "斌", "凯", "倩", "Chen", "亚历山大", "史蒂夫", "凯文"
]

# 英文名
ENGLISH_NAMES = [
    "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack",
    "Kate", "Leo", "Mia", "Nathan", "Olivia", "Paul", "Quinn", "Ryan", "Sophia", "Tom",
    "Uma", "Victor", "Wendy", "Xander", "Yvonne", "Zoe", "Michael", "Sarah", "John", "Emily"
]

def create_database_schema():
    """创建所有数据库表结构"""
    print("创建数据库架构...")

    # 员工数据库
    conn = sqlite3.connect(EMPLOYEES_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            english_name TEXT,
            department_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            level TEXT NOT NULL,
            personality TEXT NOT NULL,  -- JSON
            capabilities TEXT NOT NULL,  -- JSON
            performance TEXT NOT NULL,  -- JSON
            collaboration TEXT NOT NULL,  -- JSON
            agent_config TEXT NOT NULL,  -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dept ON employees(department_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_level ON employees(level)")
    conn.commit()
    conn.close()

    # 部门数据库
    conn = sqlite3.connect(DEPARTMENTS_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            responsibilities TEXT NOT NULL,  -- JSON
            required_capabilities TEXT NOT NULL,  -- JSON
            output_schema TEXT NOT NULL,  -- JSON
            quality_criteria TEXT NOT NULL,  -- JSON
            automation_level INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    # 协作网络数据库
    conn = sqlite3.connect(COLLAB_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collaboration_edges (
            employee_id TEXT NOT NULL,
            collaborator_id TEXT NOT NULL,
            projects_together INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            trust_score REAL DEFAULT 0.0,
            communication_rating REAL DEFAULT 0.0,
            last_collaboration TIMESTAMP,
            PRIMARY KEY (employee_id, collaborator_id),
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            FOREIGN KEY (collaborator_id) REFERENCES employees(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp ON collaboration_edges(employee_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_collab ON collaboration_edges(collaborator_id)")
    conn.commit()
    conn.close()

    print("✓ 数据库架构创建完成")

def generate_big5():
    """生成Big Five人格特质"""
    return {
        "openness": round(random.uniform(0.3, 0.9), 2),
        "conscientiousness": round(random.uniform(0.4, 0.95), 2),
        "extraversion": round(random.uniform(0.2, 0.9), 2),
        "agreeableness": round(random.uniform(0.3, 0.95), 2),
        "neuroticism": round(random.uniform(0.1, 0.7), 2)
    }

def generate_traits(mbti):
    """基于MBTI生成特质"""
    traits = []
    # 根据MBTI维度添加特质
    if "I" in mbti:
        traits.extend(["独立思考", "深度专注", "独立工作"])
    else:
        traits.extend(["善于交际", "团队协作", "外向表达"])

    if "N" in mbti:
        traits.extend(["战略思维", "创新思考", "未来导向"])
    else:
        traits.extend(["注重细节", "务实执行", "现实检验"])

    if "F" in mbti:
        traits.extend(["共情能力强", "注重和谐", "价值驱动"])
    else:
        traits.extend(["逻辑分析", "客观决策", "效率优先"])

    if "J" in mbti:
        traits.extend(["计划性强", "有条不紊", "决策果断"])
    else:
        traits.extend(["灵活应变", "探索开放", "延迟决策"])

    return traits

def generate_work_style(personality, department_id):
    """生成工作风格"""
    base_style = {
        "remote_work": random.choice(["preferred", "neutral", "office-only"]),
        "working_hours": random.choice(["flexible", "strict", "night-owl", "early-bird"]),
        "communication_preference": random.choice(["async", "sync", "mixed"]),
        "decision_making": random.choice(["data-driven", "intuitive", "consensus", "hierarchical"]),
        "problem_solving": random.choice(["analytical", "creative", "systematic", "experimental"])
    }

    # 根据部门调整
    if department_id in [1, 9]:  # 技术部门
        base_style["code_review_preference"] = random.choice(["thorough", "light-touch", "skip"])
        base_style["documentation"] = random.choice(["comprehensive", "minimal", "code-as-doc"])

    if department_id in [6, 7]:  # 项目开发
        base_style["sprint_participation"] = random.choice(["full", "partial", "observer"])
        base_style["status_reporting"] = random.choice(["daily", "weekly", "as-needed"])

    return base_style

def generate_skills(department_id, position, level):
    """生成技能矩阵"""
    capabilities = []

    # 根据部门确定技能类别
    skill_categories = {
        1: ["research", "analytics", "web-search", "data-mining"],
        2: ["product-management", "user-research", "requirements-engineering"],
        3: ["ui-design", "ux-design", "prototyping", "design-system"],
        4: ["product-strategy", "roadmap-planning", "prd-writing"],
        5: ["system-architecture", "backend-dev", "database-design"],
        6: ["project-management", "wbs", "gantt", "risk-management"],
        7: ["full-stack-dev", "backend-dev", "frontend-dev", "testing"],
        8: ["coordination", "problem-solving", "risk-management"],
        9: ["infrastructure", "devops", "ci-cd", "cloud-architecture"],
        10: ["qa", "test-automation", "performance-testing", "deployment"],
        11: ["content-creation", "graphic-design", "copywriting", "video-production"],
        12: ["hr", "finance", "administration", "compliance"]
    }

    # 核心技能
    core_skills = skill_categories.get(department_id, ["general"])
    for skill in core_skills:
        level_value = random.randint(max(1, level-2), min(10, level+2))
        experience = random.randint(0, 5000)
        capabilities.append({
            "name": skill,
            "level": level_value,
            "experience": experience,
            "certified": random.choice([True, False])
        })

    # 添加一些跨部门技能
    if random.random() < 0.3:
        cross_skill = random.choice(list(ALL_SKILLS.keys()))
        capabilities.append({
            "name": cross_skill,
            "level": random.randint(1, 5),
            "experience": random.randint(0, 1000),
            "certified": False
        })

    return capabilities

def generate_performance():
    """生成性能数据"""
    return {
        "projects_completed": random.randint(0, 50),
        "success_rate": round(random.uniform(0.6, 0.98), 3),
        "avg_rating": round(random.uniform(3.0, 5.0), 2),
        "quality_score": round(random.uniform(0.7, 0.98), 3),
        "delivery_speed": round(random.uniform(0.6, 0.95), 3),
        "innovation_score": round(random.uniform(0.3, 0.9), 3)
    }

def generate_collaboration():
    """生成协作数据"""
    return {
        "teamwork_rating": round(random.uniform(0.5, 0.95), 2),
        "communication_style": random.choice(["direct", "diplomatic", "analytical", "emotional", "structured"]),
        "preferred_roles": random.sample(["leader", "contributor", "reviewer", "mentor", "innovator"], k=random.randint(1, 3)),
        "conflict_handling": random.choice(["collaborative", "compromising", "accommodating", "competing", "avoiding"]),
        "knowledge_sharing": round(random.uniform(0.4, 0.95), 2)
    }

def generate_agent_config(position, level):
    """生成Agent配置"""
    # 根据级别选择模型
    if level in ["Principal", "Director"]:
        provider = "openrouter"
        model = random.choice(["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "google/gemini-2.0-flash-001"])
        temperature = round(random.uniform(0.3, 0.7), 2)
        max_tokens = 8000
    elif level in ["Senior", "Lead"]:
        provider = "openrouter"
        model = random.choice(["anthropic/claude-3-haiku", "openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"])
        temperature = round(random.uniform(0.5, 0.8), 2)
        max_tokens = 4000
    else:
        provider = "openrouter"
        model = random.choice(["anthropic/claude-3-haiku", "meta-llama/llama-3.1-8b-instruct", "google/gemma-2-9b-it"])
        temperature = round(random.uniform(0.7, 1.0), 2)
        max_tokens = 2000

    return {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "system_prompt_template": f"你是{position}，专业、高效、协作。你的工作风格是{{work_style}}。请以最高质量完成工作。",
        "retry_policy": {"max_attempts": 3, "backoff_factor": 2.0},
        "timeout_seconds": 300 if level in ["Principal", "Director"] else 180
    }

def generate_employee(dept, idx):
    """生成单个员工"""
    emp_id = f"emp_{idx:03d}"

    # 基本信息
    if random.random() < 0.7:  # 70%中文名
        name = random.choice(SURNAMES) + random.choice(GIVEN_NAMES)
        english_name = None
    else:  # 30%英文名
        name = random.choice(ENGLISH_NAMES)
        english_name = f"{name}_CN"

    # 部门和职位
    department_id = dept["id"]

    # 根据部门生成职位和级别
    positions_by_dept = {
        1: ["市场研究员", "技术分析师", "竞品分析专家", "数据采集员"],
        2: ["业务分析师", "需求工程师", "产品专员", "用户研究员"],
        3: ["UI设计师", "UX设计师", "交互设计师", "设计系统专家"],
        4: ["产品经理", "高级产品经理", "产品总监", "产品策略师"],
        5: ["架构师", "高级工程师", "技术专家", "代码架构师"],
        6: ["项目经理", "高级项目经理", "项目总监", "项目治理专家"],
        7: ["开发工程师", "高级开发", "开发主管", "技术负责人"],
        8: ["资源协调员", "风险经理", "支持专家", "运营协调员"],
        9: ["DevOps工程师", "SRE工程师", "架构师", "基础设施专家"],
        10: ["测试工程师", "QA专家", "测试架构师", "质量保证经理"],
        11: ["内容创作者", "设计师", "视频编辑", "营销专家"],
        12: ["HR专员", "财务专员", "行政专员", "合规专员"]
    }

    positions = positions_by_dept.get(department_id, ["专员", "分析师", "工程师"])
    position = random.choice(positions)

    # 级别分布（偏向中高级）
    level_weights = [0.1, 0.25, 0.35, 0.2, 0.08, 0.02]  # Junior 到 Director
    level = random.choices(LEVELS, weights=level_weights)[0]

    # 人格
    mbti = random.choice(MBTI_TYPES)
    big5 = generate_big5()
    traits = generate_traits(mbti)

    # 能力
    level_num = LEVELS.index(level) + 1
    capabilities = generate_skills(department_id, position, level_num)

    # 表现
    performance = generate_performance()

    # 协作
    collaboration = generate_collaboration()

    # Agent配置
    agent_config = generate_agent_config(position, level)

    # 工作风格
    work_style = generate_work_style(big5, department_id)

    # 组合personality
    personality = {
        "mbti": mbti,
        "big5": big5,
        "traits": traits,
        "work_style": work_style
    }

    employee = {
        "id": emp_id,
        "name": name,
        "english_name": english_name,
        "department_id": department_id,
        "position": position,
        "level": level,
        "personality": json.dumps(personality, ensure_ascii=False),
        "capabilities": json.dumps(capabilities, ensure_ascii=False),
        "performance": json.dumps(performance, ensure_ascii=False),
        "collaboration": json.dumps(collaboration, ensure_ascii=False),
        "agent_config": json.dumps(agent_config, ensure_ascii=False),
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat()
    }

    return employee

def generate_all_employees():
    """生成所有130名员工"""
    print(f"生成 {TOTAL_EMPLOYEES} 名员工数据...")

    conn = sqlite3.connect(EMPLOYEES_DB)
    cursor = conn.cursor()

    # 为每个部门分配员工
    employees_per_dept = TOTAL_EMPLOYEES // DEPARTMENTS_COUNT
    remainder = TOTAL_EMPLOYEES % DEPARTMENTS_COUNT

    emp_idx = 1
    for dept in DEPARTMENTS:
        count = employees_per_dept + (1 if remainder > 0 else 0)
        remainder -= 1

        print(f"  部门 {dept['name']}: {count} 名员工")

        for i in range(count):
            employee = generate_employee(dept, emp_idx)
            cursor.execute("""
                INSERT INTO employees
                (id, name, english_name, department_id, position, level,
                 personality, capabilities, performance, collaboration,
                 agent_config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee["id"], employee["name"], employee["english_name"],
                employee["department_id"], employee["position"], employee["level"],
                employee["personality"], employee["capabilities"],
                employee["performance"], employee["collaboration"],
                employee["agent_config"], employee["created_at"], employee["updated_at"]
            ))
            emp_idx += 1

        if emp_idx > TOTAL_EMPLOYEES:
            break

    conn.commit()
    conn.close()
    print(f"✓ 已生成 {emp_idx-1} 名员工")

def initialize_departments():
    """初始化部门数据"""
    print("初始化部门数据...")

    conn = sqlite3.connect(DEPARTMENTS_DB)
    cursor = conn.cursor()

    for dept in DEPARTMENTS:
        cursor.execute("""
            INSERT INTO departments
            (id, name, description, responsibilities, required_capabilities,
             output_schema, quality_criteria, automation_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dept["id"], dept["name"], dept["description"],
            json.dumps(dept["responsibilities"], ensure_ascii=False),
            json.dumps(dept["required_capabilities"], ensure_ascii=False),
            json.dumps(dept["output_schema"], ensure_ascii=False),
            json.dumps(dept["quality_criteria"], ensure_ascii=False),
            dept["automation_level"],
            datetime.datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    print(f"✓ 已初始化 {len(DEPARTMENTS)} 个部门")

def initialize_collaboration_network():
    """初始化协作网络"""
    print("初始化协作网络...")

    # 读取所有员工
    conn = sqlite3.connect(EMPLOYEES_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, department_id FROM employees")
    employees = cursor.fetchall()
    conn.close()

    # 生成协作关系
    conn = sqlite3.connect(COLLAB_DB)
    cursor = conn.cursor()

    # 每个员工与同部门的2-5名其他员工建立协作关系
    # 以及跨部门的1-3名员工
    for emp_id, dept_id in employees:
        # 同部门协作
        same_dept = [e for e in employees if e[1] == dept_id and e[0] != emp_id]
        num_same = random.randint(2, min(5, len(same_dept)))
        for collaborator in random.sample(same_dept, num_same):
            cursor.execute("""
                INSERT OR REPLACE INTO collaboration_edges
                (employee_id, collaborator_id, projects_together, success_rate,
                 trust_score, communication_rating, last_collaboration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                emp_id, collaborator[0],
                random.randint(1, 20),
                round(random.uniform(0.5, 0.95), 3),
                round(random.uniform(0.4, 0.9), 3),
                round(random.uniform(0.5, 0.95), 3),
                datetime.datetime.now().isoformat()
            ))

        # 跨部门协作
        other_depts = [e for e in employees if e[1] != dept_id]
        num_other = random.randint(1, min(3, len(other_depts)))
        for collaborator in random.sample(other_depts, num_other):
            cursor.execute("""
                INSERT OR REPLACE INTO collaboration_edges
                (employee_id, collaborator_id, projects_together, success_rate,
                 trust_score, communication_rating, last_collaboration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                emp_id, collaborator[0],
                random.randint(1, 10),
                round(random.uniform(0.4, 0.85), 3),
                round(random.uniform(0.3, 0.8), 3),
                round(random.uniform(0.4, 0.85), 3),
                datetime.datetime.now().isoformat()
            ))

    conn.commit()

    # 最后单独查询总数
    cursor.execute("SELECT COUNT(*) FROM collaboration_edges")
    total_edges = cursor.fetchone()[0]

    conn.close()
    print(f"✓ 已创建 {total_edges} 条协作关系")

def verify_databases():
    """验证数据库"""
    print("验证数据库...")

    # 检查员工数
    conn = sqlite3.connect(EMPLOYEES_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM employees")
    emp_count = cursor.fetchone()[0]
    conn.close()

    # 检查部门数
    conn = sqlite3.connect(DEPARTMENTS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM departments")
    dept_count = cursor.fetchone()[0]
    conn.close()

    # 检查协作关系
    conn = sqlite3.connect(COLLAB_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM collaboration_edges")
    collab_count = cursor.fetchone()[0]
    conn.close()

    print(f"✓ 员工数量: {emp_count} (目标: {TOTAL_EMPLOYEES})")
    print(f"✓ 部门数量: {dept_count} (目标: {DEPARTMENTS_COUNT})")
    print(f"✓ 协作关系: {collab_count}")

    assert emp_count == TOTAL_EMPLOYEES, f"员工数量不匹配: {emp_count} != {TOTAL_EMPLOYEES}"
    assert dept_count == DEPARTMENTS_COUNT, f"部门数量不匹配: {dept_count} != {DEPARTMENTS_COUNT}"
    print("✓ 所有数据库验证通过")

def main():
    """主函数"""
    print("=" * 60)
    print("Agents公司数字员工系统初始化")
    print("=" * 60)
    print(f"工作目录: {BASE_DIR}")
    print()

    # 删除旧数据库（如果存在）
    for db in [EMPLOYEES_DB, DEPARTMENTS_DB, COLLAB_DB]:
        if db.exists():
            db.unlink()
            print(f"已删除旧数据库: {db}")

    print()

    # 1. 创建架构
    create_database_schema()

    # 2. 初始化部门
    initialize_departments()

    # 3. 生成员工
    generate_all_employees()

    # 4. 初始化协作网络
    initialize_collaboration_network()

    # 5. 验证
    verify_databases()

    print()
    print("=" * 60)
    print("初始化完成！")
    print("=" * 60)
    print("下一步: 创建工作流定义和执行器")
    print("运行: python ~/.hermes/agents_company/init_company.py")

if __name__ == "__main__":
    main()
