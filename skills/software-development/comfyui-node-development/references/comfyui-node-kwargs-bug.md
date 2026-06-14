# ComfyUI 节点 kwargs 签名 Bug

## 症状
ComfyUI执行时报错：
TypeError: xxx.get_prompt() got an unexpected keyword argument '文件夹路径'

## 根因
ComfyUI把所有widget参数作为命名关键字参数传入节点的FUNCTION方法。
方法签名为def get_prompt(self, kwargs)即位置参数的话，ComfyUI调用相当于get_prompt(文件夹路径=..., 模式选择=...)就会报错。

## 修复
改两处方法签名：
1. def get_prompt(self, kwargs): → def get_prompt(self, **kwargs):
2. def IS_CHANGED(cls, kwargs): → def IS_CHANGED(cls, **kwargs):

## 验证命令
grep -n 'def get_prompt|def IS_CHANGED' __init__.py
两行都应该是**kwargs

## 铁律
每次备份恢复代码后，第一条检查就是验证方法签名是否为**kwargs。
已犯两次，绝不再犯。
