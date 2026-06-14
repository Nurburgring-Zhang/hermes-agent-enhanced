# Cron Auto-Pause 检测与恢复

## 现象
cronjob列表显示job存在但 `enabled: false, state: paused`。
自进化引擎(self_evolve)自动pause了因"Script not found"失败的job，但**不推送告警**。

## 检测
```
cronjob list | python3 -c "
import sys,json
d=json.load(sys.stdin)
paused=[j for j in d['jobs'] if not j['enabled']]
if paused:
    print(f'{len(paused)}个job被pause:')
    for j in paused: print(f'  {j[\"name\"]}: {j[\"paused_reason\"]}')
else:
    print('所有job正常')
"
```

## 恢复
```
# 找到paused的job_id
cronjob action=list

# 重新启用
cronjob action=update job_id=<JOB_ID> schedule="* * * * *"
```

## 预防
- 部署新cron后立即验证enabled=true, state=scheduled
- context_selfcheck应包含cron状态检查
