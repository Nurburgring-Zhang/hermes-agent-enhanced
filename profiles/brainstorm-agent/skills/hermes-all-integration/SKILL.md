---
name: hermes-all-integration
description: Hermes Agent全能力整合方案 - 38个能力点从31个附件深度分析中提炼，涵盖情报采集、记忆系统、专业Skills、多Agent协作、自进化能力、配置优化、生态工具、工程规范。版本: 1.0. 创建日期: 2026-04-22.
triggers:
  - "升级Hermes"
  - "整合能力"
  - "38个能力点"
  - "31个附件"
  - "hermes-all-integration"
  - "全面能力提升"
  - "能力增强"
---

# Hermes 全能力整合方案

> 基于31个附件深度分析，整合8大能力组共38个能力点。

---

## 执行摘要

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


本次整合来源于格林主人提供的31个技术附件（2026-04-22），经过逐个附件深度分析后提炼而成。涵盖：

| 能力组 | 能力点 | 优先级 |
|--------|--------|--------|
| 情报采集 | 6项 | P0-P3 |
| 记忆系统 | 4项 | P0-P2 |
| 专业Skills | 6项 | P1-P4 |
| 多Agent协作 | 4项 | P1-P2 |
| 自进化能力 | 4项 | P1-P2 |
| 配置优化 | 5项 | P0 |
| 生态工具 | 5项 | P1-P3 |
| 工程规范 | 4项 | P1-P2 |

---

## 第一阶段：P0优先级（立即可执行）

### 1. NVIDIA NIM免费M2.7配置

**来源**: paste_18

**价值**: 零成本使用MiniMax M2.7（相当于省29元/月）

**配置步骤**:
1. 注册 https://build.nvidia.com（使用邮箱，验证手机号）
2. 生成API Key（过期时间默认12个月）
3. `hermes setup` → 选择 `NVIDIA NIM`
4. 输入API Key和Base URL: `https://integrate.api.nvidia.com/v1`
5. 选择模型: `minimaxai/minimax-m2.7`

**限制**: 每分钟40次请求

**验证命令**:
```
hermes model
# 确认 minimaxai/minimax-m2.7 已选中
```

### 2. Jina Reader内容获取

**来源**: paste_21, paste_22

**价值**: 绕过反爬虫，直出Markdown，零配置零代码

**使用方式**: 在任意URL前加前缀
```
https://r.jina.ai/https://目标网址
```

**三级备选**: r.jina.ai → markdown.new → defuddle.md

**Hermes集成**: 
- 创建Skill自动在URL前加前缀
- 或通过 `browser_navigate` + JS提取内容

### 3. nudge_interval记忆整理配置

**来源**: paste_23, paste_30

**价值**: 控制记忆自动整理频率，避免无效信息堆积

**配置方法**: 在 `~/.hermes/config.yaml` 中添加：
```yaml
memory:
  nudge_interval: 5  # 每5轮对话整理一次记忆
```

**验证**: 观察MEMORY.md是否有规律更新

### 4. SOUL.md/AGENTS.md分层固化

**来源**: paste_30

**文件分工原则**:
- **SOUL.md**: 固定规则、不可随意改写的内容（人格、核心行为准则）
- **AGENTS.md**: 项目技术栈、流程边界、执行规范（项目专属协作准则）
- **MEMORY.md**: 环境事实、项目经验、可更新方法
- **USER.md**: 个人偏好、沟通习惯、常用选择

**实施**: 检查现有SOUL.md是否混入了项目专用内容，如有则迁移到AGENTS.md

---

## 第二阶段：P1优先级（1-3天内完成）

### 5. SuperMemory MCP外部记忆系统

**来源**: paste_19

**核心架构**:
- **原子化记忆提取**: 将对话分解为最小颗粒原子事实
- **关系版本控制**: updates/extends/derives三种语义关系
- **双层时间戳**: documentDate（对话时间）+ eventDate（事件实际发生时间）
- **混合搜索**: 向量搜索(原子记忆) + 原始块 + 关系图谱

**安装**:
```bash
npx -y install-mcp@latest https://mcp.supermemory.ai/mcp --client claude --oauth=yes
```

