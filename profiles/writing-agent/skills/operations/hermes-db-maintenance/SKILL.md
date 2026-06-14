---
name: hermes-db-maintenance
title: "Hermes Database Maintenance Suite"
description: "Systematic database maintenance for all Hermes SQLite databases — WAL checkpoint, vacuum, dedup, size monitoring, freelist reclamation, and archival compression. Consolidates patterns from bulk_clean.py, cleanup_state_db.py, vacuum_state.py, hermes_deep_clean_v1/2.py, and archive_compressor.py."
domain: operations
priority: medium
triggers:
  - "clean database"
  - "vacuum db"
  - "reclaim space"
  - "数据库维护"
  - "db maintenance"
  - "purge duplicates"
  - "dedup intelligences"
  - "compress archives"
  - "check db size"
  - "free up space"
  - "wal checkpoint"
  - "incremental vacuum"
version: "1.0"
created: "2026-05-07"
---

# Hermes Database Maintenance Suite

Systematic maintenance for all Hermes SQLite databases. Run periodically (recommended: weekly) or on demand when DB grows too large.

## Database Paths

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


| Database | Path | Typical Size | Notes |
|----------|------|-------------|-------|
| Intelligence DB | `~/.hermes/intelligence.db` | 30-200MB | Main intel store |
| State DB | `~/.hermes/state.db` | 215MB + ~200MB WAL | Gateway holds write-lock |
| Push History | `~/.hermes/scripts/push_history.db` | Small | Push records |
| Pipeline Runs | `~/.hermes/scripts/pipeline_runs.sqlite` | Small | Pipeline metadata |
| State DB WAL | `~/.hermes/state.db-wal` | Up to 200MB | Can't shrink (gateway lock) |

## Step 1: Check Database Sizes

```bash
echo "=== Intelligence DB ==="
ls -lh ~/.hermes/intelligence.db
echo ""
echo "=== State DB ==="
ls -lh ~/.hermes/state.db*
echo ""
echo "=== All DB files ==="
find ~/.hermes -name "*.db" -o -name "*.sqlite" | while read f; do
  wal="${f}-wal"
  wal_size=""
  [ -f "$wal" ] && wal_size=" (WAL: $(ls -lh "$wal" | awk '{print $5}'))"
  echo "$(ls -lh "$f" | awk '{print $5, $NF}')$wal_size"
done
```

## Step 2: WAL Checkpoint (Release WAL)

```bash
python3 -c "
import sqlite3, os

dbs = [
    '$HOME/.hermes/intelligence.db',
    '$HOME/.hermes/state.db',
    '$HOME/.hermes/scripts/push_history.db',
]

for db_path in dbs:
    if not os.path.exists(db_path):
        print(f'⚠️  Not found: {db_path}')
        continue
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cur = conn.cursor()
        cur.execute('PRAGMA wal_checkpoint(TRUNCATE);')
        row = cur.fetchone()
        # row = (busy, log, checkpointed)
        wal_file = db_path + '-wal'
        wal_size = os.path.getsize(wal_file) if os.path.exists(wal_file) else 0
        print(f'✅ {os.path.basename(db_path)}: WAL checkpointed (busy={row[0]}, log_pages={row[1]}, ckpt_pages={row[2]}, wal_remaining={wal_size}B)')
        conn.close()
    except Exception as e:
        print(f'❌ {os.path.basename(db_path)}: WAL checkpoint failed: {e}')
"
```

**Note:** `state.db` WAL cannot be fully checkpointed because the gateway process holds an active write-lock. The WAL file remaining ~200MB is normal. Alert only if >500MB+500MB.

## Step 3: Check Freelist and Reclaim Space

