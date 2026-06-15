# 项目代码清理完整协议 (2026-06-16 实战)

## 触发条件
用户说"清理无用文件/报告/启动脚本/测试"时执行。

## 清理范围

### 1. 报告文档
删除根目录下所有审计/交付/完成/分析报告（audit/completion/delivery/review等）：
```bash
# 保留README.md和CHANGELOG.md
for f in *.md; do
  case "$f" in README.md|CHANGELOG.md) echo "保留: $f" ;; *) rm -f "$f" ;; esac
done
```

### 2. 冗余启动脚本
```bash
rm -f *.bat *.ps1 start_linux.sh run*.bat run*.ps1 *.patch
# 只保留 start.sh
```

### 3. 测试目录
```bash
rm -rf backend/*/tests backend/*/tests-unit
```

### 4. 空目录
```bash
find . -type d -empty -not -path '*node_modules*' -not -path '*.git*' -exec rmdir {} \;
```

### 5. 旧项目名称重命名
```bash
# 目录: .minimax → .factory
mv .minimax .factory
# 子目录: minimax-docx → factory-docx
# 子目录: minimax-pdf → factory-pdf
# DotNet项目: MiniMaxAIDocx → FactoryAIDocx
# 文件内容: sed 's/minimax/factory/g; s/MiniMax/Factory/g; s/MINIMAX/FACTORY/g'
```

### 验证
```bash
grep -r "minimax\|MiniMax\|MINIMAX" --include="*.py" --include="*.md" --include="*.json" -l . | wc -l
# 必须输出 0
```

## 清理后项目文件数
典型结果：从~3592文件减到~3459文件