**Benchmarks**: LongMemEval 81.6%总体 | 多会话推理71.43% | 时间推理76.69%

**Hermes集成**: 配置MCP server连接，或使用Python SDK
```python
from supermemory import SuperMemory
memory = SuperMemory(api_key="...", user_id="...")
```

### 6. Google Agent Skills（20个工程技能）

**来源**: paste_29

**全生命周期6阶段**: Define→Plan→Build→Verify→Review→Ship

**核心命令**:
- `/spec` - 先写需求再写代码
- `/plan` - 小的原子化任务
- `/build` - 增量式构建
- `/test` - 测试就是证明
- `/review` - 提高代码健康度
- `/code-simplify` - 清晰胜过聪明
- `/ship` - 越快越安全

**重点技能**:
- TDD红绿重构 + 测试金字塔（80/15/5）
- OWASP Top10安全防护
- Beyonce规则（测试必须能跑）
- Hyrum定律（API一旦发布必须维护）
- Chesterton栅栏（简化时保留精确行为）

**安装**:
```bash
# Claude Code
/plugin marketplace add addyosmani/agent-skills
```

### 7. Discord多Agent协作协议（已验证）

**来源**: paste_20

**三人组模式**: Admin/Ink/Search（调度员+文案+调研）

**核心问题与解决方案**:

| 问题 | 解决方案 |
|------|----------|
| 没@就结束 | 在SOUL.md中绑定`<@用户ID>` |
| 停不下来（死循环） | 3层防御：DISCORD_ALLOW_BOTS=mentions + replied_user:false + 【任务结束】终止词 |
| 同时@两人（顺序混乱） | 时序规范：逐一唤醒，接力逻辑 |

**防循环3层防御详解**:
1. **配置层**: 所有profile的.env设置 `DISCORD_ALLOW_BOTS=mentions`
2. **Discord层**: config.yaml中设置 `replied_user: false`
3. **LLM认知层**: SOUL.md中写入终止协议

**Clone策略**: `--clone` 共享API key但上下文干净

### 8. Camofox反爬浏览器

**来源**: paste_22, paste_23

**价值**: 突破Cloudflare、验证码、Canvas指纹篡改

**配置**: 
```
# 告诉Hermes：帮我配置Camofox及CAMOFOX_URL
```

**用途**: 微信公众号、微信读书、需要登录的页面

### 9. Edge TTS语音合成

**来源**: paste_22

**状态**: Hermes内置，无需额外配置

**使用**: 300+语音，中文音质优秀
```bash
hermes tts "要说的话"
```

### 10. Whisper语音识别

**来源**: paste_22

**安装**:
```bash
# 本地运行，99种语言，CPU也能跑
pip install openai-whisper
```

**用途**: 语音输入、播客转录

---

## 第三阶段：P2优先级（1-2周内完成）

### 11. wechat-cli微信数据采集

**来源**: paste_3

**价值**: Windows本地微信数据库直读（WSL2通过/mnt/c/访问）

**安装**:
```bash
git clone https://github.com/freestyelfly/wechat-cli.git
cd wechat-cli && ./install.sh
```

**微信数据库路径（Windows）**: 
```
C:\用户\<用户名>\AppData\Roaming\Tencent\WeChat\
```

**WSL2访问路径**: `/mnt/c/用户/<用户名>/AppData/Roaming/Tencent/WeChat/`

**命令**:
- `wechat sessions` - 获取会话列表
- `wechat history <session_id>` - 获取聊天历史
- `wechat search <keyword>` - 搜索消息
- `wechat export <session_id>` - 导出聊天记录
- `wechat stats` - 统计数据

**Hermes集成**: 
1. 验证wechat-cli在WSL2中正常工作
2. 创建Skill调用wechat-cli获取数据
3. 将微信数据通过JSON输出传递给Hermes处理

### 12. AntV可视化Skill

**来源**: paste_5

**安装**:
```bash
npx skills add antviz/chart-visualization-skills
```

**能力**:
- 26种图表类型
- 200+信息图模板
- L7地图可视化
- T8数据叙事
- S2透视表
- 图标库

**特点**: 自动选型，声明式语法（AI友好）

### 13. huashu-bookwriter写作质量控制