```python
python3 -c "
import sqlite3, os

db_path = os.path.expanduser('~/.hermes/intelligence.db')
conn = sqlite3.connect(db_path, timeout=60)
cur = conn.cursor()

# Check freelist
cur.execute('PRAGMA freelist_count;')
free = cur.fetchone()[0]
print(f'Freelist pages: {free}')

# Check page count
cur.execute('PRAGMA page_count;')
pages = cur.fetchone()[0]
print(f'Total pages: {pages}')
print(f'Page size: {cur.execute(\"PRAGMA page_size\").fetchone()[0]}')

# If freelist > 100 pages, reclaim incrementally
if free > 100:
    reclaim = min(free, 10000)
    print(f'Reclaiming {reclaim} freelist pages...')
    cur.execute(f'PRAGMA incremental_vacuum({reclaim});')
    conn.commit()
    print('✅ Incremental vacuum done')
else:
    print('✅ Freelist is healthy, no vacuum needed')

conn.close()
"
```

## Step 4: Deduplicate Raw Intelligence

Removes duplicate entries from `raw_intelligence` based on `url_hash`:

```python
python3 -c "
import sqlite3, os

db_path = os.path.expanduser('~/.hermes/intelligence.db')
conn = sqlite3.connect(db_path, timeout=60)
cur = conn.cursor()

# Check for duplicates
cur.execute('''
    SELECT url_hash, COUNT(*) as cnt
    FROM raw_intelligence
    GROUP BY url_hash
    HAVING cnt > 1
''')
dupes = cur.fetchall()
print(f'Found {len(dupes)} duplicate url_hash groups')

if dupes:
    total_removed = 0
    for url_hash, cnt in dupes:
        # Keep the first (oldest) entry, delete the rest
        cur.execute('''
            DELETE FROM raw_intelligence
            WHERE url_hash = ? AND id NOT IN (
                SELECT MIN(id) FROM raw_intelligence WHERE url_hash = ?
            )
        ''', (url_hash, url_hash))
        total_removed += cur.rowcount
    conn.commit()
    print(f'✅ Removed {total_removed} duplicate records')

    # Also check cleaned_intelligence
    cur.execute('''
        SELECT url_hash, COUNT(*) as cnt
        FROM cleaned_intelligence
        GROUP BY url_hash
        HAVING cnt > 1
    ''')
    cleaned_dupes = cur.fetchall()
    if cleaned_dupes:
        for url_hash, cnt in cleaned_dupes:
            cur.execute('''
                DELETE FROM cleaned_intelligence
                WHERE url_hash = ? AND id NOT IN (
                    SELECT MIN(id) FROM cleaned_intelligence WHERE url_hash = ?
                )
            ''', (url_hash, url_hash))
        conn.commit()
        print(f'✅ Removed duplicates from cleaned_intelligence')

conn.close()
"
```

## Step 5: Deep Clean (Purge Stale Push Candidates)

Remove old push candidates and stale data:

```python
python3 -c "
import sqlite3, os
from datetime import datetime, timedelta

db_path = os.path.expanduser('~/.hermes/intelligence.db')
conn = sqlite3.connect(db_path, timeout=60)
cur = conn.cursor()

# Remove raw_intelligence older than 30 days (already archived)
cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
cur.execute('DELETE FROM raw_intelligence WHERE collected_at < ?', (cutoff,))
deleted = cur.rowcount
print(f'🗑️ Deleted {deleted} raw_intelligence records older than {cutoff}')

# Check push_records for stale records (>14 days)
try:
    cur.execute('SELECT COUNT(*) FROM push_records WHERE created_at < ?', (cutoff,))
    stale = cur.fetchone()[0]
    print(f'Push records older than {cutoff}: {stale}')
except Exception as e:
    print(f'push_records check: {e}')

conn.commit()
conn.close()
"
```

## Step 6: Archive Old Data (7-day cutoff)

Use the dedicated archive script:

```bash
cd ~/.hermes
python3 scripts/archive_old_data.py
```

Or manually:

