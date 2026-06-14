# PersistentManager 模式 — SQLite持久化基类（2026-06-10）

## 用途
任何需要重启后数据不丢失的Manager类，继承 `PersistentManager` 即可自动获得SQLite存储能力。

## 基础模式

```python
from core.persistent_base import PersistentManager

class MyManager(PersistentManager):
    _db_table = "my_objects"                       # 表名
    _db_key_field = "id"                            # 主键字段（默认为"id"，非标准必须覆盖）
    _db_fields = ["id","name","type","data","tags"]  # 所有列（TEXT类型）

    def __init__(self):
        self._objects: Dict[str, MyObject] = {}     # 内存缓存
        super().__init__()                           # 创建表
        self._load_from_db()                         # 加载已有数据

    def _load_from_db(self):
        for row in self._load_all():
            obj = MyObject(**row)                    # 重建对象
            self._objects[obj.id] = obj
```

## 关键约定

| 约定 | 说明 |
|------|------|
| `_save(key, data_dict)` | 写入/更新一条记录。data_dict的value如果是dict/list自动JSON序列化 |
| `_load_all()` | 加载全部记录，返回list[dict]。JSON字段自动反序列化 |
| `_load_one(key)` | 按主键查询单条 |
| `_delete(key)` | 按主键删除 |
| 非主键字段 | 自动JSON序列化，list/dict/str/int/float全支持 |
| 主键字段 | 以纯文本存储（不做JSON编码），确保WHERE条件准确匹配 |

## 已知陷阱

### 1. `_db_key_field` 必须正确
默认值为 `"id"`。如果主键字段名不同（如 `StatsManager` 用 `user_id`），必须在子类中覆盖：
```python
class StatsManager(PersistentManager):
    _db_key_field = "user_id"  # 务必覆盖！
```

### 2. 每个Manager有自己的DB文件
DB文件名 = `ClassName.db`，存放在 `backend/data/` 目录。可通过设置环境变量 `DATA_DIR` 改变位置。

### 3. 线程安全
`_save`/`_load_all`/`_delete` 内部使用 `threading.Lock` 保护。但 `create_version` 等复合操作需要在业务层额外加锁（见data_manager的`_version_lock`）。

### 4. 迁移注意事项
新增字段时只需在 `_db_fields` 列表中追加即可，SQLite自动兼容旧数据。
