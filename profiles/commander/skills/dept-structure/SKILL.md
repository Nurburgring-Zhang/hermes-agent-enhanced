# SKILL.md - 部门结构 (Department Structure)

## 概述

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

本文档描述 OpenClaw 公司的 12 部门组织结构，已迁移到 Hermes 系统。

## 部门流程链
```
信息采集(Collector)
    ↓
[01] 市场营销部 (Marketing)
    ↓
[02] 设计部 (Design)
    ↓
[03] 产品部 (Product)
    ↓
[04] 研发部 (R&D)
    ↓
[05] 项目管理部 (PMO)
    ↓
[06] 项目开发部 (Development)
    ↓
[07] 项目支持部 (Project Support)
    ↓
[08] 工程部 (Engineering)
    ↓
[09] 测试与交付部 (QA & Delivery)
    ↓
[10] 宣传媒体部 (Media)
    ↓
[11] 支持部 (Support)
    ↓
[12] 销售部 (Sales)
    ↓
客户交付
```

---

## 部门详情

### 01 市场营销部 (Marketing) - 5人
**代号**: 01_marketing  
**使命**: 从信息采集流中挖掘需求，提出产品要求  
**角色**: 市场总监, 品牌经理, 数字营销专家, 内容营销专家, 渠道经理

**跨部门协作**:
- 上游: 信息采集系统
- 下游: 设计部

---

### 02 设计部 (Design) - 8人
**代号**: 02_design  
**使命**: 根据产品需求设计产品功能与用户体验  
**角色**: 设计总监, UX研究员, 交互设计师, 视觉设计师, UI组件设计师, 动效设计师, 品牌设计师, 设计规范工程师

**跨部门协作**:
- 上游: 市场营销部
- 下游: 产品部

---

### 03 产品部 (Product) - 4人
**代号**: 03_product  
**使命**: 根据设计部的产品功能制定具体的产品形态  
**角色**: 产品总监, 产品经理, 产品运营, 产品分析师

**跨部门协作**:
- 上游: 设计部
- 下游: 研发部

---

### 04 研发部 (R&D) - 6人
**代号**: 04_rd  
**使命**: 根据产品形态进行产品研发  
**角色**: 研发总监, AI研究员, 后端架构师, 前端架构师, 数据工程师, 安全工程师

**核心工具**: web_search, web_fetch, read, write, edit, exec, sessions_spawn, cron, message, memory_search, memory_get

**跨部门协作**:
- 上游: 产品部
- 下游: 项目管理部 (PMO)
- 横向: 工程部(提供技术标准和框架)

---

### 05 项目管理部 (PMO) - 5人
**代号**: 05_pmo  
**使命**: 制定项目开发计划并管理项目全流程  
**角色**: PMO总监, 项目经理A, 项目经理B, 项目协调员, 风险管理师

**跨部门协作**:
- 上游: 研发部
- 下游: 项目开发部

---

### 06 项目开发部 (Development) - 30人
**代号**: 06_dev  
**使命**: 执行项目开发计划，完成产品代码实现  
**角色**: 开发组长, 高级开发工程师A~G, 全栈开发工程师A~E, 前端开发工程师A~D, 后端开发工程师A~D, AI开发工程师A~B, 移动端开发工程师A~B, DevOps工程师A~B, 测试开发工程师A~B, 安全开发工程师A

**跨部门协作**:
- 上游: 项目管理部
- 下游: 项目支持部

---

### 07 项目支持部 (Project Support) - 20人
**代号**: 07_support_proj  
**使命**: 对项目研发提供全链路技术支持  
**角色**: 支持组长, 技术支持工程师A~E, 数据库管理员A~B, 运维工程师A~C, SRE工程师A~C, 配置管理员A~B, 文档工程师A, 日志分析师A, 性能调优师A, 迁移工程师A

**跨部门协作**:
- 上游: 项目开发部
- 下游: 工程部

---

