# 商用级UI验收框架

## 核心思想
不依赖主观判断，用**可量化的检查清单**逐项打分。每个页面逐项过，不过关要提供具体修改方案。

## 五维评分体系

| 维度 | 权重 | 检查内容 |
|------|------|---------|
| 架构完整性 | 20% | Vite+Vue3/VueRouter/Pinia/TS/ElementPlus/代码分割 |
| 页面丰富度 | 25% | 每个页面是否有完整CRUD/筛选/排序/批量操作/弹窗 |
| UI组件多样性 | 20% | 是否覆盖table/dialog/form/tabs/progress/tag/skeleton等 |
| 交互完善度 | 20% | loading态/空状态/错误态/操作反馈/快捷键/批量导出 |
| 后端真实对接 | 15% | 是否调用真实API/有fallback机制/错误处理 |

## UI组件检查清单（Element Plus）

每个页面必须检查：

```
el-table        ✅ 表格（含v-loading/empty-text/stripe）
el-dialog      ✅ 弹窗（含确认/取消操作的二次确认）
el-form        ✅ 表单验证（el-form-item + rules）
el-tabs        ✅ 多Tab页面切换
el-tag         ✅ 状态标签（着色语义化：success/warning/info/danger）
el-progress    ✅ 进度条/评分展示
el-card        ✅ 模块卡片化
el-message     ✅ 操作反馈（ElMessage.success/error/warning）
el-select      ✅ 下拉选择
el-input       ✅ 输入框（含v-model）
el-button      ✅ 按钮（含loading态、type语义化）
```

## 全局UX增强清单

```
GlobalSearch    搜索组件（el-autocomplete + 关键词路由）
ErrorBoundary   错误边界（onErrorCaptured + 恢复按钮）
TableSkeleton   骨架屏（el-skeleton + animated）
useTable        组合函数（批量选择 + 导出CSV）
useShortcuts    快捷键系统（Ctrl+S/Z/Shift+E + Delete/D）
```

## 商用级差距快速判定

```bash
# 单页面分析
wc -l <page>.vue
grep -c 'el-table\|el-dialog\|el-form' <page>.vue
grep -c 'api.get\|api.post\|fetch' <page>.vue
grep -c 'onMounted\|watch\|ref\|reactive' <page>.vue

# 如果 < 100 行 → 骨架页面，严重不足
# 如果 100-300 行 → 有基本功能但不完善
# 如果 300-600 行 → 达到商用级标准
# 如果 600+ 行 → 丰富交互的完整页面
```

## DAG编辑器验收标准

```
DAGCanvas.vue: 
  ✅ 无限平移(panX/panY + mousedown/drag)
  ✅ 滚轮缩放(zoom + 以鼠标位置为中心)
  ✅ SVG贝塞尔曲线连线(getEdgePath + cubic bezier)
  ✅ 端口拖拽连接(startEdge + mousemove temp path)
  ✅ 节点选中/删除/复制
  ✅ 右键上下文菜单
  ✅ 键盘快捷键(Ctrl+A全选/Delete删除/Ctrl+D复制)
  
NodePanel.vue:
  ✅ 从API加载节点(get /api/v2/nodes)
  ✅ 分类分组展示
  ✅ 搜索筛选
  ✅ 拖拽添加到画布(dragstart + drop)
  
ParamPanel.vue:
  ✅ 类型感知表单(string→Input/int→InputNumber/bool→Switch)
  ✅ JSON预览 + 复制按钮
  ✅ 空状态指引
  
Workflow.vue:
  ✅ 三栏布局(左侧面板+画布+右侧面板)
  ✅ 保存/加载(localStorage)
  ✅ 执行(POST /api/v2/workflow/execute)
  ✅ 导出JSON
  ✅ 统计栏(节点数+连线数)
```
