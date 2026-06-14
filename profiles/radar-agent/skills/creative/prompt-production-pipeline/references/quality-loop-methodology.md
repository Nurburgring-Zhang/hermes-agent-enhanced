# 质量循环方法论 — 维度库组合引擎对比测试

## 核心原则

每次建立维度库后，**必须**执行质量循环：
1. 生成组合prompt → 2. 对比参考文件 → 3. 找出缺陷 → 4. 修正库 → 5. 重复

只有通过对比测试（胜率≥80%）才能认为库的质量达标。

## 组合测试脚本

```python
# 每次版本号递增
# 最新版: /tmp/composer_v7.py
# 组合引擎基于15维度库的6层结构生成

# 运行方法
python3 /tmp/composer_v7.py
# 输出10组对比结果，每组有V7评分 vs 参考评分
```

## 质量评分函数

```python
def evaluate(prompt):
    score = 60
    if len(prompt) >= 300: score += 10
    if len(prompt) >= 450: score += 10
    if "左" in prompt or "右" in prompt: score += 10
    if "光线" in prompt or "光" in prompt: score += 5
    if "色彩" in prompt or "色调" in prompt or "色" in prompt: score += 5
    if "氛围" in prompt: score += 5
    if "女性" in prompt or "男性" in prompt or "她" in prompt or "他" in prompt: score += 5
    if "。" in prompt and prompt.count("。") >= 5: score += 5
    return min(score, 120)
```

## 参考文件路径

`D:\Hermes\1000000提示词\小红书 （10).txt` — 12735条，平均287字/条，87%左右区分，6维度齐全

## 常见缺陷及修复

| 检测到的问题 | 根因 | 修复方法 |
|------------|------|---------|
| 场景标签为"通用" | 场景库关键词不够细或匹配不上 | 扩大场景库关键词范围 |
| 左右区分率<80% | 各库条目缺乏左右区分 | 搜索全库中"双手""双臂"，改为"左手X右手Y" |
| 穿搭和姿势矛盾 | 场景-穿搭-姿势匹配规则表缺了该场景 | 向匹配规则表添加该场景的合法组合 |
| 有比喻词命中 | 某库条目未清理 | 搜索全库：仿佛/犹如/就像/好似/宛如/如同 |
| 长度不足(<250字) | 组合引擎拼接不完整 | 增加第3-4层描述（配饰/材质/动态） |
| V7评分低于参考 | 生成prompt维度不完整 | 查看具体缺失哪个维度并补充对应库 |
