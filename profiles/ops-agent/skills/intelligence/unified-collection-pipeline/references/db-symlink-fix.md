# intelligence.db 符号链接修复

## 问题
Hermes 系统同一路径有两个 `intelligence.db`：
- `~/.hermes/intelligence.db` — 真实数据 (约396MB)
- `~/.hermes/data/intelligence.db` — 幽灵数据库 (0字节或8KB，访问的却是旧的路径)

多次自进化检查发现 data/ 路径为空，误判为采集系统故障。

## 检查方法
```bash
ls -la ~/.hermes/data/intelligence.db
# 如果显示为 0 字节，就是幽灵数据库
ls -la ~/.hermes/intelligence.db
# 如果这个文件很大，说明数据在这里
```

## 修复方法
```bash
rm ~/.hermes/data/intelligence.db
ln -s ~/.hermes/intelligence.db ~/.hermes/data/intelligence.db
```

## 验证
```bash
ls -la ~/.hermes/data/intelligence.db  # 应显示符号链接
python3 -c "import sqlite3; import os; c=sqlite3.connect(os.path.expanduser('~/.hermes/data/intelligence.db')); print(c.execute('SELECT COUNT(*) FROM raw_intelligence').fetchone())"
```

## 预防
- 所有脚本应该使用 `config.get('db_path', 'intelligence.db')` 而不是硬编码路径
- 自进化检查脚本的路径检测需要处理符号链接情况
