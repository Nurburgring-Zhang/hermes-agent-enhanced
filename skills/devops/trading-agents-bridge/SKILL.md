---
name: trading-agents-bridge
description: TradingAgents多智能体金融交易框架桥接。基于84K★开源项目TauricResearch/TradingAgents。多智能体并行分析(基本面/情绪/新闻/技术指标)+风险经理审核+执行Agent下单的全自主金融交易系统。
---

# TradingAgents Bridge — 多智能体金融交易

## 作用
TradingAgents是一个**多智能体LLM金融交易框架**，模拟一个完整的华尔街交易团队：
- 4个分析师并行工作（基本面/市场情绪/新闻情报/技术指标）
- 1个风险经理审核
- 1个执行Agent下单

## 核心架构
```
[分析师集群]
  ├── 基本面分析师 → 公司/行业深度分析
  ├── 市场情绪分析师 → 舆情/社媒情绪
  ├── 新闻情报分析师 → 实时新闻事件
  └── 技术指标分析师 → 图表/量价/趋势
        ↓
[风险经理] → 审核分析报告，评估风险等级
        ↓
[执行Agent] → 生成交易指令/回测/模拟
```

## 集成方式
本Hermes的集成：
1. 回测与策略研究（不涉及实盘交易）
2. 接入economics-finance-experts skill的领域知识
3. 利用多Agent引擎(production_chain_v2.py)相似理念

## 技术栈
- Python + LLM驱动分析
- 支持回测框架
- 可视化数据图表
- 金融数据API集成

## 获取
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
```
