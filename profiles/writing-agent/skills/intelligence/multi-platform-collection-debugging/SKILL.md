---
name: multi-platform-collection-debugging
description: Hermes多平台信息采集调试方法论 - 修复微博/头条/快手等平台API采集问题
triggers:
  - 微博采集失败403
  - 头条JSON截断
  - 平台API返回不完整JSON
  - 多平台采集失败调试
category: intelligence-collection
tags: [api, debugging, json, regex, china-platforms]
author: Hermes
version: 1.0
created: 2026-04-24
---

# Multi-Platform Collection Debugging Methodology

## 核心发现

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时


### 1. 微博API修复 (Weibo Hot Search)
**问题**: `HTTP 403 Forbidden` + JSON截断 (`Unterminated string starting at`)

**根因**: 
- mobile UA被重定向到visitor系统
- JSON响应被截断（服务端在数组闭合前切断连接）

**解决方案**:
```python
def collect_weibo_hot():
    out = fetch("https://weibo.com/ajax/side/hotSearch", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://weibo.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
    })
    if out and '"ok":1' in out[:200]:
        # 安全解析: 在realtime数组末尾截断避免JSON截断问题
        rt_start = out.find('"realtime":[')
        if rt_start >= 0:
            safe = out[rt_start:]
            brace_count = 0
            end_idx = 0
            for i, c in enumerate(safe):
                if c == '[': brace_count += 1
                elif c == ']': brace_count -= 1
                if brace_count == 0 and i > 10:
                    end_idx = i + 1
                    break
            if end_idx > 0:
                d = json.loads(safe[:end_idx])
```

### 2. 今日头条JSON截断修复 (Toutiao)
**问题**: `json.loads` 失败，返回不完整JSON

**解决方案**: 三层备援
```python
try:
    d = json.loads(out)
    # 正常处理
except (json.JSONDecodeError, ValueError):
    # JSON截断时用正则降级提取
    titles = re.findall(r'"title"\s*:\s*"([^"]{5,100})"', out)
    urls = re.findall(r'"article_url"\s*:\s*"(https?://[^"]{10,200})"', out)
    for i, title in enumerate(titles[:20]):
        url = urls[i] if i < len(urls) else 'https://www.toutiao.com/'
        # 添加降级数据...
```

### 3. 快手多端点备援 (Kuaishou)
**问题**: GraphQL query不正确时返回空

**解决方案**: 尝试多个GraphQL query格式
```python
queries = [
    '{"operationName":"HotSearch","variables":{},"query":"query HotSearch{hotSearch{title playCount}}"}',
    '{"operationName":"hotSearch","variables":{},"query":"query hotSearch{hotSearch{title}}"}',
    '{"operationName":"HotSearchContent","variables":{"cursor":0,"limit":20},"query":"query HotSearchContent{hotSearchContent(cursor:0,limit:20){title}}"}',
]
for q in queries:
    out = fetch(..., post_data=q)
    if out and len(out) > 50:
        d = json.loads(out)
        # 尝试多个可能的JSON路径
        for path in ['data.hotSearch', 'data.hotSearchContent', 'data']:
            node = d
            for k in path.split('.'):
                if k == 'data': continue
                node = node.get(k, [])
```

## 调试流程

1. **API端点测试** → 用curl/urllib测试不同UA和端点
2. **响应分析** → 检查200响应 vs 403/重定向
3. **JSON完整性** → 尝试json.loads()，捕获JSONDecodeError
4. **正则降级** → JSON失败时用正则从raw HTML/text提取数据
5. **Playwright兜底** → API和HTML都失败时用浏览器JS渲染

## 关键经验

- **桌面Chrome UA是万能钥匙**: 很多平台对desktop UA更宽松
- **JSON截断用brace-counting**: 找到`[`计数到`]`匹配就截断
- **正则降级是保底方案**: 从任意文本提取目标数据
- **清洗batch_size要设大**: 默认200太小，2000+更合理
- **并行采集看关键指标**: 成功/失败/超时/数据量

## 验证命令

```bash
# 测试微博API
python3 -c "
import urllib.request, ssl, json
ctx = ssl.create_default_context()
url = 'https://weibo.com/ajax/side/hotSearch'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://weibo.com/',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json, text/plain, */*',
})
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    print(r.read(1000).decode('utf-8', errors='ignore')[:200])
"

# 测试采集器
python3 scripts/hermes_collector_v6.py --platform weibo_hot
python3 scripts/hermes_collector_v6.py --platform toutiao

# 运行完整管线
python3 scripts/master_v6_pipeline.py --full
```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
