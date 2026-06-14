# Female Template Library Guide (女性模板库指南)

Generated 2026-05-20 during the 100K prompt generation campaign.

## File Locations

All files in: `D:\Hermes\1000000提示词\高质量模板\` (WSL: `/mnt/d/Hermes/1000000提示词/高质量模板/`)

| File | Content | Count | Format |
|------|---------|-------|--------|
| 15_女性风格库.txt | Visual style descriptions (流行风格/经典艺术/摄影风格) | 2000 | 100-150字 each |
| 16_女性穿搭库.txt | Outfit combinations (发+妆+上衣+下装+鞋+配饰) | 2000 | 100-150字 each |
| 17_女性姿势库.txt | Pose/scene descriptions (时尚生活场景) | 2000 | 100-150字 each |
| 18_摄影风格库.txt | Photography style descriptions (大师风格/社交媒体趋势) | 59 | 100-150字 each (quality-focused) |

## Format Rules

**CRITICAL: Pure content only, no formatting artifacts**
- No row numbers (`001|`, `002|`) — user explicitly rejected these
- No style labels (`（性感魅惑10条）`, `---`) — user explicitly rejected these
- No headers or titles in the data rows
- Each line is standalone readable content
- 100-150 characters per line (enforced by wc -m)

## Content Quality

### Style库 (15_女性风格库.txt)
Describes visual styles from three categories:
1. **生活美学**: 极简白色/日系胶片/韩系奶油/法式慵懒/北欧冷淡/美式复古/新中式/森系/赛博霓虹/地中海/波西米亚/圣诞暖冬/海滩度假/咖啡馆文艺/天台日落
2. **经典艺术**: 吉卜力治愈/新海诚通透/王家卫港风/莫奈光斑/梵高厚涂/穆夏藤蔓/克里姆特金箔/蒙克扭曲/马蒂斯色彩/霍珀孤独/怀斯忧郁/弗里达超现实
3. **潮流趋势**: 多巴胺配色/美拉德色系/格雷系灰调/Y2K千禧/Barbiecore芭比/Cottagecore田园/废土/静奢/老钱/芭蕾核

Each entry: `{风格名}风格，{光影/色彩/材质特征}。整体呈现出...`

### 穿搭库 (16_女性穿搭库.txt)
Each entry covers: 发型+妆容+上衣+下装+鞋+配饰+风格标签
Style rotation: 韩系温柔/法式复古/美式街头/日系清新/新中式/欧美性感/酷飒御姐/甜酷/静奢/Y2K/芭蕾核/多巴胺/美拉德/格雷系/老钱/废土/海边度假/运动休闲/都市通勤/Cottagecore/Barbiecore/工装机能/南法田园/赛博街头/千禧女团

### 姿势库 (17_女性姿势库.txt)
Each entry: body pose + head angle + eye direction + hand details + leg position + atmosphere
Scenes: 咖啡馆/地铁/天台/超市/试衣间/健身房/书店/画展/花店/厨房/阳台/公园/夜市/音乐会/泳池/海边/公交站/便利店/唱片行/滑板场/美术馆/机场/摩天轮/老街/古董店/天台花园/雨天/雪中/樱花/枫叶/天文馆/滑雪场/海洋馆/宠物咖啡馆/古着店/甜品店/陶艺工作室/露天音乐会

## Generation Method

Libraries were built using:
1. `delegate_task` with 3 parallel subagents
2. Each subagent used Python scripts to generate 50 items per batch
3. Repeated deployments until target count reached
4. Quality check after each batch: word count distribution, duplicate detection, format validation
