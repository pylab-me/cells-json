# cells-json

通用 JSON 序列化工具，提供 `orjson` 优先的高性能序列化能力，并补齐 Python 项目中常见的复杂类型处理需求。

## 🚀 核心特性

- **orjson 优先**：默认使用 `orjson` 作为主后端，优先追求吞吐量和低延迟。
- **极致性能**：通过适配器模式和类型查找缓存，性能较标准库提升 3x - 10x。
- **全量类型支持**：原生支持 `datetime`、`Decimal`、`UUID`、`Enum`、`Path`、`numpy`、`pandas`、`set`、`tuple` 等。
- **工业级异常体系**：提供统一的 `JSONEncodeError` 和 `JSONDecodeError`，兼容标准库并保留完整上下文。
- **多后端适配**：保留 `backend="json"` 显式回退能力，适合需要标准库参数语义的场景。
- **防御性设计**：内置循环引用检测（支持标记字符串或严格报错）和显式参数控制。
- **便捷工具**：提供装饰器、基类和辅助函数简化日常开发。

## 📦 安装

```bash
pip install cells-json
```

## 💡 快速开始

### 1. 核心 API 导入

你可以直接从根包导入最常用的功能：

```python
from cells.json import (
    safe_json_dumps,    # 安全序列化（推荐）
    dump, load,         # 文件流接口
    dumps, loads,       # 高性能适配器
    UniversalSerializer, # 核心转换器
    JSONEncodeError,    # 编码异常
    JSONDecodeError     # 解码异常
)
```

### 2. 通用序列化 (推荐)

`safe_json_dumps` 会自动处理常见复杂类型，并采用递归扫描以支持循环引用标记。

```python
from datetime import datetime
from cells.json import safe_json_dumps

data = {
    "time": datetime.now(),
    "tags": {"python", "json"},
    "meta": {"version": "1.0"}
}

# 支持 indent 等标准参数
json_str = safe_json_dumps(data, indent=2)
```

### 3. 高性能模式

使用 `dumps` 和 `loads` 直接走 `orjson` 主路径。该接口默认统一返回 `str` 类型。

```python
from cells.json import dumps, loads

# 默认优先使用 orjson
json_str = dumps({"key": "value"}, ensure_ascii=False)
obj = loads(json_str)
```

### 4. 标准库风格导入

如果你希望在工程里用 `cells` 统一替代标准库入口，可以直接这样写：

```python
from cells import json

payload = json.dumps({"name": "alice"}, ensure_ascii=False)
data = json.loads(payload)
```

也支持实例化适配器：

```python
from cells.json import JSONAdapter

json = JSONAdapter()
payload = json.dumps({"name": "alice"}, ensure_ascii=False)
data = json.loads(payload)
```

## 后端策略

`cells.json` 的接口形状接近标准库 `json`，但行为策略以增强能力为准，不承诺与标准库逐项等价。

- 默认 `backend="auto"` 会优先使用 `orjson`。
- `orjson` 能适配的参数会尽量适配。
- 无法安全适配的标准库参数会直接报错，并提示显式指定 `backend="json"`。

例如：

```python
from decimal import Decimal
from cells.json import dumps, loads

# orjson 主路径支持的参数
payload = dumps({"b": 1, "a": 2}, ensure_ascii=False, sort_keys=True, indent=2)

# 需要标准库解码钩子时，显式指定 json backend
data = loads("{\"value\": 1.25}", parse_float=Decimal, backend="json")
```

### 当前参数策略

- `sort_keys`：在 `orjson` 主路径下已适配。
- `indent=2`：在 `orjson` 主路径下已适配。
- `skipkeys=True`：在 `orjson` 主路径下会先做键过滤，再编码。
- `separators=(",", ":")`：在 `orjson` 主路径下已适配。
- `check_circular=False`：在 `orjson` 主路径下接受，但不保证行为与标准库一致。
- `ensure_ascii=True`、`object_hook`、`parse_float`、`parse_int`、`parse_constant`、`object_pairs_hook`、自定义 `cls`：
  需要显式使用 `backend="json"`。

