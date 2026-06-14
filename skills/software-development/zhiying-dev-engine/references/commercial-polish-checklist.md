# 商用级打磨检查清单

## 触发条件
用户说"商用级深度打磨"、"磨平粗糙边缘"、"商用到细节"。

## 前端清单（每个页面逐项检查）

### 1. Loading态
- [ ] 首次加载有骨架屏（el-skeleton）或loading指示
- [ ] 按钮操作时有loading状态（防止重复点击）
- [ ] 长时间操作有进度反馈（el-progress或loading text）
- [ ] 图片/视频加载有占位或进度

### 2. 空状态
- [ ] 数据为空时有引导提示（不是空白或空表格）
- [ ] 首次使用有操作指引（拖拽区域、示例功能）
- [ ] 搜索无结果时建议其他关键词

### 3. 错误处理
- [ ] API失败时有ElMessage.error提示（不是静默失败）
- [ ] 可恢复的错误有重试按钮
- [ ] 全局有ErrorBoundary兜底

### 4. 操作反馈
- [ ] 每个用户操作（创建/删除/保存等）都有ElMessage提示
- [ ] 危险操作有确认弹窗
- [ ] 导出/下载完成有提示

### 5. 性能体验
- [ ] 大文件加载用el-progress
- [ ] 长时间操作（＞3s）允许取消
- [ ] 表格/列表分页加载

## 后端清单

### 1. 可靠性
- [ ] 所有aiohttp.ClientSession()都有timeout参数
- [ ] 数据库连接有连接池（非每次新建）
- [ ] POST请求支持幂等性Key（X-Idempotency-Key）
- [ ] 速率限制有burst支持（前N个请求不限制）

### 2. 错误响应
- [ ] 404统一返回JSON（不是FastAPI默认{"detail":"Not Found"}）
- [ ] 500错误不暴露traceback（全局exception_handler）
- [ ] 错误响应包含request_id可追踪
- [ ] 响应格式统一（success/error/data三字段Model）

### 3. API设计
- [ ] API路径统一（/api/v2/前缀）
- [ ] 分页查询都支持page/limit参数
- [ ] CORS允许自定义头（X-Session-ID, X-Idempotency-Key等）
- [ ] WebSocket来源在白名单中

### 4. 数据验证
- [ ] 所有data.get("key")都有默认值
- [ ] 输入参数有类型校验（Pydantic或手动校验）
- [ ] SQL注入防护（参数化查询，禁止拼接SQL）

## 全链路清单

- [ ] 启动后所有核心端点返回200
- [ ] 所有前端页面npm run build成功
- [ ] pytest全部通过
- [ ] 404/500页面不暴露内部信息
- [ ] 前端构建产物在dist/中可强制刷新验证

## 本会话实战示例

### 修复的粗糙点
1. InfiniteCanvas: 无loading → 添加el-skeleton骨架屏 + 空画布引导 + 导出进度圈
2. VideoEditor: 无loading → 添加导出遮罩 + 进度百分比
3. ImageEditor: 无空状态 → 添加虚线边框拖拽区 + URL输入
4. BookStudio: 无空状态 → el-empty + 骨架屏
5. DramaStudio: 已有loading → 确认达标

### 后端增强
1. aiohttp超时: 3处ClientSession()全部加timeout=30
2. 速率限制burst: RateLimiter增加burst参数（前20个不限制）
3. 幂等性Key: generate+workflow端点支持X-Idempotency-Key
4. 404统一: @app.exception_handler(404)统一JSON响应
5. CORS增强: 增加WebSocket来源 + X-Session-ID/X-Idempotency-Key头白名单