```python
python3 -c "
import sqlite3, json, os
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / '.hermes'
db = str(HERMES / 'intelligence.db')
conn = sqlite3.connect(db, timeout=60)
cur = conn.cursor()

# Check what would be archived
cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
cur.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE DATE(cleaned_at) < ?', (cutoff,))
old_count = cur.fetchone()[0]
print(f'Records older than 7 days: {old_count}')

if old_count > 0:
    # Archive: insert into history_archive table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS history_archive (
            id INTEGER PRIMARY KEY,
            title TEXT, source TEXT, platform TEXT,
            url TEXT, published_at TEXT,
            importance_score REAL, language TEXT,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        INSERT OR IGNORE INTO history_archive (title, source, platform, url, published_at, importance_score, language)
        SELECT title, source, platform, url, published_at, importance_score, language
        FROM cleaned_intelligence
        WHERE DATE(cleaned_at) < ?
    ''', (cutoff,))
    archived = cur.rowcount
    
    # Delete archived rows
    cur.execute('DELETE FROM cleaned_intelligence WHERE DATE(cleaned_at) < ?', (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    print(f'✅ Archived {archived} records, deleted {deleted} from main table')

conn.close()
"
```

## Step 7: Final Stats Report

```python
python3 -c "
import sqlite3, os
from pathlib import Path

HERMES = Path.home() / '.hermes'
db = str(HERMES / 'intelligence.db')
conn = sqlite3.connect(db, timeout=30)
cur = conn.cursor()

print('=== Database Stats ===')
for table in ['raw_intelligence', 'cleaned_intelligence', 'push_records']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        count = cur.fetchone()[0]
        print(f'{table}: {count:,} records')
    except:
        print(f'{table}: N/A')

# Per-source breakdown for today
cur.execute('''
    SELECT source, COUNT(*) as cnt
    FROM raw_intelligence
    WHERE DATE(collected_at) = DATE('now','localtime')
    GROUP BY source
    ORDER BY cnt DESC
''')
rows = cur.fetchall()
print(f'\\nToday\\'s collection by source ({len(rows)} sources):')
for src, cnt in rows:
    mark = '✅' if cnt > 0 else '❌'
    print(f'  {mark} {src}: {cnt}')

# DB file sizes
print(f'\\nDB file sizes:')
for f in os.listdir(str(HERMES)):
    if f.endswith('.db') or f.endswith('.sqlite'):
        fp = HERMES / f
        size = fp.stat().st_size
        wal = HERMES / (f + '-wal')
        wal_size = wal.stat().st_size if wal.exists() else 0
        print(f'  {f}: {size/1024/1024:.1f}MB (WAL: {wal_size/1024/1024:.1f}MB)')

conn.close()
"
```

## Run Full Routine (One-Liner)

```bash
cd ~/.hermes && python3 scripts/archive_old_data.py && python3 scripts/hermes_archiver.py && python3 -c "
import sqlite3, os
db=os.path.expanduser('~/.hermes/intelligence.db')
c=sqlite3.connect(db,timeout=60);cu=c.cursor()
cu.execute('PRAGMA wal_checkpoint(TRUNCATE)')
cu.execute('PRAGMA freelist_count');f=cu.fetchone()[0]
if f>100:cu.execute(f'PRAGMA incremental_vacuum({min(f,10000)})');c.commit();print(f'Reclaimed {f} pages')
c.close()
print('✅ DB maintenance complete')
"
```

## WAL Growth Monitoring (Added 2026-05-08)

Monitor state.db WAL growth trends to proactively intervene before it reaches critical size (~200MB+).

### Growth Pattern Observed
- Post-VACUUM baseline: state.db ~12MB, WAL=0B
- Growth rate: ~16MB/h (state.db + WAL combined)
- Critical threshold: state.db >100MB OR WAL >80MB OR total(DB+WAL) >180MB
- Peak historic: 206MB (state.db) + ~200MB (WAL) = ~406MB total

### Check WAL Growth Rate

