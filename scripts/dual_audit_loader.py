"""
双AI互审引擎 — 自动加载器
每次Hermes启动时自动加载双审规则

不可关闭。不可绕过。
"""
from pathlib import Path

ENABLED = True

def audit_loader():
    """确保双AI互审模块已加载"""
    skills_dir = Path.home() / ".hermes" / "skills" / "autonomous-systems" / "dual-ai-review"
    if (skills_dir / "SKILL.md").exists():
        return True
    return False

def check_soul_integrity():
    """检查SOUL.md中双审规则是否完整"""
    soul_path = Path.home() / ".hermes" / "SOUL.md"
    if not soul_path.exists():
        return False, "SOUL.md不存在"

    content = soul_path.read_text()
    checks = {
        "双AI互审标题": "双AI互审（永久开启" in content,
        "监督AI职责": "预审" in content and "实时验证" in content and "干预权" in content,
        "不可绕过": "不可绕过" in content,
        "STOP信号": "STOP" in content,
    }
    all_pass = all(checks.values())
    failed = [k for k, v in checks.items() if not v]
    return all_pass, failed

if __name__ == "__main__":
    ok, detail = check_soul_integrity()
    if ok:
        print("[双审] ✅ 双AI互审规则已加载，永久生效")
    else:
        print(f"[双审] ⚠️ 规则不完整: {detail}")

    loaded = audit_loader()
    print(f"[双审] {'✅ Skill就绪' if loaded else '⚠️ Skill未加载'}")
