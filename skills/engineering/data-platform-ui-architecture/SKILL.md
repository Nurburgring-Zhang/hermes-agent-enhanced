---
name: data-platform-ui-architecture
description: 以用户旅程为中心的AIGC数据平台UI架构设计方法论 — 对标Scale AI/Labelbox/ComfyUI的界面理念。
  覆盖：功能映射→导航层设计→仪表盘布局→工作区格局→响应式策略→三AI互审验收。
  适用于：多功能的AIGC/数据生产/标注平台的UI从零设计或重构、已有项目功能散落在多个页面需要统一导航结构。
triggers:
  - 用户要求"对标Scale AI/Labelbox的界面"
  - 用户对"功能分散在多个页面"表示不满
  - 用户反复说"要丰富！！操作要直观合理"
  - 需要为多模块数据平台设计统一的UI架构
  - "所有的功能都需要正确合理的完整呈现"
  - 从功能开发转向UI集成阶段
  - 用户说"只看到画布没有侧边栏"或"按键没反应"(JS被破坏)
  - 用户要求"常用的功能都要直接的呈现出来"
  - 用户正在多次被要求重设计时拒绝迭代要求重建
  
---

# 数据平台UI架构设计方法论

## 核心理念

对标 Scale AI / Labelbox 的界面设计思想：

1. **常用功能直接放主界面** — 用户最常用的操作不超过3次点击可达
2. **不常用的放菜单** — 左侧导航树用于组织所有功能但不要淹没高频操作
3. **全功能门户首页** — 8-12个功能卡片网格，每张卡片直达核心功能区域
4. **每个功能卡片必须包含**：大图标 + 功能名称 + 一句话描述 + hover视觉反馈(上移+边框发光)
5. **页面必须丰富** — "简单的列表"不够，每个页面要有数据总览+图表+操作入口

## 第一步：全功能-页面-操作映射

在开始任何UI设计前，必须完整列出项目的**所有功能**和**每个功能的用户操作**。

```markdown
| 功能 | 操作 | 目标页面 | 点击次数从首页 |
|------|------|---------|--------------|
| 智影工场 | CRUD管理 | /zhiying | 1 |
| AIGC生成 | 图片/视频/3D生成 | /studio.html | 1 |
| 工作流编排 | 节点拖拽编辑 | /workflow.html | 1 |
| ML模型管理 | 注册/预标注/主动学习 | 系统内部 | 2 |
| ... | ... | ... | ... |
```

**所有功能必须在导3次点击内可达**。任何需要4+次点击的功能说明导航层设计有问题。

## 第二步：三站式导航架构设计

### 标准布局

```
首页(/) — 功能门户(8-12卡片网格)
├── 主工作区 (SAP) — 左侧导航树 + 右侧工作面板
│   ├── 导航树 = 按角色/任务组织的所有功能
│   └── 每个节点 = 一个独立的功能页面
├── 专题页面 — 独立的全功能界面
│   ├── AIGC生成工作室
│   ├── 工作流编辑器(DAG节点图)
│   └── 其他单页应用
└── API/系统 — 直接访问
    ├── /health /metrics /docs
    └── 纯API端点
```

### 左侧导航树设计标准

| 层级 | 示例 | 说明 |
|------|------|------|
| 一级标题 | 📊 数据生产 | 模块分类(5-7个) |
| 二级功能 | ├── 智影工场 | 具体功能页面(2-5个/模块) |
| 三级操作 | │   ├── 数据看板 | 具体页面(1-3个/功能) |
| ... | │   ├── ML模型管理 | 最多3级，超过就要重组 |

### Vue3 SPA 菜单扩展模式

当在Vue3 SPA中添加新页面时，遵循以下步骤：

