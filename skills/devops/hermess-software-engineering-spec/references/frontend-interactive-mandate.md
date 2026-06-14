# 前端交互真实实现 — 禁止静态展示

## 🔴 核心禁令
HTML_TEMPLATE不能是纯静态展示。"做完"≠"做完"——前端没有交互等于没做。

## 审计检查项（audit.py强制执行）
每次启动前检查HTML_TEMPLATE是否包含以下交互功能：

| 检查项 | 检测方法 | 不通过的后果 |
|--------|---------|-------------|
| 有JS事件绑定 | `addEventListener` 存在 | 纯静态、阻断启动 |
| 有拖拽交互 | `draggable` 或 `mousedown+mousemove` | 节点不能移动、阻断启动 |
| 有连线功能 | `connections` 数组 + `svg path` | 无连线系统 |
| 有文件上传 | `FileReader` 或 `input type="file"` | 不能传文件 |
| 调后端API | `fetch(` 存在 | 无后端通信 |
| 有执行按钮 | `execNode` 或 `execute` | 不能生产 |
| 可保存工作流 | `saveWF` 或 `JSON.stringify(nodes)` | 不能持久化 |
| 有历史操作 | `undo` 或 `history` | 不能撤销 |

## 最小可行节点编辑器清单
如果从零开始写HTML节点编辑器，最少需要的功能：
1. 侧边栏节点类型列表（可拖出到画布）
2. 画布div（容纳节点，支持鼠标平移）
3. 节点div（带header/body/ports/action）
4. 节点拖拽（mousedown+mousemove+样式更新）
5. 连线系统（点击port开始→svg path绘制→连接数据更新）
6. 文件拖放上传（FileReader读取→创建对应类型节点）
7. 执行回调（点击按钮→fetch后端API→展示结果）
8. 工作流保存/加载（JSON序列化→文件下载/上传）
9. 撤销/重做（状态快照栈）
10. 右键菜单（删除/复制）
11. 键盘快捷键（Ctrl+Z/Y/Delete/Ctrl+S）

## 经验教训（2026-06-10）
用17KB纯HTML+JS实现了完整的节点编辑器（无框架、无依赖）：
- 9种节点类型（文本/图片/视频/LLM/ComfyUI/PPT/脚本/输出/3D）
- 完整的拖拽/连线/执行/保存/加载/历史
- 前端代码放在api/canvas_web.py的HTML_TEMPLATE中
- 后端API有90条路由
