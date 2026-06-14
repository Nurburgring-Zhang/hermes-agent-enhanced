# 全栈审计实战日志 (2026-06-08)

## 项目: NanoBot Factory

- 后台 ~123K 行 Python (60源文件), 前端 ~61K 行 TS/TSX (146源文件)
- 审计发现 104 问题: P0:3, P1:5, P2:56, P3:40
- 最终结果: 7/7修复项完成, 237/237测试通过

## 关键发现

### 类型序列化陷阱
- `np.float32/np.float64` 不是 JSON 可序列化 → 用 `float()`
- `PosixPath` 对象 → 用 `str()`
- numpy 类型在 dataclass 字段要显式转为标准类型

### 全局单例模式
质量引擎用 `get_quality_engine()` 返回单例。第一次调 `skip_model_init=True` 跳过了初始化，后续调 `skip_model_init=False`也不会重试。修复：加 `force_reinit` 参数。

### bare except 修复策略
38处 bare except，修复模式：
- `except:` → `except Exception as e: logger.warning(...)`
- `except: pass` → `except SpecificError: ...` 至少记录日志
- storage/queue 层16处保留（存储层逻辑），其余全部修复

### TypeScript strict 模式的8个开关
| 开关 | 旧值 | 新值 |
|------|------|------|
| strict | false | true |
| noImplicitAny | false | true |
| strictNullChecks | false | true |
| strictFunctionTypes | false | true |
| strictBindCallApply | false | true |
| strictPropertyInitialization | false | true |
| noImplicitThis | false | true |
| alwaysStrict | false | true |

### 参数真实性验证6步协议
详见 `multimodal-data-production` skill 的 `references/nanobot-factory-round2-20260608.md`
