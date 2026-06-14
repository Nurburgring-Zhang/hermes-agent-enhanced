# Cron ID 格式识别

## 两种格式

### 旧格式（short hex）
```
3c0084b57096
ea525a9b281d
6bc94495c0de
```
12字符 hex，由 Hermes 早期版本生成。通常对应 guardian.py 旧三模式（cycle/heal/push）的 cron 注册。

### 新格式（UUID）
```
567f1c990fc5
066d07a138a5
2b8b44314a4c
```
12-16字符 hex，稍新版本生成。包含 no_agent=true、workdir、script 等额外字段。

### UUID v4 格式
```
c661ec2d-d22e-4044-99db-7e3aa08369dd
```
标准 36字符 UUID，最新版 Hermes cron 注册器生成。

## 识别规则
- **全小写 12 字符 hex** → 旧格式（可能是旧系统残留）
- **有连字符的 36 字符 UUID** → 最新格式
- **12-16 字符无连字符** → 新版格式（但有 `no_agent` 字段的可能是最新的）

## 删除优先级
确定同功能重复时，**保留最完整的那个**（有 no_agent + workdir + script 字段的 > 无字段的）。