```javascript
// 1. 在 menuItems 数组中插入新项（按逻辑分组，不是按时间追加）
menuItems = [
  { id: 'dashboard', label: '仪表盘', icon: '📊' },
  // ... 现有菜单 ...
  { id: 'ml_models', label: 'ML模型', icon: '🧠' },  // 插入
  { id: 'quality', label: '质量中心', icon: '📊' },
  // ... 按逻辑分组 ...
]

// 2. 添加对应的Vue page div
// <div class="page" :class="{ active: currentPage === 'ml_models' }">
//   页面内容...
// </div>

// 3. 在JS setup()中添加data和methods
const mlModelList = ref([]);
const loadMLModels = async () => { ... };

// 4. 在onMounted中调用
onMounted(() => {
  loadMLModels();
  loadVersionLog();
});

// 5. 在return中导出
return { mlModelList, loadMLModels, ... };
```

## 第三步：首页仪表盘布局

### 8卡片设计

```html
<div class="cards-grid" style="grid-template-columns: repeat(4, 1fr);">
  <a href="/target" class="card">
    <span class="card-icon">📊</span>
    <h3>功能名称</h3>
    <p>功能描述</p>
  </a>
  <!-- 共8个同款卡片 -->
</div>
```

### CSS规格

```css
.card {
  background: #1e293b;  /* 表面色 */
  border: 1px solid #334155;
  border-radius: 1rem;
  padding: 1.5rem 1.25rem;
  transition: all 0.25s ease;
  cursor: pointer;
}
.card:hover {
  transform: translateY(-5px);
  border-color: #3b82f6;
  box-shadow: 0 12px 30px rgba(0,0,0,0.3), 0 0 0 1px rgba(59,130,246,0.3);
}
.card-icon { font-size: 2.25rem; }
.card h3 { font-size: 1.05rem; font-weight: 600; }
.card p { font-size: 0.8rem; color: #94a3b8; }
```

### 首页底部状态栏

```html
<footer>
  <div>版本号</div>
  <div>API状态: <span class="status-dot green"></span>已连接</div>
</footer>
```

```javascript
// 自动检测API状态
fetch('/health')
  .then(r => r.json())
  .then(d => { /* 更新dot为绿色 */ })
  .catch(() => { /* 更新dot为红色 */ })
```

### 首页头部导航

```
[Logo + 标题] [导航链接1] [导航链接2] [导航链接3] [导航链接4]
```

4-5个快速导航链接，直接指向核心功能。

## 第四步：完整页面组织示例（参照实战案例）

### 首页门户（8-12卡片）

| 卡片 | 图标 | 目标路径 | 描述 |
|------|------|---------|------|
| 智影数据工场 | 📊 | /zhiying | 数据生产/标注/质量全流程 |
| AIGC工作室 | 🎨 | /studio.html | 图像/视频/3D智能生成 |
| 工作流编辑器 | 🔧 | /workflow.html | 拖拽式自动化工作流 |
| ML模型管理 | 🧠 | /zhiying#ml | 模型训练/部署/版本管理 |
| 资产管理 | 📁 | /api/assets | 数据集/素材统一管理 |
| 权限管理 | 🔐 | /zhiying#rbac | 角色/权限/团队协作 |
| 质量中心 | 📈 | /zhiying#quality | 数据质量监控/审核 |
| 系统设置 | ⚙️ | /zhiying#settings | 平台配置/日志管理 |

### 智影工场侧边栏（13+菜单项按逻辑分组）

```
数据管理组: 仪表盘📊 资产管理🖼️ 需求管理📋 任务管理📌
数据开发组: 数据集💾 数据集版本🗂️ ML模型🧠 模型评测🧪
质量监控组: 统计看板📈 数据治理🔐 质量中心📊
协作管理组: 多模态标注🎬 权限管理🔐 用户管理👥
```

### AIGC工作室侧边栏

```
🖼️ 图片生成
✏️ 图片编辑
🎬 视频生成
🎲 3D生成
📁 历史生成
🔧 ComfyUI
```

### 工作流编辑器

