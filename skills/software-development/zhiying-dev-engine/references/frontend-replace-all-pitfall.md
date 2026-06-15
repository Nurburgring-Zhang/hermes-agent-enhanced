# Frontend replace_all 破坏模式（2026-06-16实战）

## 灾难触发条件
在HTML文件中使用 `patch(replace_all=true)` 时，如果 old_string 在文件中出现多次（如 `<script src="/js/pages/drama-studio.js"></script>\n<script src="/js/app.js"></script>`），replace_all 会把每一处都替换，包括已经被前一次替换污染的行。

## 实际灾难
```html
<!-- 原始 -->
<script src="/js/pages/drama-studio.js"></script>
<script src="/js/app.js"></script>

<!-- replace_all 后 -->
<script src="/js/pages/drama-studio.js"></script>
<script src="/js/pages/data-viewer.js"></script>
<script src="/js/app.js"></script>"></script>
<script src="/js/pages/data-viewer.js"></script>
<script src="/js/app.js"></script>pt>
<script src="/js/pages/data-viewer.js"></script>
<script src="/js/app.js"></script>ipt>
...
```

每次替换叠加前一次污染，产生指数级增长的垃圾行（6次出现 → 18次替换 → 文件从正常变成满屏 `></` 乱码）。

## 修复方法
```python
# 用Python精确重写script区域
with open("index.html", "r") as f:
    content = f.read()

# 找到正常HTML和登录检查之间的位置
marker = '<!-- 登录状态检查'  # 或用其他唯一标记
idx = content.find(marker)

# 用已知正确的script列表替换中间区域
correct_scripts = """<script src="/js/lib/api.js"></script>
<script src="/js/pages/dashboard.js"></script>
...
<script src="/js/app.js"></script>"""

new_content = content[:script_start] + correct_scripts + content[auth_idx:]

with open("index.html", "w") as f:
    f.write(new_content)
```

## 防止措施
1. **禁止对HTML文件使用replace_all=true** — replace_all只对简单文本配置安全
2. 如果必须用 patch 修改HTML中的script标签，确保 old_string 包含足够的唯一上下文
3. 修改后的第一件事：检查文件尾部是否有多余的 `>` `</` 残片
4. 保存一份 clean-slate.html 作为恢复基线
