---
name: reflex-fabric-heartbeat
description: Reflex Fabric heartbeat maintenance — detect stale nodes, clean old messages, output stats. Runs as cron job.
---

# Reflex Fabric Heartbeat Maintenance

## Trigger
Cron job: daily or hourly maintenance of the Reflex Fabric network.

## Steps

1. Run the standalone script (bypasses `agents_company.__init__.py` import chain):
   ```bash
   cd /home/administrator/.hermes && python3 scripts/fabric_heartbeat.py
   ```

2. The script does:
   - **Stale node detection**: Nodes with heartbeat >300s are marked offline
   - **Old message cleanup**: Undelivered messages past their TTL are marked delivered
   - **Old delivered message purge**: Delivered messages >1 hour old are deleted
   - **Fabric self-registration**: Registers its own heartbeat so we know maintenance ran

## Pitfalls

- DO NOT import from `agents_company` package (its `__init__.py` eagerly imports `agents_company_executor` which fails on `No module named 'workflow_definitions'`)
- The standalone script at `scripts/fabric_heartbeat.py` directly connects to `state.db` using sqlite3, bypassing the entire agents_company import chain
- All 508 nodes were registered via `gateway_registry.json` and are offline by default — this is normal unless agents are actively running
- During this run （2026-05-08）, the fabric_heartbeat node itself was also marked offline (last heartbeat from the previous cron run was >4h ago), which is expected — the script always re-registers it after detection
- 1 online node is always fabric_heartbeat after the script runs

## Verification

```bash
python3 scripts/fabric_heartbeat.py
```

Expected output format:
```
Reflex Fabric 心跳维护报告
⏱ 时间:       ...
📊 节点统计
   注册:       508
   在线:       1
   离线:       507
📋 维护操作
   超时下线:   0
   过期消息清理: 0
   旧消息删除:   0
📨 消息统计
   总数:       0
   未投递:     0
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
