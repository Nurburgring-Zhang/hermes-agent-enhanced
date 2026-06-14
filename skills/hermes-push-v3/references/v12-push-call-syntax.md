# hermes_v12_push.py 调用语法

## 基础命令
```bash
cd ~/.hermes

# DRY RUN模式（预览，不推送）
python3 scripts/hermes_v12_push.py

# 实际推送（必须加 --push）
python3 scripts/hermes_v12_push.py --push
```

## 推送行为
- **无参数**: DRY RUN — 显示预览HTML、排序结果、过滤过程，但**不推送**、**不记录**推送历史
- **`--push`**: 实际调用 PushPlus API 发送微信消息，成功后写入 push_records 表

## 正常输出
成功推送时末尾可见：
```
📤 推送微信(HTML模板)...
✅ 推送成功! (HTML模板)
已记录 N 条推送历史
⏱️ 耗时: X.Xs
```

DRY RUN时末尾可见：
```
🔍 DRY RUN模式 — 不推送
⏱️ 耗时: X.Xs
```

## 2026-06-07 实测（23:57 推送）
- 参数: `--push`
- 候选池: 84条 → 过滤60条 → 最终17条
- 7个平台（Techmeme/新浪/HN/36氪/虎嗅/CSDN/IT之家）
- 推送成功 ✅，耗时0.1s

## 对应的cron配置
```cron
# 🔴 必须带 --push！
0 8 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py --push
0 14 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py --push
0 20 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py --push
0 0 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py --push
```
