# 多项目迁移实战记录（2026-06-08~10）

## 源项目清单

| 项目 | 原始大小 | 原始文件 | 迁移后位置 | 迁移方法 |
|------|---------|---------|-----------|---------|
| penguin-canvas v2.1.4 | 187MB | 421 | 47种节点+10后端模块 | 逐文件分析→Python重写→物理迁移 |
| garden-skills (7K★) | 35MB | 557 | templates/garden/ (231文件) | 全量cp |
| frontend-slides (20.5K★) | 4.5MB | 193 | templates/frontend-slides/ (152文件) | 全量cp+改名 |
| html-video (2.4K★) | 320KB | 10 | vendor/html-video/ | cp packages+docs |
| hyperframes (9.6K★) | 7.8MB | 5 | vendor/hyperframes/ | cp 核心包 |
| crawl4ai (67K★) | 38MB | 909 | vendor/crawl4ai/ (90文件) | cp Python核心模块 |

## 迁移结果

目标项目: /mnt/d/Hermes/infinite-multimodal-data-foundry/
迁移前: 1.1MB, 36文件, 依赖外部vendor
迁移后: 85MB, 794文件, 完全独立

## 教训

1. 最容易被骂的坑: 只做逻辑复刻,不做物理文件迁移
   用户发现项目从274M变成1.1M时会瞬间暴怒
2. 验证独立性方法: 删掉源项目目录后目标项目能完整运行
3. 改名策略: 加imdf_前缀,改PascalCase为snake_case
4. 跨平台: 创建config/platform_config.py避免硬编码路径
