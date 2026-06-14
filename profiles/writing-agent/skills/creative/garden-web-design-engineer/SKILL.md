---
name: garden-web-design-engineer
description: ConardLi garden-skills 网页设计工程师 — 让AI Agent像专业设计师一样做网页。从判断产品类型和受众开始，确定视觉方向、信息层级、排版节奏、组件密度和交互细节。25+设计主题模板，覆盖SaaS/开发者工具/品牌/数据/创意等全场景。
version: 1.1.0
author: Hermes Agent (from ConardLi garden-skills)
domain: creative
tags:
  - web-design
  - design-templates
  - ui-design
  - landing-page
  - design-system
  - saas-design
triggers:
  - "网页设计"
  - "设计模板"
  - "官网设计"
  - "Landing Page"
  - "落地页"
  - "设计系统"
  - "UI设计"
  - "网页生成"
  - "主题选择"
  - "设计风格"
  - "B2B官网"
  - "SaaS官网"
  - "企业官网"
  - "产品展示页"
  - "Dashboard"
  - "活动页"
---

# Garden Web Design Engineer

## 核心理念

来自 ConardLi garden-skills 的 web-design-engineer 全面集成。

**问题**：AI生成网页最常见的问题是"一眼就能看出是AI做的"——大渐变、玻璃卡片、发光边框、过度圆角、信息排布松散。

**解法**：把Agent从"套默认审美"拉回到真正的网页设计流程：
1. 先判断产品类型和受众
2. 再确定视觉方向和设计风格
3. 建立信息层级和排版节奏
4. 控制组件密度和交互细节

## 25+设计主题模板

| 主题 | 风格 | 适合 |
|------|------|------|
| **linear** | 极简克制 | B2B SaaS、开发者工具、项目管理 |
| **raycast** | 暗色快捷 | 效率工具、命令面板、极客产品 |
| **aesop** | 留白+文字比例 | 美妆、护肤、精品零售、生活方式品牌 |
| **tufte-dataink** | 数据驱动 | 研究报告、论文图表、信息可视化 |
| **field-io** | 艺术实验 | 艺术科技、互动装置、创意工作室 |
| **active-theory** | 电影感 | 品牌Campaign、游戏/娱乐、沉浸首屏 |
| **bloomberg-businessweek** | 杂志感 | 封面专题、观点专题、强视觉编辑 |
| **balenciaga-post-2017** | 生硬冷感 | 时装、潮流、反奢侈品 |
| **mailchimp-freddie** | 温暖创意 | 社区、创业工具、小团队B2C SaaS |
| **headspace-meditation** | 圆润轻松 | 健康、心理、教育、儿童产品 |
| **y2k-retrofuturism** | Y2K复古 | 活动页、音乐、潮流、年轻化Campaign |
| 另含15+主题覆盖各类商业/技术/创意场景 | | |

## 工作流程

### 阶段1: 项目诊断

输入: 项目背景/产品描述/目标用户
输出: 设计方向决策

```yaml
# 诊断要点
product_type: SaaS | 电商 | 品牌 | 内容 | 工具 | 社区
target_audience: CTO | 设计师 | 消费者 | 投资人 | 开发者
visual_direction: 极简 | 丰富 | 冷酷 | 温暖 | 数据驱动 | 创意
complexity: 单页 | 多页 | Dashboard
```

### 阶段2: 风格匹配

根据诊断结果自动推荐最适合的主题，或按需求指定：

```python
# 示例: 给CTO展示的开发者工具
theme_match = {
    "product": "开发者API工具",
    "audience": "CTO/技术负责人",
    "suggested": ["linear", "raycast"],
    "avoid": ["aesop", "balenciaga", "y2k"]
}
```

### 阶段3: 信息架构

确定页面结构、信息层级和导航方式。

### 阶段4: 页面生成

生成完整的HTML/CSS/JS文件。

### 阶段5: 设计评审

逐页检查：信息层级、视觉一致性、交互细节、响应式。

## 与Hermes现有系统融合

### 1. 与情报采集联动

Crawl4AI采集的竞品网站 → 分析其设计风格 → 作为风格参考输入

### 2. 与认知蒸馏联动

蒸馏出的受众模型 → 决定设计风格和排版节奏：
- 给CTO → linear极简风格
- 给投资人 → bloomberg杂志风格
- 给消费者 → mailchimp温暖风格

### 3. 与Goal Hive联动

```
Master拆解网页设计任务:
  Worker 1: 竞品调研（采集+Craw4AI）
  Worker 2: 受众分析和风格匹配（认知蒸馏）
  Worker 3: 信息架构和页面结构
  Worker 4: 代码生成
  Worker 5: 设计评审
```

### 4. 与视频制作联动

生成的网页 → 可以直接作为视频制作的素材（garden-web-video-production）

## 验证清单

- [ ] 项目诊断正确判断产品类型和受众
- [ ] 25+主题模板按需可匹配
- [ ] 生成的HTML/网页结构清晰
- [ ] 信息层级合理（标题/正文/辅助信息）
- [ ] 响应式布局可用
- [ ] 视觉一致性（颜色/字体/间距/图标风格）
- [ ] 无典型AI设计痕迹（过度圆角/玻璃卡片/发光边框等）
- [ ] 与认知蒸馏联动（受众模型→风格决策）
- [ ] 可局部迭代修改（某页/某组件/某风格）

## 陷阱

- **主题匹配不对**：给CTO的产品别用y2k或创意工作室风格
- **页面过密**：B2B产品宁可留白过多也不能信息过密
- **装饰过度**：每个装饰元素需要有功能目的，不能为了好看而好看
- **一致性问题**：同一页面上不同组件的圆角/阴影/间距必须统一
- **响应式不考虑**：移动端是必备检查项