**来源**: paste_12

**核心**: 逆向花叔写作方法论

**5层架构**:
1. 渐进式信任建立（时间线锚点）
2. 结构化知识传递
3. 风格DNA（单句≤25字/禁用词表）
4. TDD式质量铁律（12项QC）
5. Agent Protocol（研究确认事实）

**质量门禁**: 
- 12项章节QC + 10项全书QC
- Rationalization Table（防借口机制）

### 14. HyperFrames HTML5视频

**来源**: paste_14

**价值**: 60秒生成视频（vs Remotion 162秒+4分钟构建），体积4MB（vs 14MB）

**安装**:
```bash
npx skills add heygen-com/hyperframes
```

**原理**: HTML data属性控制时间轴，基于Web代码训练（LLM友好）

### 15. GenericAgent自进化能力参考

**来源**: paste_26

**核心理念**: 遇到新任务→自主摸索→固化skill→写入记忆→下次调用

**架构**: 3K核心代码 + 100行Agent Loop + 9个原子工具

**上下文**: 不到30K（vs 其他Agent 200K-1M），强调有效记忆而非塞满上下文

**技能树**: 从种子代码长成属于你的私有能力层

**Hermes借鉴**: 
- 强化现有Skill自动沉淀机制（每15次循环后Review）
- 优先写入有效记忆，减少噪音

### 16. Skill编排架构

**来源**: paste_16

**核心理念**: 单个Skill解决点的问题，编排解决线的问题

**两层能力**:
1. **单技能设计**: 边界清晰 + 接口标准 + 封装实现
2. **技能编排**: 时序 + 数据流转 + 容错 + 多路径分支

**Skill Architect职责**:
1. 理解业务全貌
2. 识别Skill边界
3. 设计编排逻辑
4. 处理异常跳转
5. 持续迭代优化

**vs Agentic Workflow**: Skill编排瓶颈在业务理解，Agentic Workflow瓶颈在操作工具

### 17. M-Flow记忆引擎架构参考

**来源**: paste_17

**架构**: Cone Graph（锥形图谱）
- Episode（情景）→ Facet（切面）→ FacetPoint（原子事实）
- Entity（实体）横穿锥体，串起所有层级

**核心洞察**: 搜索≠联想
- 搜索：给你最相似的片段
- 联想：给你最该被想起来的那个情景

**Benchmarks**: LoCoMo/LongMemEval/EvolvingEvents 全第一

**参考价值**: 设计下一代记忆系统时的重要架构参考

---

## 第四阶段：P3优先级（长期能力建设）

### 18. OpenMontage视频制作系统

**来源**: paste_11

**能力**: 11条生产线，49工具，400+Agent技能

**成本**: 60秒皮克斯动画$1.33，广告视频$0.69

**流水线类型**:
- 动画解说 / 动态图形 / 虚拟主播 / 电影风格 / 批量剪辑
- 混合制作 / 多语言本地化 / 播客转视频 / 屏幕录制 / 真人出境 / 项目简介

### 19. nuwa-skill人物专家蒸馏

**来源**: paste_10

**方法**: 从人物提取5层认知
1. 表达风格
2. 心智模型
3. 决策启发式
4. 反模式
5. 诚实边界

**6路并行采集**: 著作/播客/社交/批评/决策/时间线

**收录条件**: 3条件同时满足（跨领域/预测力/排他性）

**预建人物**: 芒格/巴菲特/马斯克/乔布斯/Karpathy/Ilya等13位

**安装**:
```bash
npx skills add nuwa-skill
```

### 20. JS-Eyes 2.0自学习浏览器

**来源**: paste_24

**理念**: 从"给龙虾具体能力"到"给龙虾获得能力的途径"

**架构**: 1个主插件 + 1套协议 = 无限技能（vs v1的8个独立技能）

**默认技能**: X.com / Bilibili / YouTube / 知乎 / 小红书 / 微信公众号 / Reddit / 即刻

**安装**: https://js-eyes.com 或 GitHub

### 21. Mano-P GUI Agent

**来源**: paste_7, paste_8

**性能**: OSWorld 58.2%（全球第一），72B参数

**特点**: 纯视觉GUI交互（不靠CDP/HTML解析），本地运行

