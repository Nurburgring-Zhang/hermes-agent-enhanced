# Hermes 全量备份流程

## 目标
将 Hermes 全系统（规则/SKILL/脚本/Agent/引擎/记忆/状态/配置/报告/轨迹）完整导出到指定路径。源在 `~/.hermes/`，目标可以是任何挂载点（`/mnt/m/`、`/mnt/d/` 等）。

## 备份目录结构

```
M:\Hermes\                     # 目标根目录（按需更换挂载点）
├── core/                      # 核心规则文件（SOUL.md, AGENTS.md, CLAUDE.md, .cursorrules, MEMORY.md, USER.md, 所有计划文档）
├── skills/                    # 343个SKILL + 引用文件（tar流式）
├── scripts/                   # 所有Python脚本（tar流式）
├── agents_company/            # 130员工+390专家配置 + 52引擎脚本（tar流式）
├── evolution_v3/              # 7通道记忆/IFC/GEPA/Hooks/子Agent等（tar流式）
├── production_loop/           # 8个强化模块 + cron（tar流式）
├── orchestrate/               # Skills编排引擎（tar流式）
├── state/                     # 5文件状态 + SQLite数据库
├── reports/                   # 所有JSON/MD报告（cp）
├── memory/                    # MEMORY.md + USER.md
├── cron/                      # crontab -l 导出
├── system/                    # config.yaml, auth.json, 记忆层文件, 网关状态等
├── hermes-agent/              # 官方代码（可选，大文件跳过）
├── logs/                      # 日志摘要（tail -1000 每个log文件）
├── checkpoints/               # 所有检查点
└── traces/                    # 所有执行轨迹
```

## 执行步骤

### 1. 确认目标挂载点
```bash
ls /mnt/m/ 2>/dev/null && echo "已挂载" || echo "未挂载"
```
如果未挂载，先挂载：
```bash
sudo mount -t drvfs M: /mnt/m
```

### 2. 创建目录结构
```bash
DEST="/mnt/m/Hermes"
mkdir -p "$DEST"/{core,skills,scripts,agents_company,evolution_v3,production_loop,orchestrate,state,reports,logs,checkpoints,traces,memory,cron,system}
```

### 3. 核心文件（单文件cp）
```bash
for f in SOUL.md AGENTS.md CLAUDE.md .cursorrules MEMORY.md USER.md; do
    [ -f "$HERMES/$f" ] && cp -v "$HERMES/$f" "$DEST/core/"
done
```

### 4. 大目录（tar流式，保持权限和结构）
```bash
cd "$HERMES"
for dir in skills scripts agents_company evolution_v3 production_loop orchestrate; do
    tar cf - "$dir/" 2>/dev/null | (cd "$DEST" && tar xf -)
done
```

### 5. 状态文件
```bash
cp "$HERMES/state/"*.json "$DEST/state/" 2>/dev/null
cp "$HERMES/state/"*.db "$DEST/state/" 2>/dev/null
```

### 6. 报告和日志
```bash
cp "$HERMES/reports/"*.json "$DEST/reports/" 2>/dev/null
for logf in "$HERMES/logs/"*.log; do
    [ -f "$logf" ] && tail -1000 "$logf" > "$DEST/logs/$(basename $logf).tail"
done
```

### 7. Cron和配置
```bash
crontab -l > "$DEST/cron/crontab_export.txt"
find "$HERMES" -maxdepth 1 \( -name "*.json" -o -name "*.yaml" -o -name "config*" \) -exec cp {} "$DEST/system/" \;
```

### 8. SHA256校验
```bash
for f in SOUL.md AGENTS.md CLAUDE.md .cursorrules MEMORY.md USER.md; do
    src_hash=$(sha256sum "$HERMES/$f" | awk '{print $1}')
    dst_hash=$(sha256sum "$DEST/core/$f" | awk '{print $1}')
    [ "$src_hash" = "$dst_hash" ] && echo "✓ $f" || echo "✗ $f"
done
```

### 9. 文件数校验
```bash
for dir in production_loop orchestrate evolution_v3; do
    sc=$(find "$HERMES/$dir" -type f 2>/dev/null | wc -l)
    dc=$(find "$DEST/$dir" -type f 2>/dev/null | wc -l)
    [ "$sc" = "$dc" ] && echo "✓ $dir: $sc" || echo "⚠ $dir: 源$sc vs 备份$dc"
done
```

## 坑

- tar流式对大目录（scripts/ 6937文件）可能较慢，耐心等待
- hermes-agent官方代码可能超大（tar超时），用 `--exclude` 跳过或单独处理
- 目标盘空间不足时，`du -sh ~/.hermes` 先估算源大小
- 如果hermes-agent目录不需要备份（官方代码可随时重装），用 `mv` 移出备份列表
- 不要直接 `cp -r ~/.hermes` 整个目录——logs/ 和 checkpoints/ 含大量小文件，tar更高效

## 验证清单

完成备份后确认：
- [ ] 核心规则文件 SHA256 一致
- [ ] 大目录文件数一致（源 vs 备份）
- [ ] state/ 包含最新的 run_state.json + loop_state.db
- [ ] reports/ 包含最新 wake_guide.json
- [ ] crontab_export.txt 非空
- [ ] reports/ 包含最新的自进化日报
