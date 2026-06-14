# IMDF商用级全栈开发模式（2026-06-14/15实战）

## 项目结构
```
imdf/
├── api/canvas_web.py        # FastAPI后端 ~2800行 140+路由
├── engines/                  # 44个Python引擎模块
├── frontend/
│   ├── index.html            # 独立前端入口（非内联HTML_TEMPLATE）
│   ├── css/main.css          # 深色工业主题 24KB
│   └── js/
│       ├── app.js            # 应用初始化 + PAGE_RENDERERS路由
│       ├── lib/api.js        # API调用层(fetch封装)
│       └── pages/            # 16个页面JS文件
│           ├── dashboard.js      # 首页(4指标卡+8快捷按钮+最近任务)
│           ├── datasets.js       # 数据集管理(表格/搜索/分页/批量)
│           ├── annotate.js       # 标注工具(AI预标注+BBox叠加)
│           ├── canvas.js         # 工作流画布(48节点拖拽/连线/执行) 47KB
│           ├── business.js       # 任务/团队/交付/审核/统计(合并5功能)
│           ├── pipeline.js       # 44算子管线(6类展示/搜索/执行)
│           ├── data-browser-grid.js  # 数据浏览器(网格+表格视图)
│           ├── lifecycle-pipeline.js # 全生命周期流水线
│           ├── personal-workspace.js  # 个人工作台
│           ├── template-pipeline.js   # 模板化流水线
│           ├── media-production.js    # 图片/视频生产
│           ├── llm-training-pipeline.js # LLM训练管线
│           ├── zhiying.js         # 智影数据工厂入口
│           ├── image-editor.js    # 图片标注工具(CVAT对标) 48KB
│           ├── eval-review.js     # 评测闭环+AI辅助审核 32KB
│           └── data-collection.js # 数据采集+备份+导入 34KB
```

## 关键架构决策

1. **前端独立于Python** — 不再用内联HTML_TEMPLATE(r"""...""")。改为独立文件，FastAPI通过StaticFiles挂载/css和/js。

2. **PAGE_RENDERERS动态查找** — navigate()用window[rendererName]而非缓存字典，解决后续加载JS覆盖全局函数的问题。

3. **导航页直接映射JS文件** — 21个导航菜单项，16个JS页面文件（busines.js合并5功能，dashboard/annotate/datasets各自独立）

4. **子Agent并行开发** — 3个Phase并行用3个子Agent各自写独立JS文件，最后统一注册。每Phase不互相依赖。注册到index.html/nav/app.js时小心冲突。

## 验证模式

### 全链路商用级验收（25/25通过）
```bash
Phase1(基础设施): Web/Health/认证/限流/审计/静态文件 → 6/6
Phase2(核心API): 数据集/AI预标注/DAG/图片/视频/采集/备份/OSS → 8/8
Phase3(前端页面): dashboard~review 8个页面导航+JS → 8/8
Phase4(高级功能): 图片标注/评测审核/44算子/智影入口 → 4/4
```

### 快速验证命令
```bash
# 所有JS文件可访问性
for js in $(ls frontend/js/pages/*.js); do
  curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8765/js/pages/$(basename $js)"
done

# 导航-Renderer一致性
diff <(grep -oP 'data-page="([^"]+)"' frontend/index.html | cut -d'"' -f2 | sort) \
     <(grep -oP "'[^']+': render" frontend/js/app.js | cut -d"'" -f2 | sort)
```

## 深磨模式

1. **AI视频生成** — DeepSeek生成故事板JSON→Pillow渲染帧→ffmpeg合成(zoompan+drawtext+fade) → 2-3MB MP4
2. **图片编辑器** — Canvas渲染 + FileReader本地加载 + API文件浏览器 + 5种标注工具
3. **数据采集** — 新engines/data_collection_engine.py(440行) + 15条路由全部对接 + curl验证

## 常见陷阱

- **HTML_TEMPLATE不可用** — 直接迁移到独立前端，不要尝试修复内联字符串
- **子Agent文件命名** — 子Agent可能用llm-training-pipeline.js但路由注册用llm-training，检查一致性
- **端口残留** — pkill -f "python3 api/canvas_web"杀干净再启动
- **renderPlaceholder占位** — 所有占位函数必须被真实函数覆盖，用window[name]动态查找
- **JS语法** — 对象字面量内不能用//注释（必须/* */），花括号必须配对