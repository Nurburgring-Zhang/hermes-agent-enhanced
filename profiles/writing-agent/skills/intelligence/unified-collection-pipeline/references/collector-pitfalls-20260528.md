# 采集器常见陷阱与修复 — 本会话实战总结（2026-05-28更新，共11个陷阱）

## 陷阱1: csdn_blogs 自采集器返回值不兼容

**场景**: 把独立自采集器注册到 unified_collector_v5.py 的 COLLECTORS 字典
**报错**: `'int' object has no attribute 'get'`
**根因**: 自采集器自己负责入库，返回 `(saved, 0, 0)` 元组而不是items列表。
`collect_platform` 的 `insert_batch(items)` 把元组当列表遍历，int被当item处理。
**检测**:
```bash
grep 'def collect' csdn_blog_collector.py
# 看return语句
```
**修复**: 包装一层:
```python
def wrap_csdn():
    try:
        saved, _, _ = collect_csdn_blogs()
    except:
        saved = 0
    return [{'platform': 'csdn', 'title': f'csdn collected {saved} items',
             'url': 'https://blog.csdn.net/', 'source_type': 'api'}]
```
**注册**: `'csdn_blogs':(wrap_csdn,7,90)`

## 陷阱2: match类型数据被偏好过滤拦截

**场景**: 新增_match采集器（从已有数据按关键词匹配）后，函数返回items正确，但数据库无变化
**根因**: `insert_raw_item()` 函数顶部的 `is_user_interest()` 过滤：
- match数据content为空（提取自已有记录）
- title不一定命中偏好关键词
- 导致 `is_user_interest()` 返回False → 直接return False

**修复**: match类型在进入任何过滤之前走特殊分支:
```python
source_type = item.get('source_type','terminal')
if source_type == 'match':
    # 直接更新标签，跳过所有过滤
    db.execute("UPDATE raw_intelligence SET category_tags=? WHERE url=?", ...)
    return True
```

## 陷阱3: url_hash 算法不兼容

**场景**: match类型的UPDATE `WHERE url_hash=?` 永远影响0行
**根因**: 数据库中的 `url_hash` 是 **MD5(32位)** 格式（由早期CSDN等采集器写入），
但 `url_hash()` 函数使用 `hashlib.sha256(...).hexdigest()[:32]`。
两种hash完全不同。
**检测**:
```bash
python3 -c "
import hashlib
url = 'https://example.com'
print(f'MD5:    {hashlib.md5(url.encode()).hexdigest()[:32]}')
print(f'SHA256: {hashlib.sha256(url.encode()).hexdigest()[:32]}')
"
```
**修复**: match类型用 `WHERE url=?` 直接匹配URL字符串:
```python
db.execute("UPDATE ... WHERE url=?", (tags, item['url']))
```

## 陷阱4: 中文RSS站点GBK编码

**场景**: 蜂鸟网(fengniao.com)的HTML返回中文乱码
**根因**: 站点无charset头，但实际编码GB2312。`fetch()` 默认UTF-8解码破坏了原始字节。
**检测**: 看返回原始字节的charset:
```bash
curl -s -I https://www.fengniao.com/ | grep -i charset
# → 无charset！实际是GB2312
```
**修复**: 绕过fetch，直接urllib获取原始字节后指定编码:
```python
req = Request(url, headers=headers)
resp = urlopen(req, timeout=10)
raw_bytes = resp.read()
html = raw_bytes.decode('gbk', errors='replace')
```
**规约**: 中文网站如果返回乱码，先试GBK/GB2312解码。

## 陷阱5: tags拼接无限重复

**场景**: 同一行数据的 `category_tags` 出现 `Photo|Photo|Photo|Photo|Camera|Camera|...`
**根因**: UPDATE语句 `CASE WHEN category_tags='' THEN ? ELSE category_tags || '|' || ? END`
每次运行都追加，多次cron执行导致无限叠加。
**修复**: 先SELECT检查当前值然后去重:
```python
existing = db.execute("SELECT category_tags FROM raw_intelligence WHERE url=?", ...).fetchone()
if existing:
    cur_tags = existing[0] or ''
    tag_parts = tags.split('|')
    for t in tag_parts:
        if t and t not in cur_tags:
            new_tags = (new_tags + '|' + t) if new_tags else t
    db.execute("UPDATE ... SET category_tags=?", (new_tags,))
```

## 陷阱6: GitHub Trending 15s超时

**场景**: 每次采集 `github_trending` 都显示 `no data 15000ms`
**修复**: `collect_platform` 的线程join超时只有15s。GitHub页面加载慢于15s。
**修复**: 线程超时 15→30s，独立采集器timeout 60→120s。

