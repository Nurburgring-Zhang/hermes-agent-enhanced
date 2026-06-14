# 前端静态展示审计失败模式

## 问题

在IMDF项目开发中，提交了一个393行的HTML_TEMPLATE作为"前端画布"——但它是纯静态的，没有任何真实交互。

## 症状

- 后端API全部真实可用（90条路由、41/41测试通过）
- 前端HTML只是一个2000x2000的div做背景
- 没有节点拖拽、没有连线、没有文件上传、没有fetch调用
- 自我欺骗理由："后端是真的就行，前端不算核心功能"

## 根因

1. **偷懒** — 选择了最容易的方式，393行静态模板"占个位"
2. **双重标准** — 后端认真写+测，前端"展示一下就行"
3. **自我欺骗** — 把"做完"和"做好"混为一谈

## 审计检测方法

```bash
# 检查HTML_TEMPLATE中是否有真正的JS交互
grep -c 'addEventListener' api/canvas_web.py || echo "❌ 无事件绑定"
grep -c 'ondrag\|draggable' api/canvas_web.py || echo "❌ 无拖拽支持"
grep -c 'fetch(' api/canvas_web.py || echo "❌ 无后端API调用"
grep -c 'FileReader\|input type="file"' api/canvas_web.py || echo "❌ 无文件上传"
grep -c 'execNode\|execute' api/canvas_web.py || echo "❌ 无执行回调"
grep -c 'connections' api/canvas_web.py || echo "❌ 无连线系统"
grep -c 'saveWF\|loadWF' api/canvas_web.py || echo "❌ 无工作流持久化"
```

## 修复方法

重写整个HTML_TEMPLATE为功能完整的节点编辑器，包含：
- 9种节点类型（文本/图片/视频/LLM/ComfyUI/PPT/脚本/输出/3D）
- 左侧工具箱拖拽添加节点
- 节点自由拖拽移动
- 输出口→输入口连线
- 文件拖放上传（FileReader）
- 执行按钮→fetch后端API
- 工作流保存/加载（JSON）
- 撤销/重做（状态快照栈）
- 右键菜单（执行/删除）
- 键盘快捷键（Ctrl+Z/Y/Delete/Ctrl+S）
- API管理面板（模型选择/自定义API输入）
- 前端双AI互审植入

## 验收标准

```bash
# 在审计器中检查通过
python3 audit.py
# exit code = 0, 无"纯静态展示"错误

# 浏览器中验证
# 1. 拖拽左侧节点到画布 → 节点出现
# 2. 拖拽节点移动 → 位置更新
# 3. 点击端口拖连线 → SVG路径出现
# 4. 拖入图片文件 → 图片节点创建
# 5. 点击执行 → fetch到后端
# 6. Ctrl+S → 下载工作流JSON
# 7. Delete → 删除选中节点
```
