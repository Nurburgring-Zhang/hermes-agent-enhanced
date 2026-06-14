# addDOMWidget 节点高度动态修正技术

关键：addDOMWidget 创建的widget不自动参与节点的`this.size`布局计算。

## 唯一正确方案（2026-05-27验证通过）

**不要调this.setSize，不要算widget offset，不要找this.el。**
**唯一正确的做法：重写this.computeSize，累加所有widget高度，末尾加保底值。**

```javascript
const domWidget = this.addDOMWidget('ref_image_upload', 'customwidget', container, {
    serialize: false,
    hideOnZoom: false
})

// 1) DOM widget自己的computeSize
domWidget.computeSize = function(width) {
    return [width || 260, calcHeight()]
}

// 2) 重写节点的computeSize——手动累加所有widget的高度
//    这是唯一正确的方法
this.computeSize = function(nodeWidth) {
    const w = nodeWidth || this.size?.[0] || 280
    let totalH = 0
    if (this.widgets) {
        for (const wgt of this.widgets) {
            if (wgt.hidden) continue  // 跳过隐藏widget
            if (wgt.computeSize) {
                const sz = wgt.computeSize(w)
                totalH += (sz?.[1] || 30)
            } else {
                totalH += 30
            }
        }
    }
    // 60px保底，确保DOM widget不超出下边框
    return [Math.max(w, 280), totalH + 50 + 60]
}
```

## 绝对不要做的操作

| ❌ 操作 | 为什么被骂 |
|---------|-----------|
| 在redrawGrid里调this.setSize | 节点越删越高——删一张图加一次高度 |
| 硬编码偏移量（560px） | widget列表变化后全错 |
| this.setSize([w, h+0.1]) hack | 不稳定，有时不触发重绘 |
| 找this.el.parentNode.appendChild | this.el在ComfyUI中不存在 |
| 重写onResize来修正高度 | computeSize正确就不需要 |
| requestAnimationFrame + setSize | 多次尝试全部失败 |
| 动态算widget offset再setSize | 同样会越删越高 |

## 常见场景测试结果

| 图片数 | 预期高度 | 能否容纳DOM内容 |
|:------:|:--------:|:--------------:|
| 0张(空提示) | ~900px | 容纳按钮行+提示文字 |
| 3张 | ~1050px | 容纳1行网格+按钮 |
| 6张 | ~1140px | 容纳2行网格+按钮 |
| 9张 | ~1230px | 容纳3行网格+按钮 |
