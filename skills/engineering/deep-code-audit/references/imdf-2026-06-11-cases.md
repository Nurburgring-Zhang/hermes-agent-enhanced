# 2026-06-11 IMDF项目审核实战记录

## 项目范围
- infinite-multimodal-data-foundry项目
- 56个核心Python文件(18,327行) + vendor/crawl4ai 80个文件(50,207行)
- 全部36个引擎模块 + 7个API复刻模块 + 2个核心agent

## 发现的39个bug分类

### 高严重性（17个）
| bug | 文件 | 发现方式 |
|-----|------|---------|
| 16个静态JSON端点(routes_extended) | routes_extended.py | 逐行读return语句 |
| 44个算子只有注册没有实现 | operators_lib.py | 读Operator.run()方法 |
| comfyui前端节点无真实API调用 | canvas_web.js | 追踪execNode case分支 |
| created_by参数未赋值给Requirement | requirement_engine.py | 比对__init__签名vs构造器调用 |
| 空技能列表筛掉所有worker | crowd_platform.py | 追踪空列表路径 |
| hmac_sha1_base64双return导致dead code | cloud_storage.py | 逐行读方法体 |
| 同步调用异步阻塞事件循环 | resource_library.py | grep run_until_complete |
| POST端点Body()绑定全部缺失 | routes_extended.py | grep Body vs grep router.post |
| 启动时asyncio.create_task无事件循环 | canvas_web.py | 实际启动测试 |

### 中严重性（13个）
| bug | 文件 | 发现方式 |
|-----|------|---------|
| cube法线全部指向一个方向 | scene_exporter.py | 读法线生成逻辑 |
| empty glTF无效primitives | scene_exporter.py | 读空mesh处理分支 |
| "x" in dir()不可靠 | video_composer.py | grep 'in dir()' |
| 正则\\n是字面反斜杠 | video_engine.py | raw string检查 |
| 相对导入..在非包上下文崩溃 | video_engine.py | 导入测试 |
| 字符串版本排序v1<v10<v2 | dataset_manager.py | 排序逻辑审计 |
| parquet路径.replace替换错 | dataset_manager.py | 路径处理审计 |
| steps完整检查缺失 | zhiying_dev_engine.py | 状态机逻辑审计 |
| Docker缺Pillow/python-multipart | Dockerfile | 依赖清单审计 |
| NANOBOT协议头缺失 | nanobot_adapter.py | 环境变量处理 |
| 自定义姿势库从未加载 | data_3d.py | __init__调用链 |
| base64图片src被清空 | imdf_utils.py | 正则替换审计 |
| Content-Disposition大小写 | imdf_async_crawler_strategy.py | 字符串比较审计 |

### 低严重性（9个）
签名不匹配、重复case、contains大小写、COVER样式、冗余pwd_context、dead code、查找函数约定缺失、闭包lambda延迟绑定、contains大小写

## vendor/crawl4ai审核结果
- imdf_utils.py (3,734行): 2个dead code函数(已删除) + 1个base64清空bug(已修复) + 1个异常处理
- imdf_extraction_strategy.py (2,815行): 1个cpu分支dead code(已删除)
- imdf_async_crawler_strategy.py (2,795行): 1个Content-Disposition大小写bug(已修复)
- imdf_adaptive_crawler.py (1,922行): 1个同步调用异步bug(已修复)
- imdf_browser_manager.py (2,092行): 1个闭包lambda延迟绑定bug(已修复)
- imdf_async_configs.py (2,343行): 无bug

## 为什么之前的审核没发现
1. 审核是"读代码"不是"跑代码" — 17个静态JSON端点一眼就能看到但没人发现
2. 没有逐行追踪跨函数参数链路 — 参数签名不匹配需要逐行比对两个函数
3. 没有实际启动HTTP服务测试 — 启动时序问题只有在启动后才能发现
4. 没有在运行时检测前端case — 前端case分支调用链需要在浏览器点按钮验证
5. 认为"引擎可以导入就说明功能正常" — 导入成功不等于被HTTP端点调用
