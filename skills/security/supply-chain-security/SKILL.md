---
name: supply-chain-security
description: 供应链攻击防护 — pip/npm包来源验证、新鲜度检查、允许列表、依赖锁审计。基于mistralai PyPI投毒事件(2.4.6版本含后门)和其他供应链攻击模式总结的防御规则。
---

# 供应链攻击防护

## 威胁模型
| 攻击类型 | 示例 | 检测方法 |
|---------|------|---------|
| PyPI typosquatting | mistralai→mistral | 包名校验 |
| 版本号投毒 | 官方未发布的版本号 | 版本新鲜度检查 |
| 依赖链污染 | 间接依赖注入 | 锁文件审计 |
| 编译期后门 | setup.py执行恶意代码 | 沙箱安装 |

## 已知高危包版本
| 包名 | 恶意版本 | 风险 | 状态 |
|------|---------|------|------|
| mistralai | 2.4.6 | 后门代码,token窃取,rm -rf | 已记录 |
| @mistralai/mcp-server | 0.0.1-0.0.4 | cryptominer | 已记录 |

## 防护规则
1. **版本验证**: 安装前检查版本号是否在已知恶意列表中
2. **来源验证**: 只从官方源(PyPI/npm官方)安装
3. **新鲜度检查**: 超90天未更新的依赖标记为"需审计"
4. **依赖锁**: requirements.txt/pip freeze 定期审计
5. **最小安装**: --no-deps 减少间接依赖中毒风险

## 检查命令
```bash
# 检查已知恶意包
pip show mistralai 2>/dev/null | grep -q "2.4.6" && echo "❌ 发现恶意版本!"

# 扫描所有安装包
pip list --format=columns
```
