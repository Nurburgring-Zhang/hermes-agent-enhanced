# IMDF独立前端审计要点

## 前端独立化验证

审计FastAPI项目的前端时，确认以下事项：

### 1. 前端提供方式
- [ ] 内联HTML_TEMPLATE（Python `r"""..."""` 字符串）
- [ ] 独立前端文件（frontend/ + StaticFiles）
- [ ] 两者都有（根路由返回独立HTML，`/canvas`备选返回内联）

### 2. 内联HTML的JS语法检查
```bash
curl -s http://host:port/ | python3 -c "
import sys
h = sys.stdin.read()
s = h.find('<script>')
e = h.find('</script>')
js = h[s:e]
compile(js, 'test', 'exec')
print('JS语法正确')
"
```

### 3. 前端函数存在性
```javascript
typeof switchTab !== 'undefined'
typeof execNode !== 'undefined'
typeof navigate !== 'undefined'
```

### 4. 独立前端文件完整性
```
frontend/
├── index.html          # 主入口
├── css/main.css        # 深色主题
└── js/
    ├── lib/api.js      # API封装
    ├── pages/          # 每个页面独立JS
    └── app.js          # 导航路由
```

## 子Agent注入破坏检测

### 检查清单
1. **括号匹配**: JS中`{`和`}`数量是否相等
2. **注释位置**: `//`是否出现在JS对象字面量内（应用`/* */`）
3. **函数定义覆盖**: 同一函数名是否被定义多次
4. **模板字符串**: 反引号数量是否为偶数
5. **HTML标签闭合**: `<div>`和`</div>`数量是否匹配

### 典型破坏模式
- 子Agent的sed命令在Python文件行号修改 → 破坏了HTML字符串内的花括号平衡
- 多个子Agent先后注入 → 前一个注入的`function switchTab`被后一个覆盖
- JS对象字面量内的`// 注释` → 浏览器解析为无效字面量，整个script块跳过