```bash
python3 -c "
import os, time
HERMES = os.path.expanduser('~/.hermes')

def get_wal_info():
    db = os.path.getsize(HERMES + '/state.db')
    wal = os.path.getsize(HERMES + '/state.db-wal') if os.path.exists(HERMES + '/state.db-wal') else 0
    shm = os.path.getsize(HERMES + '/state.db-shm') if os.path.exists(HERMES + '/state.db-shm') else 0
    return db, wal, shm

db, wal, shm = get_wal_info()
total = db + wal
print(f'state.db:  {db/1024/1024:.1f}MB')
print(f'state.db-wal: {wal/1024/1024:.1f}MB')
print(f'state.db-shm: {shm/1024/1024:.1f}MB')
print(f'Total (DB+WAL): {total/1024/1024:.1f}MB')

if total > 200*1024*1024:
    print('⚠️ CRITICAL: Total storage >200MB — immediate checkpoint needed!')
elif total > 150*1024*1024:
    print('⚠️ WARNING: Total storage >150MB — schedule checkpoint soon')
elif total > 100*1024*1024:
    print('🟡 ALERT: Total storage >100MB — monitor closely')
else:
    print('✅ WAL growth within normal range')
"
```

### Auto-Intervene: Checkpoint When Growing Too Fast

```bash
python3 -c "
import os
HERMES = os.path.expanduser('~/.hermes')

db_path = HERMES + '/state.db'
wal_path = db_path + '-wal'
wal_size = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0

if wal_size > 80 * 1024 * 1024:  # >80MB
    import sqlite3
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.close()
        print(f'✅ Auto-checkpoint executed (WAL was {wal_size/1024/1024:.1f}MB >80MB threshold)')
    except Exception as e:
        print(f'❌ Auto-checkpoint failed (gateway lock): {e}')
else:
    print(f'✅ WAL at {wal_size/1024/1024:.1f}MB — below 80MB threshold, no action needed')
"
```

### When sqlite3 CLI is NOT Available

All Hermes database operations use Python's `sqlite3` module directly. The `sqlite3` CLI binary is NOT required:

```bash
# INSTEAD OF:  sqlite3 ~/.hermes/state.db "PRAGMA wal_checkpoint;"
# USE:
python3 -c "import sqlite3; conn=sqlite3.connect('/home/administrator/.hermes/state.db'); r=conn.execute('PRAGMA wal_checkpoint').fetchone(); print(f'checkpoint: busu={r[0]}, log={r[1]}, ckpt={r[2]}'); conn.close()"

# INSTEAD OF:  ls -lh ~/.hermes/state.db-wal
# USE:
python3 -c "import os; f='/home/administrator/.hermes/state.db-wal'; sz=os.path.getsize(f) if os.path.exists(f) else 0; print(f'WAL: {sz/1024/1024:.1f}MB')"
```

## Active Memory DB Path Consolidation (Added 2026-05-08)

`active_memory.db` has been found at **3 separate paths** with different schemas:
1. `~/.hermes/active_memory.db` — **Production** (296KB, 35 tables — actual working DB)
2. `~/.hermes/data/active_memory.db` — **Stale** (4KB, 0 tables — legacy, no data)
3. `~/.hermes/outputs/active_memory.db` — **Semantic index** (16KB, 2 tables — used by some scripts)

### Step-by-Step Consolidation Workflow

