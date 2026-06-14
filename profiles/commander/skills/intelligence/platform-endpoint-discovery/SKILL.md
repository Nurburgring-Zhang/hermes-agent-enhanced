---
name: platform-endpoint-discovery
description: 通过curl终端测试发现平台API端点的系统性方法
triggers:
  - 采集器平台失败
  - 寻找平台可用端点
  - 绕过CAPTCHA/WAF
---

# 平台端点发现方法论

## 核心发现（2026-04-21）

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时


### 数据中心IP封锁现象
WSL/datacenter IP被以下平台封锁：
- 微信公众号（搜狗入口CAPTCHA）
- 小红书（IP风险300012）
- 知乎（需登录+JS渲染空白）
- 百度（Slider验证）
- 微博API（Forbidden）
- 快手（需手机验证）

**根本原因**：所有中国主流平台对数据中心IP有严格风控，browser指纹和curl请求都会被拦截。

---

## 已验证工作的端点

### 今日头条（通过curl测试确认有效）
```bash
# 热榜JSON（返回data数组，每项含Title/HotValue/Url）
curl -s --max-time 10 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"

# 解析：json.loads(response) → data[i]["Title"], data[i]["HotValue"], data[i]["Url"]
```

### 微博热搜
```bash
# 实时热搜（需User-Agent + Referer）
curl -s --max-time 10 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -H "Referer: https://weibo.com/" \
  "https://weibo.com/ajax/side/hotSearch"

# 解析：data["data"]["realtime"][i]["word"], ["raw_hot"]
# 备用：data["data"]["band_list"][i]["word"], ["hot_number"]
```

### 36氪
```bash
# RSS源（最稳定）
curl -s --max-time 10 "https://36kr.com/feed"

# 解析：XML → channel/item → title, link
```

### bilibili（稳定）
```bash
# 热门视频API
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all"
# 解析：data["list"][i]["title"], ["aid"], ["tname"]
```

### GitHub（稳定）
```bash
# Trending
curl -s "https://github.com/trending"
# 或API
curl -s "https://api.github.com/search/repositories?q=created:>$(date -d '7 days ago' +%Y-%m-%d)&sort=stars"
```

### 海外科技媒体（curl测试可用）
```bash
# Ars Technica
curl -s "https://feeds.arstechnica.com/arstechnica/index"

# Wired
curl -s "https://www.wired.com/feed/rss"

# TechCrunch
curl -s "https://techcrunch.com/feed/"
```

---

## 端点发现标准流程

1. **curl快速测试**（先于代码实现）
```bash
curl -s --max-time 10 -A "Mozilla/5.0" "TARGET_URL" | head -50
```

2. **检查响应码和内容**
   - 200 + HTML → 可能需要JS渲染
   - 200 + JSON → 检查数据结构
   - 403/Forbidden → IP被封
   - 302/+CAPTCHA → 需要浏览器或代理
   - Timeout → 平台超时或不可达

3. **尝试不同User-Agent**
```bash
-A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
-A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
```

4. **尝试添加Referer/Accept头**
```bash
-H "Referer: https://www.target.com/"
-H "Accept: application/json"
```

5. **测试完成后再写代码** — 避免在错误端点上浪费开发时间

---

## 数据库表结构（intelligence.db）
```sql
-- 实际表名：raw_intelligence（不是articles！）
CREATE TABLE raw_intelligence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    source TEXT,
    platform TEXT,
    author TEXT,
    author_id TEXT,
    category TEXT,
    tags TEXT,
    hot_score REAL DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    collect_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    published_at TEXT,
    collected_at DATETIME DEFAULT (datetime('now')),
    raw_data TEXT
);
```

---

## 已知问题
- v4采集器使用了错误的表名`articles`，需修复为`raw_intelligence`
- 数据严重不平衡（bilibili占85%），需要调整采集权重

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
