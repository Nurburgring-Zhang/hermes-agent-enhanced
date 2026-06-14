#!/bin/bash
# 双AI互审启动检查 — 每次Hermes启动时自动执行
echo "🔍 [双审] 启动完整性检查..."

# 检查SOUL.md
if grep -q "双AI互审" ~/.hermes/SOUL.md 2>/dev/null; then
    echo "  ✅ SOUL.md: 规则完整"
else
    echo "  ⚠️ SOUL.md: 规则缺失"
fi

# 检查AGENTS.md
if grep -q "规则8" ~/.hermes/AGENTS.md 2>/dev/null; then
    echo "  ✅ AGENTS.md: 规则8存在"
else
    echo "  ⚠️ AGENTS.md: 规则8缺失"
fi

# 检查config
if grep -q "dual_ai_review" ~/.hermes/config.yaml 2>/dev/null; then
    echo "  ✅ config.yaml: 配置存在"
else
    echo "  ⚠️ config.yaml: 配置缺失"
fi

# 检查skill
if [ -f ~/.hermes/skills/autonomous-systems/dual-ai-review/SKILL.md ]; then
    echo "  ✅ dual-ai-review skill: 就绪"
else
    echo "  ⚠️ dual-ai-review skill: 缺失"
fi

echo "🔍 [双审] 检查完成"
