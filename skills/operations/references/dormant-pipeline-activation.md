# 休眠管线激活方法论

## 适用场景

发现有代码/配置/脚本存在的自动化管线没有实际被调度运行时。

## 激活流程

### Step 1: 验证引擎代码可加载

```bash
# 确认import没问题
python3 -c "import sys; sys.path.insert(0, '/path/to/engine'); import engine_module; print('✅ engine loaded')"
```

### Step 2: 检查是否有历史运行数据

```bash
# 查看DB
sqlite3 /path/to/data.sqlite "SELECT COUNT(*) FROM records"
# 查看日志文件
ls -la logs/*.log
tail -20 logs/engine.log
```

### Step 3: 确认脚本可在命令行执行

```bash
python3 /path/to/script.py 2>&1 | head -20
# 期望: 正常输出，无ImportError
```

### Step 4: 添加cron调度

```bash
(crontab -l 2>/dev/null; echo "0 6 * * * cd /home/administrator/.hermes && python3 scripts/pipeline.py >> logs/pipeline.log 2>&1") | crontab -
```

### Step 5: 添加健康检查cron

```bash
(crontab -l 2>/dev/null; echo "30 */6 * * * cd /path && python3 -c 'health check command' >> logs/health.log 2>&1") | crontab -
```

### Step 6: 验证运行

```bash
# 手动触发看是否成功
python3 scripts/pipeline.py
# 检查日志
tail -20 logs/pipeline.log
```

## 本次会话实战案例

| 管线 | 引擎存在 | 历史数据 | cron缺失 | 已修复 |
|------|---------|---------|---------|--------|
| omni_loop (8步管线) | ✅ 可加载 | ✅ 6.4MB日志, 8/8全通 | ❌ | 每天6:00 |
| production_chain_v2 (6阶段) | ✅ 可加载 | ✅ 6个产品全部delivered | ❌ | 每天8:00 |
| agents_company | ✅ 可加载 | ✅ 130员工注册 | 健康检查缺失 | 每6小时 |

## 陷阱

1. **pip install -e . 的路径问题**: 用systemd启动时WorkingDirectory必须设到源码目录，否则editable install的.pth文件找不到
2. **venv python vs 系统python**: 永远用venv的python3，不要用/usr/bin/python3
3. **crontab格式校验**: shell里不能直接用`|`管道加cron条目，写临时文件再用`crontab /tmp/file`
4. **子Agent能力限制**: delegate_task子Agent不可用父Agent的memory/network/mcp工具
