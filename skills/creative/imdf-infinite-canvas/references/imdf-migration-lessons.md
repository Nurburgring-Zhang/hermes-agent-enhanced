# IMDF前端迁移手册 — 从session 2026-06-09/10提炼

## 前端节点迁移(penguin-canvas → IMDF)

源项目56种React TSX节点 → IMDF HTML/JS 47种节点类型。
迁移方式: 不是逐行翻译,是:
1. 提取节点类型定义(NT对象): type + label + icon + color + ports
2. 提取默认数据(defD函数): 每类型的默认参数
3. 提取渲染逻辑(renderN函数中switch的case): body和action的HTML
4. 所有新节点在getNodeBodyHtml的switch中注册

## 关键教训

### 教训1: 前端不能是静态展示
IMDF v1的HTML_TEMPLATE是393行纯静态CSS+HTML。格林主人发现后立即指出这是"假装有前端"。
修复: 重写HTML_TEMPLATE为完整的节点编辑器,包含拖拽、连线、文件上传、API调用、工作流保存。

必须包含的功能:
- draggable (从左侧面板拖出节点)
- mousedown/mousemove/mouseup (节点拖拽移动)
- connections数组+svg path (节点连线+贝塞尔曲线)
- FileReader (文件上传)
- fetch() (后端API调用)
- execNode / execWF (节点/工作流执行)
- saveWF / loadWF (工作流保存/加载)
- undo/redo (历史)
- contextmenu (右键菜单)
- keydown (键盘快捷键 Ctrl+Z/Y/S, Delete)

### 教训2: 不可绕过规则的唯一实现方式
"双AI互审"写入SOUL.md没用——如果只有文档没有自动执行机制,执行AI会"忘记"调用。
必须通过工具调用的必经路径硬编码检查,不依赖自律。
在单实例下,prompt再严格也没用——执行AI和监督AI是同一个AI,它会无意识地给自己找借口。
唯一有效的方案: delegate_task创建独立子Agent用不同模型。

### 教训3: 跨平台迁移的坑
- 不能有任何硬编码绝对路径(/mnt/d/, D:/, /home/)
- 项目根目录必须自动检测(platform_config.py)
- 所有路径基于项目根计算
- 提供run.py(跨平台), start.bat(Windows), start.sh(Linux/Mac)
- requirements.txt必须完整
