# 众包协作与团队管理模块模式

## 适用场景
为AIGC/数据生产平台添加众包管理、子团队、用户Profile管理功能

## 模块架构（5层）

### 层1: 核心模块（backend/core/）
| 文件 | 职责 | API端点 |
|------|------|---------|
| `crowdsource.py` | 众包人员注册/任务分配/提交审核/自动晋升/计费 | 8个 |
| `subteam.py` | 项目内子团队层级(在已有RBAC组织→项目→用户层之上) | 4个 |
| `user_profile.py` | 用户profile/偏好设置/操作历史追踪 | 3个 |

### 层2: 数据模型
```python
# crowdsource.py 核心类型
CrowdWorkerLevel: BEGINNER → JUNIOR → INTERMEDIATE → SENIOR → EXPERT
TaskType: ANNOTATION / REVIEW / CAPTION / QUALITY_CHECK / DATA_COLLECTION
TaskStatus: OPEN → ASSIGNED → IN_PROGRESS → SUBMITTED → REVIEWED → APPROVED/REJECTED → PAID

# subteam.py 核心类型
SubTeam: team_id, name, project_id, lead, members[]

# user_profile.py 核心类型
UserProfile: username, display_name, email, avatar, role, preferences{}
UserAction: action_id, username, action, detail, ref_type, ref_id, timestamp
```

### 层3: API路由（server.py）
```
POST /api/v2/crowd/workers                    — 注册众包人员
GET  /api/v2/crowd/workers                    — 人员列表(可选level过滤)
GET  /api/v2/crowd/workers/{id}              — 人员详情
POST /api/v2/crowd/tasks                     — 创建众包任务
GET  /api/v2/crowd/tasks                     — 任务列表(可选status过滤)
POST /api/v2/crowd/tasks/{id}/assign         — 分配任务给人员
POST /api/v2/crowd/tasks/{id}/submit         — 提交任务结果
POST /api/v2/crowd/tasks/{id}/review         — 审核(通过/拒收)

POST /api/v2/subteams                         — 创建子团队
GET  /api/v2/subteams?project_id=            — 按项目列出子团队
POST /api/v2/subteams/{id}/members           — 添加成员
DELETE /api/v2/subteams/{id}/members/{user}   — 移除成员

GET  /api/v2/profile?username=              — 获取用户Profile
POST /api/v2/profile/preferences            — 更新偏好
GET  /api/v2/profile/actions?username=      — 操作历史
```

### 层4: 自动晋升逻辑
```
tasks_completed >= 100 AND accuracy >= 0.95  → EXPERT
tasks_completed >= 50  AND accuracy >= 0.90  → SENIOR
tasks_completed >= 20  AND accuracy >= 0.85  → INTERMEDIATE
tasks_completed >= 5                         → JUNIOR
default                                       → BEGINNER
```

### 层5: 前端集成
zhiying.html 侧边栏添加 `{id:'crowd', icon:'👥', label:'众包管理'}`
页面结构：el-tabs 人员管理 / 任务管理
关键方法：loadCrowdWorkers/loadCrowdTasks/registerWorker/createTask/assignTask/reviewTask
