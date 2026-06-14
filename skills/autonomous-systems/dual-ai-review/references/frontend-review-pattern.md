# 前端画布双审植入模式

## 问题

前端HTML画布(HTML_TEMPLATE)中的JS交互不受后端双审规则约束。execNode等操作在前端执行,无法通过后端delegate_task做预审。导致:用户在浏览器里点击"执行"按钮时没有任何安全审查,47种节点都可以绕过规则直接执行。

## 解决方案:前端口预审+postReview三明治

在前端的execNode外层包裹preReview/postReview,形成三明治结构:

```
用户点击执行
  → preReview() (前端高风险检查)
    → 原execNode() (实际API调用)
  → postReview() (结果验证+连续失败检测)
```

## 前端口预审实现

```javascript
const DANGEROUS_FRONTEND_OPS = ['delete','remove','clear','format','reset','purge'];
const DANGEROUS_PATTERNS = ['rm -rf','DROP TABLE','format','shutdown','reboot'];

async function preReview(task, tool, args) {
  const riskCheck = () => {
    const argsStr = JSON.stringify(args||'').toLowerCase();
    for (const op of DANGEROUS_FRONTEND_OPS) {
      if (tool.toLowerCase().includes(op))
        return {passed:false, reason:'前端高风险操作: '+tool};
    }
    for (const pat of DANGEROUS_PATTERNS) {
      if (argsStr.includes(pat))
        return {passed:false, reason:'检测到危险模式: '+pat};
    }
    return null;
  };
  const risk = riskCheck();
  if (risk) return risk;
  return {passed:true, reason:'前端预审通过'};
}
```

## 连续3次失败检测

```javascript
let reviewLog = [];

async function postReview(task, tool, result) {
  reviewLog.push({task, tool, result, time: Date.now()});
  addLog('info', '[审核] '+tool+' 已完成');
  
  const recent = reviewLog.slice(-3);
  if (recent.length >= 3 && recent.every(r => r.result && r.result.error)) {
    addLog('er', '[审核] ⚠️ 连续3次失败,建议切换模型');
  }
}
```

## 三明治覆盖模式

```javascript
// 保存原函数
const __origExec = execNode;

// 覆盖为三明治
execNode = async function(id) {
  const review = await preReview('执行节点', 'execNode', {id, type: N[id]?.type});
  if (!review.passed) {
    addLog('er', '[审核] STOP: '+review.reason);
    return;
  }
  const result = await __origExec(id);
  await postReview('执行节点', 'execNode', result);
};
```

## 检验标准

- HTML_TEMPLATE中必须有 DANGEROUS_FRONTEND_OPS 定义
- HTML_TEMPLATE中必须有 preReview/postReview 函数
- HTML_TEMPLATE中必须有 execNode=async 的最终定义(只有1处最后的覆盖)
- 所有47种节点类型在execNode的switch中都有对应case
- 前端口预审能拦截: delete操作、rm -rf模式、连续3次失败
