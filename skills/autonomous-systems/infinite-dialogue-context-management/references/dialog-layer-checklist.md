# 对话层修复核查清单

当格林主人问"xxx完美实现了吗？在所有对话中都能主动运行了吗？"
→ 先确认问的是哪个系统，然后按以下步骤核查。

## 两层核查法

### 第1层：cron层（文件存在性+新鲜度）
```bash
cd ~/.hermes && ls -la reports/context_index.json reports/context_pack.json reports/surgical_context.json reports/context_auto_assoc.json reports/cross_session_cache.json
# 所有文件应在60秒内更新
```

### 第2层：对话层（是否真正被AI使用）
```bash
# 检查cron中所有上下文脚本
crontab -l | grep -E "context|packer|slicer|index|selfcheck|session_init"

# 检查所有脚本是否存在
for f in scripts/context_packer.py scripts/surgical_context_slicer.py scripts/context_auto_assoc.py scripts/context_index_system.py scripts/cross_session_cache.py scripts/context_selfcheck.py scripts/session_init_check.py scripts/context_reconstructor.py scripts/init_hermes_context.sh; do
  [ -f "$f" ] && echo "✅ $f" || echo "❌ $f"
done

# 检查记忆规则
python3 -c "
import sqlite3
conn = sqlite3.connect('active_memory.db')
for row in conn.execute(\"SELECT content FROM memory_entries WHERE content LIKE '%索引%'\"):
    print(row[0][:100])
conn.close()
"

# 检查SOUL.md是否写入上下文压缩规则
grep -c "上下文压缩强制规则" SOUL.md && echo "✅ SOUL.md中有上下文压缩规则"
```

### 全链路完整性测试
```bash
# 复原验证
python3 scripts/context_reconstructor.py verify

# 压缩包含备份规则
python3 -c "import json; d=json.load(open('reports/context_pack.json')); print('备份规则' in d['content'])"

# 索引可追溯
python3 -c "import json; d=json.load(open('reports/context_index.json')); print(f'{d[\"sections_available\"]}章, {d[\"total_tokens\"]}tokens')"
```

## 常见遗漏

1. ❌ 只查cron不查对话层 — cron证明文件系统在跑，不证明AI真的在用
2. ❌ 文件新鲜不等于有人用它替代SOUL.md
3. ❌ 回答前不确认问的是哪个系统
