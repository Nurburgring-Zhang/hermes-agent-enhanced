# README 图片添加工作流

在 GitHub README 中添加截图/图片的标准流程。

## 完整步骤（协议）

1. **图片在本地** — 截图在 Windows 桌面/D盘，需要同步到 GitHub 仓库
2. **克隆仓库** — `git clone https://github.com/owner/repo-name.git`
3. **复制图片到仓库内** — 绝对路径的图片 GitHub 无法访问，必须放入仓库目录下
   `cp /mnt/d/截图.png repo/web/screenshot.png`
4. **修改 README** — 用 Markdown 图片语法引用
   `![描述文字](web/screenshot.png)`
5. **提交并推送** — `git add && git commit && git push`

## 典型目录约定

- `web/` — 节点类项目（ComfyUI 节点等），放截图和工作流图
- `assets/` — 通用资源
- `docs/` — 文档配图
- `screenshots/` — 明确放截图
- `images/` — 图片目录

## 图片格式

| 场景 | 推荐格式 | 备注 |
|------|---------|------|
| UI截图 | PNG | 无损，文字清晰 |
| 大量颜色/照片 | JPEG | 文件小，但压缩有损 |
| 动效演示 | GIF | 有限色，文件大 |
| 流程图/图表 | SVG | 矢量，可缩放 |

## 模型无视觉能力时的应对

当前模型（deepseek-chat）不支持图像识别。需要以下备用方案：

- **OCR**（需要安装 tesseract）: `apt install tesseract-ocr tesseract-ocr-chi-sim`
- **delegate_task**（使用有 vision 的模型分析）: 把图片路径传给子 agent 分析内容
- **文件信息推断**：通过文件名时间戳、尺寸、颜色分析（用 Pillow）推断内容类型

但这些都不如直接知道截图内容准确——最佳方案是让模型知道你截图了什么，或者去查上下文。

## 注意事项

- 推送到 main 分支前确认 README 格式正确——GitHub 渲染 Markdown 图片用相对路径
- 如果 git push 失败，检查 auth：`gh auth status` 或 GITHUB_TOKEN 是否有效
- PNG 文件在 git 中作为二进制文件处理（`git add` 不会 diff，只会全量存储）