### 08 工程部 (Engineering) - 23人
**代号**: 08_engineering  
**使命**: 为所有部门提供技术与资源支持  
**角色**: 工程总监, 系统架构师A~C, 基础设施工程师A~B, 网络工程师A~B, 存储工程师A, SRE专家A~C, 云平台工程师A~C, 安全运维工程师A, Monitoring工程师A, CICD工程师A, 性能工程师A, 容量规划师A, 容器工程师A, 网格工程师A, 混沌工程师A

**跨部门协作**:
- 上游: 项目支持部
- 下游: 测试与交付部

---

### 09 测试与交付部 (QA & Delivery) - 8人
**代号**: 09_qa  
**使命**: 项目测试与交付验收  
**角色**: QA总监, 测试架构师, 自动化测试工程师, 性能测试工程师, 安全测试工程师, 集成测试工程师, UAT工程师, 交付经理

**跨部门协作**:
- 上游: 工程部
- 下游: 宣传媒体部

---

### 10 宣传媒体部 (Media) - 7人
**代号**: 10_media  
**使命**: 根据项目制定媒体制作方案并生产媒体内容  
**角色**: 媒体总监, 视频制作师, 图文编辑, 社交媒体运营, SEO专家, 品牌内容策划, 媒体数据分析师

**跨部门协作**:
- 上游: 测试与交付部
- 下游: 支持部

---

### 11 支持部 (Support) - 6人
**代号**: 11_support  
**使命**: 对所有部门提供通用支持  
**角色**: 支持总监, 行政主管, HR专员, 财务专员, 法务专员, 采购专员

**跨部门协作**:
- 上游: 宣传媒体部
- 下游: 销售部

---

### 12 销售部 (Sales) - 8人
**代号**: 12_sales  
**使命**: 寻找需求方并将项目售卖出去  
**角色**: 销售总监, 大客户经理, 渠道销售A~B, 售前工程师, 解决方案架构师, 客户成功经理, 销售运营

**跨部门协作**:
- 上游: 支持部
- 下游: 客户交付

---

## 总人数统计
| 部门 | 人数 |
|------|------|
| 市场营销部 | 5 |
| 设计部 | 8 |
| 产品部 | 4 |
| 研发部 | 6 |
| 项目管理部 | 5 |
| 项目开发部 | 30 |
| 项目支持部 | 20 |
| 工程部 | 23 |
| 测试与交付部 | 8 |
| 宣传媒体部 | 7 |
| 支持部 | 6 |
| 销售部 | 8 |
| **合计** | **130** |

---

## 通用工具配置模板

根据角色类型，工具配置如下：

### Director/Manager 模板
```json
{
  "tools": {
    "allow": ["web_search","web_fetch","read","write","edit","exec","sessions_spawn","cron","message","memory_search","memory_get"]
  }
}
```

### Researcher/Analyst 模板
```json
{
  "tools": {
    "allow": ["web_search","web_fetch","read","write","exec","memory_search","memory_get"]
  }
}
```

### Developer/Engineer 模板
```json
{
  "tools": {
    "allow": ["web_search","web_fetch","read","write","edit","exec","sessions_spawn","memory_search","memory_get"]
  }
}
```

### Designer 模板
```json
{
  "tools": {
    "allow": ["web_search","web_fetch","read","write","exec","image_generate","image","memory_search","memory_get"]
  }
}
```

### QA 模板
```json
{
  "tools": {
    "allow": ["web_search","web_fetch","read","write","edit","exec","sessions_spawn","memory_search","memory_get"]
  }
}
```

### Media 模板
```json
{
  "tools": {
    "allow": ["web_search","web_fetch","read","write","exec","message","image_generate","video_generate","memory_search","memory_get"]
  }
}
```

---

## 来源
- 源文件: `/mnt/d/OpenClaw/dept_definitions.json`
- 源文件: `/mnt/d/OpenClaw/agents_company/ORGANIZATION_V2.md`
- 迁移日期: 2026-04-15

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
