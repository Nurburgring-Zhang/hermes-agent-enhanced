---
name: data-lifecycle-management
description: 数据生命周期管理 — 源健康检测+旧数据归档+压缩存储。整合source-cleanup-tag(静默源标记), archive-old-data(cron归档每天4:00), archive-compressor(压缩实现)。
---

# Data Lifecycle Management

## 阶段1: 源健康检测
检测4天以上无数据的采集源 → 标记为已知静默 → 建议移除或归档

## 阶段2: 旧数据归档 (cron: 0 4 * * *)
将cleaned_intelligence中7天前的数据压缩到history_archive表
保留: 标题/平台/AI评分/标签

## 阶段3: 压缩存储
zlib/gzip三级压缩 + 检查点 + delta + VACUUM归档
