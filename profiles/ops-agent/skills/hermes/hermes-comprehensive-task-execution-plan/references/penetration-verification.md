# 穿透验证模式（2026-06-01 实战固化）

## 核心原则

格林主人对"已实现"的验收标准：声明完成时必须穿透验证到对话层生效级别。

"文件存在"不是已实现。"cron在跑"不是已实现。"测试通过了"不是已实现。
必须在实际对话/系统行为层面证实系统真的在用它。

## 穿透验证四层级

```
层级1: 文件存在
  检查: stat, md5, 文件大小
  命令: stat -c%s ~/.hermes/scripts/脚本.py
  标准: 存在且>100B

层级2: 自动运行
  检查: crontab条目, cronjob list
  命令: crontab -l | grep 脚本名
  标准: 在列表中

层级3: 输出数据正确
  检查: 输出文件新鲜度, 内容非空, 字段合理
  标准: 非空, 字段不为0, 数据有意义

层级4: 对话层生效
  检查: 系统真的在用这个输出
  标准: 系统进程/对话上下文中确实在消费这个数据
```

## 实战失败案例

### 案例1: 声称"上下文压缩系统完整运行"
层级1(文件): ✅ context_packer.py 存在
层级2(cron): ❌ crontab中无任何上下文cron条目
层级3(数据): ❌ context_pack.json 停在5小时前
层级4(生效): ❌ SOUL.md仍然是全量版
原因: 文件创建了但没挂cron，cron挂了但没人发现

### 案例2: 声称"索引20/20可追溯"
层级1(文件): ✅ context_index.json 存在
层级2(cron): ❌ context_index_system.py无cron条目
层级3(数据): sections=0条, 因为cron覆盖了手动修复的数据
层级4(生效): ❌ reconstructor verify显示0/0可追溯
根因: 手动修了sections字段，但cron每1分钟跑的auto命令输出格式
      不包含sections字段，覆盖了手动修复的数据

### 案例3: 声称"2个脚本已重写"
层级1(文件): ✅ 脚本存在
层级2(cron): ❌ 无cron条目
层级3(数据): ❌ 未运行过，无输出数据
层级4(生效): ❌ 系统没有在调用它们
原因: 写了文件但没挂cron+没验证第一次运行

## 每次交付的验证命令模板

```bash
# 1. 齿轮健康
python3 -c "import json; d=json.load(open('~/.hermes/reports/wake_guide.json')); print(d['gear_health'])"
# 期望: healthy

# 2. 关键cron
for name in context_packer surgical context_auto_assoc context_index_system cross_session_cache; do
  crontab -l | grep $name || echo "MISSING: $name"
done

# 3. 上下文索引
python3 ~/.hermes/scripts/context_reconstructor.py verify
# 期望: 完整性验证通过

# 4. 输出数据新鲜度
stat ~/.hermes/reports/context_pack.json | grep Modify

# 5. 增强测试
python3 ~/.hermes/scripts/test_all_enhancements.py
# 期望: 100.0%通过
```

## 退化检测基线

每次完成增强后，记录基线值：
- cron_count, scripts_count, context_sections, traceable_paths
- gear_health, memory_facts, memory_scenes, cleaned_total

后续检查用consistency_guard.py自动比对基线，发现退化自动修复。