独立页面（不集成到SPA），提供：
- 节点库面板（左侧，按分类折叠）
- 步骤列表（可视化卡片 + 参数编辑）
- 3个预置模板按钮
- JSON预览
- 保存/加载(localStorage)
- 执行按钮

## 第五步：用户旅程设计

从登录到完成任务的完整路径，每个步骤不超过3次点击：

```
首页(/) 
  → 点击卡片进入功能页面 (第1次点击)
    → 在功能页面中选择操作 (第2次点击)
      → 执行操作并查看结果 (第3次点击)
```

### 功能可达性检查清单

| 检查项 | 标准 |
|--------|------|
| 每个功能是否都有首页卡片或导航入口？ | ✅ 是 |
| 首页到功能的点击次数？ | ≤2 |
| 功能内操作的点击次数？ | ≤3 |
| 不常用的设置入口？ | 在导航树/系统设置内 |
| 是否有功能没有任何路径到达？ | ❌ 必须修复 |

## 第六步：颜色体系

### 暗色主题（推荐）

```css
:root {
  --bg-body: #0f172a;
  --bg-card: #1e293b;
  --bg-hover: #1e3a5f;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --border: #334155;
  --border-hover: #3b82f6;
  --accent: #3b82f6;
  --accent2: #8b5cf6;
  --success: #10b981;
  --error: #ef4444;
}
```

## 第七步：三AI互审UI验收

在UI实现完成后，启动三AI互审：

| AI角色 | 任务 | 检查点 |
|--------|------|--------|
| 监督AI-A (行业对标) | 检查导航是否对标Scale AI/Labelbox | 是否所有功能3次点击可达？ |
| 监督AI-B (功能完整性) | 检查所有功能是否有页面可达 | 对照全功能映射表逐个功能检查 |
| 监督AI-C (代码质量) | 检查前端代码是否真实对接API | 按钮onclick是否调用真实fetch？ |

### 验收输出格式

```markdown
| 功能 | 首页路径 | 点击次数 | 状态 |
|------|---------|---------|------|
| 智影工场 | 首页→📊卡片 | 1 | ✅ |
| ML模型 | 首页→zhiying→🧠侧栏 | 2 | ✅ |
```

## 响应式策略

### 断点

| 断点 | 宽度 | 导航树策略 |
|------|------|-----------|
| 宽屏 | >1200px | 完整展开 |
| 标准 | 900-1200px | 展开 |
| 平板 | 500-900px | 可折叠汉堡菜单 |
| 手机 | <500px | 底部导航栏替代侧栏 |

### CSS实现

```css
@media (max-width: 900px) {
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
  header { flex-direction: column; }
}
@media (max-width: 500px) {
  .cards-grid { grid-template-columns: 1fr; }
}
```

## 设计陷阱

