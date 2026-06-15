# 项目代码清理协议

## 触发信号
用户要求"把无用的都删掉"——删除冗余报告/测试文件/启动脚本/空目录。

## 清理清单

### 1. 根目录报告文档
删除所有审计/交付/完成/计划报告，保留README.md和CHANGELOG.md。

### 2. 冗余启动脚本
保留1个start.sh，删除所有.bat/.ps1/重复的.sh。

### 3. 空目录
```bash
find . -type d -empty -not -path '*node_modules*' -not -path '*.git*' | xargs rmdir
```

### 4. 测试文件
移到test/目录或删除（视项目需求）。

### 5. 旧名称全局替换
```bash
# 重命名目录
mv .minimax .factory
mv minimax-docx factory-docx
# 重命名文件
find . -name "*minimax*" | while read f; do mv "$f" "$(echo $f | sed 's/minimax/factory/g')"; done
# 替换内容
find . -type f -not -path "*/node_modules/*" | xargs sed -i 's/minimax/factory/g; s/MiniMax/Factory/g'
# 验证
grep -r "minimax\|MiniMax" --include="*.py" --include="*.js" -l | wc -l  # 应为0
```

## 验证命令
```bash
echo "报告文档: $(ls *.md 2>/dev/null | grep -v README | grep -v CHANGELOG | wc -l)个(应为0)"
echo "启动脚本: $(ls *.bat *.ps1 2>/dev/null | wc -l)个(应为0)"
echo "空目录: $(find . -type d -empty | wc -l)个"
```