## 陷阱9: parse_rss() 的CDATA清洗破坏标准XML

**场景**: `parse_rss()` 返回0条，但直接 `ET.fromstring()` 能解析出15条RSS
**根因**: `parse_rss()` 中的 `re.sub(r'\\]\\]>', '', xml_text)` 全局删除 `]]>`，但这是有效的XML标准。CDATA段的结尾标记 `]]>` 是XML规范的一部分，不应全局删除。某些RSS feed依赖于 `]]>` 来正确终止CDATA块。
**检测**: 
```bash
# 对比parse_rss和ET直解析
python3 -c "
import xml.etree.ElementTree as ET, re
data = fetch('https://example.com/feed')
# parse_rss版本
cleaned = re.sub(r'\\]\\]>', '', data)
result1 = len(re.findall(r'<item>', cleaned))
# ET直解析版本
root = ET.fromstring(data.encode('utf-8'))
result2 = len(root.findall('.//item'))
print(f'parse_rss: {result1}, ET直解析: {result2}')
"
```
**修复**: 新采集器内的RSS解析改用ET.fromstring()直接解析，跳过parse_rss()：
```python
import xml.etree.ElementTree as ET
root = ET.fromstring(out.encode('utf-8'))
ns = {'content':'http://purl.org/rss/1.0/modules/content/'}
for entry in root.iter('item'):
    title = entry.findtext('title','')
    link = entry.findtext('link','')
    content_el = entry.find('content:encoded', ns)
    content = content_el.text if content_el is not None else entry.findtext('description','')
    if title and link:
        items.append({'title':title.strip(), 'content':content or '', 'url':link})
```
**规约**: 对已知XML-valid的RSS feed优先用ET.fromstring()直接解析，parse_rss()仅作为fallback。
注意：ET.fromstring()要求完整根元素，如果out包含多个文档或垃圾前缀会报错。需要时先截取`<rss...>...</rss>`或`<feed...>...</feed>`部分。

## 陷阱10: 国内门户RSS源已基本废弃

**场景**: 新增采集器时写入大量RSS端点URL，但全部返回404
**根因**: 国内门户（新浪/搜狐/网易/腾讯/虎扑/央视等）自2020年起逐步废弃了公共RSS订阅功能。目前还在维护的RSS只有少量垂直站（IT之家/OSChina/InfoQ/摄影世界等）。
**检测**: 新增源之前先快速测试：
```python
def test_feed(url, name):
    import urllib.request, re
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=8)
        data = resp.read().decode('utf-8', errors='replace')
        if '<rss' in data or '<feed' in data:
            n = len(re.findall(r'<item>|<entry>', data))
            return f'✅ RSS可用 ({n}条)'
        return f'⚠️ 非RSS ({len(data)}字符)'
    except Exception as e:
        return f'❌ {e}'
```
**已验证可用的国内RSS**: IT之家, OSChina, InfoQ, 摄影世界, 摄影之友(间歇500), TechMeme, FreeBuf, 博客园(需BOM修复)
**已验证废弃的RSS**: 新浪体育/新浪MMA/新浪综合 → 404；搜狐体育 → 404；网易体育 → 404；腾讯体育 → 301/404；虎扑 → HTML page；央视体育 → HTML page；格斗迷 → timeout；色影无忌 → 403/404

## 陷阱11: cron 条目重复/冗余导致系统退化

**场景**: 两个完全相同的cron同时运行，系统行为变成双倍
**根因**: 新系统（Hermes gateway管理的cron）和旧系统（crontab -l）并行运行，同一功能被多次注册。且历史cron job未及时清理，长期累积后从1-2个膨胀到67+个。
**修复**: 参见 `references/cron-audit-methodology.md` 中的完整审计方法论。核心规则：
1. core cron < 15个
2. 定期检查 `cronjob list` 的数量
3. 每次会话结束时检查临时cron是否已完成并清理

## 陷阱7: collect_platform 的collect_all() ValueError

**场景**: 新增平台到 `COLLECTORS` 后运行 `--collect` 报 `too many values to unpack`
**根因**: `filtered` 列表是 `(name, fn, pri)` 三元组，但解包写成 `for name,(fn,pri) in filtered`。
**修复**: 改为 `for name,fn,pri in filtered`。

## 陷阱8: 当collector_preferences.json 被更新时，旧代码里硬编码的关键词要同步

**场景**: 新增了Photo/Travel/Fight方向标签，但`extract_tags()`函数里的关键词列表没同步
**根因**: `extract_tags()` 有硬编码的关键词列表（40+方向），与 `collector_preferences.json` 独立管理
**修复**: 无（功能上两个系统各自独立，偏好过滤用preferences.json，标签提取用extract_tags硬编码）
