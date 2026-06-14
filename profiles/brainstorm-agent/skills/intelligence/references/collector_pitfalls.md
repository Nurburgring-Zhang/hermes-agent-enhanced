# 采集器常见陷阱与修复记录

## 1. csdn_blogs 自采集器包装问题

**症状**: `collect_platform` 报错 `'int' object has no attribute 'get'`  
**根因**: csdn_blog_collector.py 的 `collect_csdn_blogs()` 返回 `(saved, 0, 0)` 元组（它自己入库），而 `collect_platform` 用 `insert_batch(items)` 处理返回结果时，元组被当列表遍历，int被当作item。  
**修复**: 用 `wrap_csdn()` 包装，返回标准item列表：`[{'platform':'csdn', 'title':..., 'url':..., 'source_type':'api'}]`  
**规约**: 所有自采集器（自己入库不依赖v5的insert_batch）必须包装，返回格式统一的item列表。

## 2. url_hash 算法不兼容

**症状**: match采集器 `UPDATE ... WHERE url_hash=?` 永远更新0行  
**根因**: 不同采集器用不同hash算法——CSDN自采集器用MD5(32位)，v5采集器用SHA256[:32]。数据库里两种hash混存。  
**修复**: match类型改用 `WHERE url=?` 直接匹配URL字符串。  
**规约**: match/update类型操作不要依赖url_hash，直接用url匹配。

## 3. match类型被偏好过滤拦截

**症状**: match采集器函数返回了items，但insert_raw_item返回False，数据库没有变化  
**根因**: `insert_raw_item` 前3步全是过滤检查（偏好→黑名单→质量），match类型的数据content=空字符串，导致 `is_user_interest()` 返回False被丢弃。  
**修复**: 在`insert_raw_item`顶部添加 `if source_type == 'match':` 分支，先于所有过滤执行UPDATE，直接返回。  
**规约**: match类型必须跳过所有过滤逻辑。

## 4. 蜂鸟网GBK编码

**症状**: 「全焦段4K Live星光璀璨」变成乱码「ȫ����4K Live�ǹ���」  
**根因**: 蜂鸟网返回GB2312编码但无charset头，fetch函数默认用UTF-8解码破坏了原始字节。  
**修复**: 直接 `urllib.request.urlopen` 获取原始字节后 `.decode('gbk', errors='replace')`，不经过fetch的自动解码。  
**规约**: 中文网站如果返回乱码，检查响应头是否有charset，没有就试GBK/GB2312解码。

## 5. GitHub Trending 超时

**症状**: 采集结果总是 `-- github_trending: no data 15000ms`  
**根因**: GitHub页面加载慢，`collect_platform` 的线程超时仅15s，不够。  
**修复**: 线程超时15→30s，GitHub超时参数60→120s。  
**规约**: 境外源适当放宽超时。

## 6. tags重复拼接

**症状**: 数据库里 `Photo|Camera|Match|Photo|Camera|Match` 重复多次  
**根因**: 旧代码 `CASE WHEN category_tags='' THEN ? ELSE category_tags || '|' || ? END` 每次UPDATE都会拼接，多次运行导致无限叠加。  
**修复**: 插入前SELECT检查当前tags，每个tag部分检查是否已存在，只追加不存在的部分。  
**规约**: 任何拼接型UPDATE必须先检查再执行。