1. **卡片点击后跳到zhiying锚点但zhiying还没有对应页面** → 必须先确保目标页面存在或直接跳转到首页
2. **Vue SPA的v-for渲染侧边栏但snapshot只能看到几个元素** → 用`grep -c "id: '"`检查menuItems数组中的条目数
3. **导航树深度超过3层** → 用户找不到功能，必须重组
4. **把所有需求一次性塞给一个子Agent重写大HTML文件** → 会超时，必须分段patch
5. **"功能丰富"不等于"导航清晰"** — 先做功能映射再设计导航，不要反过来
6. **子Agent多次注入HTML_TEMPLATE会导致JS损坏** — 每个子Agent用sed/patch修改Python字符串中的内联HTML，会逐步破坏括号匹配、注释语法、作用域链。修复成本远大于新建。关键信号: 用户说"点任何按键都没反应"或"只有画布没有侧边栏"时，99%是JS语法错误(括号不匹配/对象字面量内//注释/函数定义作用域问题)，先检查typeof switchTab和compile(js)。
7. **用户说"不够丰富"超过2次时必须重启设计而不是迭代修补** — 用户第一次说"不够"时修改当前方案；说第二次时停止改代码，退后到架构层面重新设计方案；说第三次时表明方向错了，重写设计文档并找用户确认后再编码。
8. **"常用功能直接呈现"优于"3次点击可达"** — 用户硬性要求：首页必须有4个指标卡(今日生产量/待审核/在线人数/系统状态)+8个快捷操作按钮(上传数据/开始标注/执行工作流/查看看板/创建任务/邀请成员/交付数据/统计分析)+最近任务列表+快速标注工具。不藏在任何菜单后面。违反此原则会被用户直接驳回。

## 子Agent前端破坏修复指南

### 问题特征
- 页面加载但JS不执行，typeof switchTab返回undefined
- 子Agent注入后引入的常见JS语法错误：对象字面量内//注释(必须用/* */)、花括号不匹配、函数定义被包裹在非全局作用域内
- 多个子Agent先后注入导致代码碎片化

### 诊断步骤
1. curl -s http://host:port/ | python3 -c "import sys; js=sys.stdin.read(); compile(js, 'test', 'exec')" — 检查JS语法
2. typeof switchTab + document.querySelector('script').textContent.includes('switchTab') — 检查函数定义是否存在但不可访问
3. new Function(document.querySelector('script').textContent.slice(-500)) — 定位语法错误

### 修复策略（按优先级）
1. **新建独立前端文件**(最佳) — 不再用内联HTML_TEMPLATE，改用frontend/index.html + CSS/JS独立文件，FastAPI通过StaticFiles挂载。子Agent的sed/patch不会触及独立文件。
2. **备用路由保留** — GET /canvas保留旧内联HTML_TEMPLATE作为降级入口，GET /返回新独立前端
3. 前端不再依赖{"success":true,...}格式的猜测，统一使用api_success()/api_error()响应

### 独立前端文件结构
frontend/
  index.html           # 主入口(左侧导航+顶栏+状态栏)
  css/main.css         # 深色工业主题(变量+布局+组件)
  js/
    lib/api.js         # API调用层(fetch封装)
    pages/
      dashboard.js     # 首页(4指标+8快捷+任务列表+快速标注)
      datasets.js      # 数据集管理(表格+搜索+批量+导入导出)
      annotate.js      # 标注工具(AI预标注+BBox叠加)
      business.js      # 任务/团队/交付/审核/统计/设置
    app.js             # 路由+导航+状态栏刷新

### FastAPI配置
from fastapi.staticfiles import StaticFiles
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/css", StaticFiles(directory=os.path.join(_frontend_dir, "css")))
app.mount("/js", StaticFiles(directory=os.path.join(_frontend_dir, "js")))

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(_frontend_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f: return f.read()
    return HTML_TEMPLATE  # fallback
6. **用户要求的5步门控流程不可省略** — 全局观念→深度分析→规划→执行→三AI互审

### 强制前置流程（用户硬性要求）

当用户说"全局观念建立，深度思考分析，建立完整规划方案，然后按照软件工程的完整流程严格执行。记得要三AI互审互查"时，这是在强制执行一个5步门控流程：

1. **全局观念建立** — 扫描所有功能模块，输出能力矩阵
2. **深度思考分析** — 对比行业竞品（Scale AI、Labelbox、ComfyUI），找出差距
3. **完整规划方案** — 基于差距制定分层执行计划
4. **按软件工程流程执行** — 7步SDLC
5. **三AI互审互查** — 3个独立的AI做交叉验证

任何试图省略前3步直接跳到代码的行为都会被用户打断。这是硬约束。

## 实现方案参考

前端具体实现（独立文件结构、FastAPI StaticFiles配置、SPA路由）请参考 `zhiying-dev-engine` skill 的 `references/standalone-frontend-implementation.md`。

本技能基于 Nanobot Factory 项目实战提炼。参考案例：
- `references/nanobot-factory-ui-architecture-2026-06-12.md` — 首页、智影(13菜单项)、studio、workflow的完整导航设计与三AI互审验收
