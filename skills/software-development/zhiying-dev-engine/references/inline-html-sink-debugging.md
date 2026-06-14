# 内联HTML被多子Agent注入破坏的根因链与修复模式

## 故障模式（2026-06-13/15 实战总结）

### 根因链
43833字符的HTML_TEMPLATE(r"""...""" 字符串)被多轮子Agent注入破坏：
1. 子Agent A注入监控面板代码
2. 子Agent B注入数据浏览器代码
3. 子Agent C注入运营看板代码
4. sed/patch操作Python文件行号破坏字符串内花括号匹配
5. const NT={...} 对象字面量内出现 // 注释
6. execNode被重复覆盖3次（3个子Agent各自加了一层wrap）
7. 最终 typeof switchTab === undefined — 整个script块不执行

### 修复模式
1. 花括号配对检查
2. 对象内//注释→/* */替换
3. 删除重复的execNode覆盖和孤立的}
4. 用node --check验证（有Node.js时）
5. 最终方案：放弃内联HTML，改用独立文件

### 铁律
**永远不要把前端代码内联在Python字符串中。** 改用独立文件+StaticFiles挂载。
详见 `references/standalone-frontend-migration.md`
