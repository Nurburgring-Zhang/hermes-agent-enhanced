#!/usr/bin/env python3
"""
修改前自检脚本 — 遵循开发与生产工程规范
用法: python3 scripts/check_script.py scripts/要修改的文件.py
"""
import os
import re
import sys


def check_file(path: str) -> list:
    errors = []
    with open(path) as f:
        content = f.read()
        lines = content.split("\n")

    nlines = len(lines)
    if nlines > 500:
        errors.append(f"⚠️  文件过长: {nlines}行 (限制500行)")

    # 检查 docstring
    if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
        # 可能第一行是 shebang
        first_content = content.lstrip()
        if not first_content.startswith('"""') and not first_content.startswith("'''"):
            errors.append("❌ 缺少文件级 docstring")

    # 检查函数长度
    func_pattern = re.compile(r"^def\s+(\w+)\s*\(")
    current_func = None
    func_start = 0
    for i, line in enumerate(lines, 1):
        m = func_pattern.match(line)
        if m:
            if current_func and i - func_start > 60:
                errors.append(f"⚠️  函数过长: {current_func} ({i-func_start}行, 限制60行)")
            current_func = m.group(1)
            func_start = i

    # 检查硬编码密钥模式
    key_patterns = [
        r'api_key\s*=\s*["\'](?:nvapi-|sk-|ghp_)',
        r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}',
    ]
    for pat in key_patterns:
        matches = re.finditer(pat, content)
        for m in matches:
            line_no = content[:m.start()].count("\n") + 1
            errors.append(f"❌ 疑似硬编码密钥 (行{line_no})")
            break  # 每个模式只报一次

    # 检查类型注解缺失
    funcs_no_annotation = []
    for m in re.finditer(r"^def\s+(\w+)\s*\((.*?)\)\s*:", content, re.MULTILINE):
        name, params = m.group(1), m.group(2)
        if name.startswith("_"):
            continue  # 私有函数放行
        # 检查返回值注解
        line = lines[content[:m.start()].count("\n")]
        if "->" not in line and name != "__init__":
            # 检查下一行是否也是def
            funcs_no_annotation.append(name)

    if funcs_no_annotation:
        errors.append(f"⚠️  缺少返回值类型注解: {', '.join(funcs_no_annotation[:5])}")

    # 检查 try/except 覆盖 I/O
    io_patterns = [
        (r"open\(", "文件操作"),
        (r"requests\.(get|post|put)", "HTTP请求"),
        (r"sqlite3\.connect", "数据库连接"),
        (r"urllib\.request", "URL请求"),
        (r"subprocess\.", "子进程"),
    ]
    for pat, desc in io_patterns:
        count = len(re.findall(pat, content))
        if count > 0:
            # 粗略检查是否被try包围（只是提醒）
            pass  # 精确检测太复杂，留作人工检查

    return errors

def main():
    if len(sys.argv) < 2:
        print("用法: check_script.py <目标文件.py>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        sys.exit(1)

    print(f"检查: {path}")
    print("=" * 40)

    errors = check_file(path)

    if not errors:
        print("✅ 检查通过")
        sys.exit(0)
    else:
        for e in errors:
            print(f"  {e}")
        print(f"\n共 {len(errors)} 个问题")
        sys.exit(1 if any(e.startswith("❌") for e in errors) else 0)

if __name__ == "__main__":
    main()
