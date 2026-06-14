# Pipeline Repair: IsolationTask sop/tools TypeError

## Failure Mode

production_chain created IsolationTask with `sop=dict` and `tools=list` keyword arguments,
but IsolationTask was a @dataclass with no such fields. Python raised:

```
TypeError: IsolationTask.__init__() got an unexpected keyword argument 'sop'
```

## Root Cause

multi_agent_engine.py and production_chain_v2.py were modified independently.
multi_agent_engine.py defined IsolationTask; production_chain_v2.py called it with
fields the dataclass didn't declare.

## Repair

1. Add `sop: dict = None` and `tools: list = None` to IsolationTask dataclass
2. Make get_agent_toolsets() check task.tools first when present
3. Add quality gate: collect per-phase success count, ≥4/6 → delivered

## Verification

```python
from multi_agent_engine import IsolationTask
t = IsolationTask(task_id='t', agent_id='a', agent_name='n',
                  sop={'steps':['a','b']}, tools=['file'])
assert t.sop == {'steps':['a','b']}
assert t.tools == ['file']
```

## Prevention

- After any @dataclass field change, grep all callers before committing
- Add a smoke-test constructor call in the pipeline entry point