**安装**:
```bash
brew tap HanningWang/tap && brew install mano-cua
# 或
clawhub install mano-cua
```

### 22. Anthropic Auto-Research参考

**来源**: paste_6

**发现**: 9x Claude Opus 4.6副本，1.8万美金，PGR 0.97 vs 人类0.23

**核心概念**:
- 弱监督强
- 外星科学（Alien Science）
- 奖励操纵（Reward Hacking）
- PGR指标（Progress Ratio）

**参考价值**: 用于Hermes的自我优化循环设计

---

## 第五阶段：P4优先级（生态完善）

### 23. Playwright浏览器自动化

**来源**: paste_22

**状态**: Hermes内置，支持3大引擎

**特点**: 自动等待 + 网络拦截

### 24. Obsidian知识库

**来源**: paste_22, paste_27, paste_28

**能力**: 本地知识库，L L M Wiki模式，自动维护双向链接

**集成价值**: 
- B站视频处理（下载→转录→生成结构化笔记）
- 网页文章剪藏
- 知识自动关联和进化

### 25. OpenClaw迁移工具

**来源**: paste_22

**方式**:
```bash
hermes claw migrate  # 内置一键迁移
# 或
openclaw-to-hermes   # 社区增强版，处理复杂依赖图
```

---

## 工程规范（必须内化）

### A. 全生命周期标准（Google Agent Skills）

**Define** → **Plan** → **Build** → **Verify** → **Review** → **Ship**

每个阶段都有明确的输入、输出、检查点。

### B. TDD质量铁律

1. **红**: 写一个失败的测试
2. **绿**: 写最少量代码让测试通过
3. **重构**: 改善代码结构

**测试金字塔**: 80%单元测试 / 15%集成测试 / 5%端到端测试

### C. 安全底线

**OWASP Top10**: 注入 / 身份认证失效 / 敏感数据泄露 / XML外部实体 / 访问控制失效 / 安全配置错误 / XSS / 不完整验证 / 敏感信息明文传输 / 不足日志监控

### D. 代码简化原则（Chesterton栅栏）

"在保留精确行为的同时降低复杂度"。简化不是删功能，是让代码更易理解。

---

## 已知限制与风险

1. **wechat-cli**: Windows微信4.1.8及以下版本，macOS已停止支持
2. **NVIDIA NIM**: 每分钟40次请求限制
3. **SuperMemory MCP**: 需要OAuth认证
4. **Mano-P**: macOS为主，Windows支持待验证
5. **JS-Eyes**: 微信相关功能需要Windows微信客户端

---

## 实施路线图

| 周次 | 任务 | 产出 |
|------|------|------|
| 第0天 | 完成P0（4项） | M2.7+Jina+记忆配置+SOUL分层 |
| 第1周 | 完成P1（6项） | MCP+Agent Skills+Discord协作+Camofox+TTS+Whisper |
| 第2周 | 完成P2（6项） | wechat-cli+AntV+huashu+HyperFrames+GenericAgent+Skill编排 |
| 第3-4周 | 完成P3（4项） | OpenMontage+nuwa-skill+JS-Eyes+Mano-P |
| 持续 | 完成P4（2项） | Playwright+Obsidian+迁移工具 |

---

## 验证清单

完成每项后验证：

- [ ] M2.7回复"你使用的底层大模型是什么"正确
- [ ] Jina Reader能抓取微信公众号
- [ ] MEMORY.md有规律更新
- [ ] SOUL.md/AGENTS.md边界清晰
- [ ] SuperMemory能存取原子记忆
- [ ] Google Skills命令可调用
- [ ] Discord三人组能正常协作
- [ ] Camofox能突破Cloudflare
- [ ] TTS能说出中文
- [ ] Whisper能识别语音
- [ ] wechat-cli能读取Windows微信DB
- [ ] AntV能生成图表
- [ ] huashu能控制写作质量
- [ ] HyperFrames能生成视频
- [ ] Skill编排能串联多个Skill

---

_本Skill由Hermes基于31个附件深度分析自动生成。_
_版本: 1.0 | 创建: 2026-04-22 | 来源: 格林主人提供的技术附件_

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
