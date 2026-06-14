# 采集器扩增实战记录 — 2026-05-28

## 背景

格林主人要求扩大采集平台覆盖范围。原有的33个采集器覆盖了AI/手机/新能源/军事等核心方向，但
**摄影/相机、格斗/UFC、芯片/半导体、旅游**四个偏好方向没有专属采集源。

## 执行过程

### Phase 1: 全量评估 (Recap)

**步骤**:
1. 读取数据库 `SELECT platform, COUNT(*), MAX(collected_at) FROM raw_intelligence GROUP BY platform`
2. 读取 `unified_collector_v5.py` 的 `COLLECTORS` 注册表 → 发现priority=1的平台有11个从未产出数据
3. 读取 `collector_preferences.json` 确认P0/P1/P2方向
4. 测试境外RSS在国内WSL下的可用性
5. 检查cron配置

**发现**:
- 33个注册采集器中，约22个**从未或近期无数据**
- GitHub Trending使用 `search/repositories?q=stars:>1` 返回差
- HuggingFace/掘金/腾讯云/虎嗅/知乎日报/Dev.to 等priority=1 → 被 `is_worth_collecting()` 以50%概率跳过
- 蜂鸟网 `fetch()` 返回GBK编码乱码
- 穷游 `qyer.com` RSS可用(已验证111条)
- 境外RSS(Sherdog/BloodyElbow/PetaPixel)间歇性被国内网络限流

### Phase 2: 制定扩增方案

分三步执行:
1. **恢复停摆平台** — GitHub Trending改HTML爬取, priority从1→7提升
2. **新增四个方向的专属源**
3. **优化cron频率** + 修复过程中发现的bug

### Phase 3: 执行+修复+验证

经历了多次bug发现和修复循环:

#### Bug 1: csdn_blogs 返回值类型不匹配

**症状**: `collect_platform` 报错 `'int' object has no attribute 'get'`
**根因**: `csdn_blog_collector.collect_csdn_blogs()` 返回 `(saved, 0, 0)` 元组（它自己入库），
但 `collect_platform` 用 `insert_batch(items)` 处理，元组被当作列表遍历，int被当作item。
**修复**: 用 `wrap_csdn()` 包装，返回标准item列表。

#### Bug 2: match类型采集器永远0条入库

**发现**: photo_match/mma_match/semi_match 函数能正确返回items(27/15/15条)，
但数据库中查询 `platform='photo_match'` 始终是0条。

**根因① — url_hash算法不兼容**:
数据库中的 `url_hash` 是MD5格式（由旧采集器写入），而 `url_hash()` 函数用SHA256[:32]。
`INSERT OR IGNORE` 以url_hash去重，已经存在的url被忽略。

**根因② — 偏好过滤误杀**:
match数据的content为空字符串（提取自已有记录），title也不一定命中偏好关键词。
`is_user_interest()` 判断为不感兴趣 → `return False`。

**修复**: match类型数据在 `insert_raw_item()` 顶部走特殊分支：
- 使用 `WHERE url=?` 直接匹配URL（绕过hash差异）
- 跳过所有过滤（数据就是按偏好匹配出来的，不需要再过滤）

```python
if source_type == 'match':
    tags = item.get('category_tags','')
    url_val = item.get('url','')
    db.execute(\"UPDATE raw_intelligence SET ... WHERE url=?\", (tags, url_val))
    db.commit()
    return True
```

#### Bug 3: 蜂鸟网GBK编码乱码

**症状**: 「全焦段4K Live星光璀璨」变成「ȫ����4K Live�ǹ���」
**根因**: 蜂鸟网返回GB2312编码但无charset头，`fetch()` 函数默认UTF-8解码破坏了原始字节。
**修复**: 直接 `urlopen` 获取原始字节后 `.decode('gbk', errors='replace')`

```python
req = Request(url, headers=headers)
resp = urlopen(req, timeout=10)
raw_bytes = resp.read()
html = raw_bytes.decode('gbk', errors='replace')
```

#### Bug 4: GitHub Trending超时

**症状**: 采集结果总是 `-- github_trending: no data 15000ms`
**根因**: GitHub页面加载慢，`collect_platform` 的线程超时仅15s。
**修复**: `t.join(timeout=15)` → `t.join(timeout=30)`

#### Bug 5: tags重复拼接

**症状**: 数据库里 `Photo|Camera|Match|Photo|Camera|Match` 重复6次
**根因**: 旧代码 `CASE WHEN category_tags='' THEN ? ELSE category_tags || '|' || ? END` 每次UPDATE都会追加。
**修复**: 检查当前tag是否已存在，只追加不存在的部分。

### Phase 4: cron优化

```
之前: 0 */6 * * *  (每6小时一次)
之后: 0 */3 * * * (每3小时，8并发)
      30 */6 * * * (每6小时加重，14并发)
```

### Phase 5: 最终验证

```
注册采集器: 33→48
今日入库: ~800→1667条
活跃平台: ~12→26个
全部偏好方向均有数据
cron: 3小时/6小时双频
```

## 关键教训

### 1. 验证数据库格式和代码假设是否一致
这次最大的教训是**不要假设数据库里存的格式和代码里用的格式一致**。
- CSDN自采集器用MD5 url_hash → v5采集器用SHA256 → 混合在一起没人知道
- `is_user_interest()` 会过滤掉match类型的数据（content为空）

### 2. 加新功能时要检查所有已有路径不被破坏
match类型插入走的是 `insert_raw_item()` 路径，这个函数有3层过滤在前面。
任何新加的source_type必须确认不被过滤拦截。

### 3. 收集式策略 vs 主动爬取
国内WSL环境下，海外RSS/API不可靠。最佳策略是：
1. 先用国内源（微博/头条/CSDN/Sina）大量采集
2. 然后用match模式从采集结果中按关键词提取特定方向内容
3. 海外RSS作为补充分（能通就有，不通不影响）

### 4. 备份习惯
所有删除/覆盖写/批量修改前先备份到 `/mnt/d/Hermes/备份/`。
这次备份了crontab和collector_preferences.json。

## 新增平台信息

### qyer（穷游）— 已验证全链路
- RSS URL: `https://www.qyer.com/rss/`
- 返回格式: 标准RSS 2.0，约20-30条/次
- 编码: UTF-8
- 入库: ~111条/次采集

### fengniao（蜂鸟网）
- URL: `https://www.fengniao.com/`
- 编码: GB2312（无charset头）
- 抓取方式: 直接urllib获取原始字节→GBK解码
- HTML解析: 用re.findall匹配h2内a标签的title属性
- 产出: 约4-8条/次（首页热门文章）

### SonyRumors — 已验证
- RSS URL: `https://www.sonyalpharumors.com/feed/`
- 可访问（已验证7条）
- category_tags: Sony|Rumors|Photo|Camera|Gear

## 已停摆但加了fallback的平台

| 平台 | 原始端点 | fallback策略 |
|------|---------|-------------|
| juejin | api.juejin.cn API | 从已有数据匹配开发者话题(前端/后端/Spring/React/Vue) |
| tencent_cloud | RSS端点失效 | 匹配云原生/容器/K8s/Docker/Serverless话题 |
| huxiu | RSS端点失效 | 匹配创业/融资/商业/IPO/独角兽话题 |
| huggingface | API限流 | 保留原API调用 |
