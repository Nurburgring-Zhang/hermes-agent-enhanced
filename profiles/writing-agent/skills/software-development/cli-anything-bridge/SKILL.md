---
name: cli-anything-bridge
description: "CLI-Anything桥架 — 让Hermes操控40+专业软件(GIMP/Blender/LibreOffice等)，把任意软件变成AI原生CLI工具"
version: 1.0.0
tags: ["cli", "software-control", "gimp", "blender", "automation"]
trigger: 用户要求操控专业软件(如"用Blender渲染/用GIMP编辑/处理视频")
---

# CLI-Anything 桥架

基于 CLI-Anything 项目 (github.com/HKUDS/CLI-Anything) 的架构，为Hermes提供操控专业软件的能力。

## 架构

```
用户请求 "帮我把这张图在GIMP里调色"
    │
    ▼
Hermes Agent → cli-anything-bridge skill
    │
    ├── [识别软件] → 判断目标软件(GIMP/Blender/LibreOffice等)
    ├── [加载模板] → 加载对应软件的CLI命令模板
    ├── [构建命令] → 自然语言→结构化CLI命令
    ├── [执行] → terminal() 调用软件CLI
    └── [验证] → 检查输出/生成结果
```

## 已映射的软件CLI命令

### 1. 图像编辑 (GIMP)
```bash
# 安装: sudo apt install gimp
gimp -i -b '(my-function "arg1" "arg2")' -b '(gimp-quit 0)'
# 批处理模式：-i 无界面，-b 执行Script-Fu

# 模板: 调整图像大小
gimp -i -b '(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE "input.png" "input.png")))
                  (drawable (car (gimp-image-get-active-layer image))))
             (gimp-image-scale image 1920 1080)
             (gimp-file-save RUN-NONINTERACTIVE image drawable "output.png" "output.png")
             (gimp-image-delete image))' -b '(gimp-quit 0)'
```

### 2. 3D建模 (Blender)
```bash
# 安装: sudo apt install blender
blender -b -P script.py
# -b 后台模式，-P 执行Python脚本

# 模板: 渲染场景
blender -b project.blend -o //render/frame_ -f 1
# 输出到 //render/frame_0001.png

# 运行Python脚本
blender -b -P /dev/stdin << 'EOF'
import bpy
# 操作场景
bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
EOF
```

### 3. 矢量图形 (Inkscape)
```bash
# 安装: sudo apt install inkscape
inkscape --batch-process input.svg --export-type=png --export-filename=output.png
inkscape --batch-process input.svg --actions="select-all;object-group;export-filename:output.svg;export-do"
```

### 4. 音频编辑 (Audacity)
```bash
# 安装: sudo apt install audacity
# Audacity通过pipe控制
echo "Select: Start=0 End=10" | audacity -pipe
```

### 5. 办公套件 (LibreOffice)
```bash
# 转换格式
libreoffice --headless --convert-to pdf input.docx
libreoffice --headless --convert-to pptx input.pptx
# 宏执行
libreoffice --headless "macro:///Standard.Module1.MyMacro"
```

### 6. 流程图 (Draw.io)
```bash
# Draw.io CLI
draw.io --export --format png --width 1920 input.drawio
```

### 7. FFmpeg (音视频处理)
```bash
# 剪辑
ffmpeg -i input.mp4 -ss 00:00:10 -t 00:00:30 -c copy output.mp4
# 转换格式
ffmpeg -i input.mov -vcodec libx264 -crf 23 output.mp4
# 提取音频
ffmpeg -i input.mp4 -q:a 0 -map a output.mp3
```

## 有状态REPL模式

对于需要多步操作的软件，使用有状态会话：

```bash
# 启动REPL
blender -b -P repl.py  # 在后台启动

# 通过命名管道发送命令(两步完成)
echo "bpy.ops.mesh.primitive_cube_add(size=2)" > /tmp/blender_pipe
echo "bpy.ops.render.render(write_still=True)" > /tmp/blender_pipe
```

## JSON结构化输出

所有命令尽可能加--json参数或解析通用输出：

```bash
# 解析blender场景信息
blender -b scene.blend -P /dev/stdin << 'EOF' 2>&1 | python3 -c "
import json,sys; data={'objects':[]}
for line in sys.stdin:
    if 'OB' in line: data['objects'].append(line.strip())
print(json.dumps(data))
"
```

## 触发条件

当用户请求包含以下关键词时自动触发此skill：
- "用GIMP/Photoshop/图像编辑/调色/修图"
- "用Blender/3D建模/渲染/动画"
- "用Inkscape/矢量/Logo设计"
- "用Audacity/音频编辑/录音/降噪"
- "用OBS/直播/录屏"
- "用LibreOffice/Office/文档转换/PDF"
- "用Draw.io/流程图/架构图"
- "剪辑视频/转码/ffmpeg/提取音频"
- "批量处理/转换格式"

## 软件安装检测

首次调用时自动检测软件是否安装：

```bash
command -v gimp || echo "GIMP未安装，请先: sudo apt install gimp"
command -v blender || echo "Blender未安装，请先: sudo snap install blender --classic"
```

## 注意事项
1. 所有软件必须在系统已安装才能使用
2. 后台模式(-b/--headless)不需要显示界面
3. 批量操作用循环，单文件操作用直接命令
4. Blender Python API比CLI参数更灵活
5. GIMP Script-Fu语法特殊，推荐用Python-fu替代
6. 复杂操作建议先生成脚本再执行
7. CLI-Hub (clianything.cc) 可获取社区预制的CLI包

## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