```bash
# Step 1: List all active_memory.db paths
echo "=== active_memory.db 副本路径检查 ==="
find ~/.hermes -name "active_memory.db" -type f -exec ls -lh {} \; 2>/dev/null

# Step 2: Verify each database schema (table count)
python3 << 'EOF'
import sqlite3, os
from pathlib import Path

paths = [
    Path.home() / '.hermes' / 'active_memory.db',
    Path.home() / '.hermes' / 'data' / 'active_memory.db',
    Path.home() / '.hermes' / 'outputs' / 'active_memory.db',
]

for p in paths:
    if p.exists():
        try:
            conn = sqlite3.connect(str(p), timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            size = p.stat().st_size
            print(f"{p.relative_to(Path.home())}: {size/1024:.0f}KB, {len(tables)} tables: {tables}")
            conn.close()
        except Exception as e:
            print(f"{p.relative_to(Path.home())}: ERROR: {e}")
    else:
        print(f"{p.relative_to(Path.home())}: not found")
EOF

# Step 3: Clean stale copies (keep only ~/.hermes/active_memory.db)
# Only run these if verification confirms the production DB is correct
python3 << 'EOF'
import sqlite3, os, shutil
from pathlib import Path

production = Path.home() / '.hermes' / 'active_memory.db'
data_copy = Path.home() / '.hermes' / 'data' / 'active_memory.db'
outputs_copy = Path.home() / '.hermes' / 'outputs' / 'active_memory.db'

# Verify production DB is valid
print(f"Production: {production.stat().st_size/1024:.0f}KB")

for stale_path in [data_copy, outputs_copy]:
    if stale_path.exists():
        # Create backup before deletion
        backup = str(stale_path) + ".bak." + os.popen('date +%Y%m%d').read().strip()
        shutil.copy2(str(stale_path), backup)
        os.remove(str(stale_path))
        print(f"✅ 已备份并删除: {stale_path.relative_to(Path.home())} (备份: {backup})")
    else:
        print(f"ℹ️ 不存在: {stale_path.relative_to(Path.home())}")
EOF

# Step 4: Verify only one active_memory.db remains
echo "=== 清理后检查 ==="
find ~/.hermes -name "active_memory.db" -type f 2>/dev/null
```

### Verification After Cleanup
```bash
# Check that all scripts still reference the correct path
grep -rn "active_memory.db" ~/.hermes/scripts/ --include="*.py" --include="*.md" 2>/dev/null | grep -v ".bak" | grep -v "data/active" | grep -v "outputs/active"

# Expected: all references should point to ~/.hermes/active_memory.db (or relative equivalent)
```

### Pitfalls
- Stale copies may be read by old cron jobs — always check cron scripts first
- The `outputs/active_memory.db` may be intentionally used by memory engine scripts — verify before deleting
- Backup stale copies before removal (the workflow above already does this)

## Related Skills

- **`lowscore-cleaning-workflow`** — Score-specific cleanup (archive 0-score items, patch null timestamps, orphaned raw). Complements general DB maintenance when the issue is low-quality scored data rather than structural DB health.
- **`hermes-intelligence-heartbeat`** — Daily health check for the intelligence pipeline. Runs before deciding whether maintenance is needed.

## Pitfalls

1. **state.db cannot be fully vacuumed** — Gateway process (PID varies) holds active connection. WAL will always be ~200MB. Only alert at >500MB+500MB.
2. **No VACUUM on state.db** — Full VACUUM requires exclusive lock which conflicts with gateway. Use incremental_vacuum when possible.
3. **Don't purge archived data** — `history_archive` table holds compressed data. Only purge from raw/cleaned tables.
4. **Backup before major operations** — Copy `intelligence.db` before dedup/clean operations:
   ```bash
   cp ~/.hermes/intelligence.db ~/.hermes/intelligence.db.bak.$(date +%Y%m%d)
   ```
5. **WAL journal_mode** — All Hermes DBs use WAL journal mode by default. Normal checkpointing is automatic. Manual checkpoint is for emergency space reclamation.
6. **Database locked errors** — If maintenance scripts fail with `database is locked`, wait and retry. Other cron jobs may be writing.
7. **sqlite3 CLI binary NOT required** — All operations use Python's built-in `sqlite3` module. Install with `apt install sqlite3` only if manual CLI debugging is needed.
8. **WAL growth is NOT a bug** — Write-ahead logging grows naturally under load. Only intervene when total (DB+WAL) consistently exceeds 200MB or grows >30MB/h over 3+ consecutive checks.

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
