# Hermes 环境变量安全加载器模式
## 基于2026-06-12 Phase-0紧急止血实战

## 问题
Hermes Agent的config.yaml中存储了6处明文API密钥（NVIDIA x4, DeepSeek x2），
且config.yaml文件权限为 -rw-------，但任何通过subprocess运行的子进程可直接读取。

## 解决方案

### 1. 创建env_loader.py（3262行，3个核心函数）
- `load_env_file()` — 从.env文件读取所有变量并设置到os.environ
- `resolve_env_refs()` — 替换字符串中的`${ENV_VAR}`引用
- `resolve_config_env()` — 递归替换config dict中所有`${ENV_VAR}`引用
- `init_env()` — 模块导入时自动初始化

### 2. config.yaml密钥替换
所有`api_key: nvapi-xxxxx` → `api_key: ${NVIDIA_DEEPSEEK_API_KEY}`

### 3. 注入点（model_tools.py）
在model_tools.py的模块初始化区（Plugin discovery之前）加入：
```python
try:
    import sys
    from pathlib import Path
    _hermes_scripts = str(Path(__file__).resolve().parent.parent / 'scripts')
    if _hermes_scripts not in sys.path:
        sys.path.insert(0, _hermes_scripts)
    from env_loader import init_env
    init_env()
except Exception as e:
    logger.debug("env_loader init failed (non-fatal): %s", e)
```

### 4. .env文件权限
`chmod 600 ~/.hermes/.env`

### 5. 验证方法
```python
from env_loader import init_env, resolve_config_env
init_env()
# 检查所有provider密钥是否从环境变量解析
resolved = resolve_config_env(providers)
for name, p in resolved.items():
    if p.get('api_key') and p['api_key'].startswith(('nvapi-', 'sk-')):
        print(f"{name}: resolved ({len(p['api_key'])} chars)")
```

## 注意事项
- Hermes不支持`${ENV_VAR}`语法原生解析——必须通过env_loader注入
- `.env`文件已有DEEPSEEK_API_KEY/PUSHPLUS_TOKEN等，不要去重而是追加新变量
- 不要在终端输出中暴露密钥文本——用execute_code安全读取
- env_loader的`resolve_config_env()`在Hermes每次config加载后调用，确保provider配置中的`${}`被解析
