---
name: hyperframes-video-bridge
description: HyperFrames HTML→MP4确定性视频渲染引擎桥接。基于HeyGen开源9.6K★项目，将HTML/CSS/JS原生渲染为MP4视频。替代garden-web-video-production的"网页模拟+录屏"方案，实现像素级精确的确定性视频输出。
---

# HyperFrames Video Bridge — HTML→MP4确定性渲染

## 作用
garden-web-video-production 用"HTML模拟视频+录屏"的方式工作。
HyperFrames 直接从 HTML 渲染为 MP4 原生视频格式——确定性、像素级精确、一致输出。

## 核心差异
| 维度 | garden-web-video-production | HyperFrames |
|------|---------------------------|-------------|
| 输出方式 | 录屏 | 原生MP4渲染 |
| 一致性 | 受屏幕分辨率影响 | 确定性的同一HTML→同一输出 |
| 格式支持 | 需额外ffmpeg转换 | 直接MP4 |
| 动画支持 | CSS动画有限 | GSAP/Lottie/Three.js原生支持 |

## 工作流程
```
Step 1: 创建HTML composition
  - index.html + compositions/ + assets/
  - 支持GSAP动画、Three.js、Lottie

Step 2: 预览（可选）
  hyperframes preview

Step 3: 渲染为视频
  hyperframes render

Step 4: 与现有管线集成
  - 可用于短视频、产品演示、动画内容
  - 输出供后续剪辑/配音/合成
```

## 安装
```bash
npm install -g @heygen/hyperframes
```

## 典型用途
- 产品功能演示视频
- 技术分享动画
- 数据可视化视频
- 品牌宣传短片
- 与xindaya-translation + TTS组合为完整视频管线
