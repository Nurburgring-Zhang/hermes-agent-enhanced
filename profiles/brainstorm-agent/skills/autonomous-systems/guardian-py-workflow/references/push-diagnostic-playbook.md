# Push 推送诊断手册 (v12)

## 用户说"没收到推送"时的诊断流程

### 第1步：看最后推送日志（最快定位）
```bash
tail -30 ~/.hermes/logs/cron_push.log      # guardian push日志
tail -30 ~/.hermes/logs/v12_push.log        # v12推送详细日志
```

关键信号：
- `✅ 推送成功` → PushPlus返回200，微信已发出。用户没收到=微信问题
- `❌ 推送失败: 服务端验证错误` → PushPlus token过期或格式问题
- `DRY RUN模式` → 脚本在测试模式没真推

### 第2步：查推送记录（确认是否有数据出去）
```bash
cd ~/.hermes && python3 -c "
import sqlite3
db = sqlite3.connect('intelligence.db')
cu = db.execute('SELECT COUNT(*), MAX(push_time) FROM push_records')
print(f'总推送: {cu.fetchone()}')
cu = db.execute('SELECT push_time, title FROM push_records ORDER BY push_time DESC LIMIT 5')
for r in cu.fetchall():
    print(f'  {r[0]} | {r[1][:40]}')
db.close()
"
```

### 第3步：检查推送候选池（是否有数据可取）
```bash
cd ~/.hermes && python3 -c "
import sqlite3
db = sqlite3.connect('intelligence.db')
cu = db.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total >= 15')
print(f'可推送(评分≥15): {cu.fetchone()[0]}')
cu = db.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0 OR ai_score_total IS NULL')
print(f'未评分: {cu.fetchone()[0]}')
cu = db.execute('SELECT collected_at, title FROM cleaned_intelligence ORDER BY rowid DESC LIMIT 3')
for r in cu.fetchall():
    print(f'  最新: {r[0]} | {r[1][:40]}')
db.close()
"
```

### 第4步：检查采集正常
```bash
cd ~/.hermes && python3 -c "
import sqlite3
db = sqlite3.connect('intelligence.db')
cu = db.execute('SELECT COUNT(*) FROM raw_intelligence')
print(f'raw: {cu.fetchone()[0]}')
cu = db.execute('SELECT COUNT(*) FROM cleaned_intelligence')
print(f'clean: {cu.fetchone()[0]}')
cu = db.execute('SELECT COUNT(*) FROM raw_intelligence WHERE collected_at > datetime(\"now\", \"-1 day\")')
print(f'今日采集: {cu.fetchone()[0]}')
"
```

### 第5步：已知故障模式

| 症状 | 根因 | 修复 |
|------|------|------|
| 08:00失败但08:20成功 | PushPlus临时验证超时 | 重试机制已内置，等下一轮 |
| `推`送成功但没收到 | 微信延迟/PushPlus队列 | 等5分钟看 |
| 12:00/18:00全部"服务端验证错误" | PushPlus token过期 | 刷新token |
| 前一天有推送今天全失败 | cron调度停了 | crontab -l检查，重新添加 |
| "无候选"→推0条 | 采集断了/评分积压 | 检查unified_collector |
| 评分全0 | DeepSeek model名错误(deepseek/deepseek-chat → deepseek-chat) | 修复model名后手动回填 |
| `data/push_records.db` 是0字节 | 推送记录在intelligence.db里直接用 | 不影响推送，只是历史记录文件 |
