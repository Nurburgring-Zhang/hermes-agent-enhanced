# SQLite持久化层模式 — PersistentManager基类

## 动机
所有内存Dict管理的Manager服务重启后数据全丢。需要统一持久化方案。

## PersistentManager基类
位置: `core/persistent_base.py`

关键设计:
- `_db_table`, `_db_key_field`, `_db_fields` 三个类属性定义表结构
- `__init__` 自动 `_ensure_table()` (CREATE TABLE IF NOT EXISTS)
- `_save(key, dict)` → INSERT OR REPLACE, JSON序列化所有字段
- `_load_all()` → SELECT * + JSON反序列化
- `_delete(key)` → DELETE WHERE
- 线程安全: `threading.Lock` 保护所有SQLite写操作

## 继承模式

```python
from core.persistent_base import PersistentManager

class MyManager(PersistentManager):
    _db_table = "my_items"
    _db_key_field = "my_id"  # !! 如果不叫"id"必须覆盖，否则sqlite3.OperationalError
    _db_fields = ["my_id","name","json_data","created_at"]

    def __init__(self):
        super().__init__()  # 自动建表
        self._items: Dict[str, Item] = {}
        self._load_from_db()

    def _load_from_db(self):
        for row in self._load_all():
            item = Item(**row)
            self._items[item.my_id] = item

    def create(self, ...):
        item = Item(...)
        self._items[item.my_id] = item
        self._save(item.my_id, item.model_dump())

    def delete(self, my_id):
        self._items.pop(my_id, None)
        self._delete(my_id)
```

## 常见问题
1. `_db_key_field` 默认"id"——如果你的主键是`user_id`, `item_id`等必须显式覆盖
2. `_save()` 中key字段不JSON编码（保持原始字符串），非key字段用json.dumps
3. `_load_all()` 调用 json.loads 反序列化——非JSON字符串（如纯数字的字符串）会走except保留原始值
4. 必须在每个create/update/delete点都调_save/_delete，少一个就是数据丢失

## 高级陷阱

### 陷阱1: _ensure_table不在__init__中调用
如果Manager的__init__没有调用super().__init__()(或显式调用_ensure_table())，涉及新建表的操作会在运行时因为表不存在而静默失败——数据写不进去也不报错。
对策: _ensure_table 必须对所有子表调用，尤其是Manager管理多于1个实体表时。

### 陷阱2: 多表Manager的持久化孤岛
当Manager管理多个实体(如GovernanceManager管理lineage/audit_logs/backups 3个表)，每个实体必须有独立的 _save/_delete 调用点。常见遗漏: 一个实体调了_save另一个没调。
对策: 每个实体的create/update/delete点都必须显式调用其对应的持久化方法。审计时直接打开.db文件检查。

### 陷阱3: Pydantic枚举值持久化陷阱
SQLite存储枚举为字符串，但读取时Pydantic v2可能抛出serializer警告。
对策: _load_from_db 中手动类型转换: if isinstance(row.get("status"), str): row["status"] = TaskStatus(row["status"])

### 陷阱4: 持久化改造后原有构造逻辑损坏
父类__init__调用了_ensure_table和_load_from_db，可能在原有__init__逻辑之前执行。如果_load_from_db清空了内存字典，原有初始化创建的数据会被覆盖。
对策: super().__init__() 在子类初始化完成之后再调用。

## 已验证的持久化Manager (9个)
RequirementManager, TaskManager, EvalManager, StatsManager, GovernanceManager, 
AssetManager, UserManager, DataManager, WorkflowEngine

DB文件统一存储在 `backend/data/{ClassName}.db`