## 🔍 场景化指南 (QA)

| 场景             | 推荐方案                                                   | 说明                            |
|:---------------|:-------------------------------------------------------|:------------------------------|
| **标准库报不可序列化**  | `safe_json_dumps(data)`                                | 自动转换 datetime/Decimal/UUID 等  |
| **遇到未知类型必须报错** | `UniversalSerializer(strict=True).dumps(data)`         | 严格校验，防止脏数据入库                  |
| **未知类型自动降级为空** | `UniversalSerializer(ignore_unknown=True).dumps(data)` | 无法处理的字段转为 `null`              |
| **存在循环引用**     | `safe_json_dumps(data, fail_on_circular=False)`        | 默认模式，返回 `<CircularReference>` |
| **循环引用必须报错**   | `safe_json_dumps(data, fail_on_circular=True)`         | 抛出 `CircularReferenceError`   |
| **追求极致吞吐量**    | `from cells.json import dumps`                         | 默认优先走 orjson 主路径            |
| **美化输出/美化日志**  | `from cells.json.utils import prettify_json`           | 带缩进和排序的格式化                    |
| **需要标准库解析钩子** | `loads(data, parse_float=Decimal, backend="json")`    | 显式切换到标准库后端                   |

## 📊 性能基准 (Performance)

在 Python 3.13 环境下，对比标准库 `json` 的吞吐量表现：

| 场景                     | 标准 `json.dumps` | `cells-json` (Universal) | 提升倍数      |
|:-----------------------|:----------------|:-------------------------|:----------|
| **简单字典** (2k keys)     | ~5,800 ops/sec  | **~57,000 ops/sec**      | **~10x**  |
| **复杂对象** (500 entries) | ~630 ops/sec    | **~2,100 ops/sec**       | **~3.4x** |

> *注：测试包含类型缓存优化。复杂对象场景包含大量 DateTime、Decimal 和 UUID 的混合处理。*

## 🛠️ 支持的数据类型

- **日期时间**: `datetime`, `date`, `time` (ISO 格式), `timedelta` (总秒数)。
- **数值与标识**: `Decimal` (float), `UUID` (str), `Enum` (value)。
- **科学计算**: `numpy` (ndarray/generic), `pandas` (DataFrame/Series)。
- **容器**: `set`, `tuple` (转换为 list)。
- **自定义对象**:
  - 优先尝试 `to_dict()` 方法。
  - 其次尝试 `__dict__` 或 `__slots__` 序列化。

## ⚠️ 异常处理

本库提供了一套完整的、与底层后端解耦的异常体系：

```python
from cells.json import JSONEncodeError, JSONDecodeError, CircularReferenceError

try:
    payload = dumps(complex_obj)
except CircularReferenceError as e:
    print(f"检测到循环引用: {e.path}")
except JSONEncodeError as e:
    print(f"编码失败，对象类型: {e.obj_type}")

try:
    data = loads(invalid_str)
except JSONDecodeError as e:
    # 保留了标准库的错误位置信息
    print(f"解析失败 at pos {e.pos}: {e.msg}")
```

当 `orjson` 主路径不支持某个标准库参数时，会直接抛出 `TypeError`，并提示使用 `backend="json"`。

## 📂 辅助工具 (Utils)

如需使用以下辅助功能，请从 `cells.json.utils` 导入：

- `save_json(data, path)` / `load_json(path)`：快捷文件读写。
- `prettify_json(data)`：快速生成美化的 JSON 预览。
- `JsonSerializable` 基类：继承后可使用 `obj.to_json()`。
- `@json_serializable` 装饰器：为类动态注入 JSON 序列化能力。

## 📜 许可证

MPL-2.0
