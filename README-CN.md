# cells-json

[English](README.md) | [简体中文](README-CN.md) | [日本語](README-JP.md)

面向 Python 应用的 JSON 序列化工具，发行包名为 `cells-json`，导入路径为 `cells.json`。

本库结合优先使用 `orjson` 的适配器与可配置的序列化器，处理日期、十进制数、标识符、科学计算数据和自定义对象。除常见的 `dump`、`dumps`、`load`、`loads` 接口外，还提供递归转换能力，用于需要显式处理循环引用的场景。

## 功能特性

- 优先使用 `orjson` 的适配器，支持显式选择标准库后端。
- 扩展类型转换，并缓存类型处理函数。
- 递归序列化，支持以标记字符串或异常处理循环引用。
- 可配置的未知类型与自定义对象处理策略。
- 主接口使用统一的编码与解码异常。
- 文件读写、格式化以及类序列化辅助工具。

## 安装

```bash
python -m pip install cells-json
```

`orjson` 是必需依赖。NumPy 和 pandas 需要单独安装，安装后启用对应的类型支持。

当前源码请使用 **Python 3.14**：代码使用了 Python 3.14 引入的异常语法。包元数据目前声明 `Python >=3.9`，但该声明未反映当前源码的语法要求。CI 测试任务配置为在 Linux 和 Windows 上使用 Python 3.14。

## 快速开始

```python
from datetime import datetime
from decimal import Decimal

from cells import json

payload = json.dumps(
    {"created_at": datetime(2026, 1, 1, 12, 0), "amount": Decimal("19.95")},
    ensure_ascii=False,
    indent=2,
)
data = json.loads(payload)

assert data["created_at"] == "2026-01-01T12:00:00"
assert data["amount"] == 19.95
```

`dumps()` 默认返回 `str`。使用 `orjson` 后端时，设置 `ensure_str=False` 可返回 `bytes`；标准库后端返回 `str`。`loads()` 接受 `str`、`bytes` 或 `bytearray`，返回普通 Python 值。

## 选择序列化接口

| 接口 | 用途 | 编码路径 |
| --- | --- | --- |
| `dumps()` / `dump()` | 通过接近标准库的接口序列化 | 优先使用 `orjson`；可显式指定 `backend="json"` |
| `loads()` / `load()` | 解析 JSON 文本或可读流 | 与适配器采用相同的后端选择方式 |
| `safe_json_dumps()` | 递归转换对象树并处理循环引用 | 转换后使用标准库 `json` |
| `UniversalSerializer` | 复用类型转换规则，或提供 `default` 回调 | 其 `dumps()` 和 `dump()` 使用标准库 `json` |
| `JSONAdapter` | 复用固定后端和序列化配置的适配器 | 可配置适配器 |

递归转换示例：

```python
from datetime import date
from cells.json import safe_json_dumps

payload = safe_json_dumps(
    {"date": date(2026, 1, 1), "tags": {"python", "json"}},
    ensure_ascii=False,
    indent=2,
)
```

`safe_json_dumps()` 会在编码前将字典键转为字符串，将元组和集合转为列表。集合元素的顺序不作保证。重新加载 JSON 时，不会恢复原始 Python 类型。

## 后端行为与兼容性

适配器的接口形态接近标准库 `json`，但不保证所有参数和值的行为完全一致。

- `backend="auto"` 在 `orjson` 可用时优先使用它，否则使用标准库 `json`。
- `backend="orjson"` 要求已安装 `orjson`；缺少依赖时，构造适配器会抛出 `RuntimeError`。
- `backend="json"` 显式选择标准库编码和解码，同时保留本库的扩展类型回调。

不支持的参数不会触发自动切换后端。需要标准库参数语义时，请指定 `backend="json"`。

| 参数 | 使用 `orjson` 后端时的行为 |
| --- | --- |
| `ensure_ascii=True` | 支持，编码后转义非 ASCII 字符；这是默认值 |
| `sort_keys=True` | 支持 |
| `indent=2` | 支持；其他非 `None` 缩进值需要 `backend="json"` |
| `separators=(",", ":")` | 支持；其他显式分隔符需要 `backend="json"` |
| `skipkeys=True` | 编码前过滤不支持的字典键 |
| `check_circular=False` | 接受该参数，但不保证与标准库的循环引用语义一致 |
| `allow_nan=False` | 需要 `backend="json"` |
| 自定义编码器或解码器 `cls` | 需要 `backend="json"` |
| `object_hook`、`object_pairs_hook`、`parse_float`、`parse_int`、`parse_constant` | 需要 `backend="json"` |

例如，解析时需要保留十进制数，可使用标准库后端：

```python
from decimal import Decimal
from cells.json import dumps, loads

payload = dumps({"b": 1, "a": 2}, sort_keys=True, indent=2)
data = loads('{"amount": 19.95}', parse_float=Decimal, backend="json")

assert data["amount"] == Decimal("19.95")
```

不同后端对非有限数值、整数范围和字典键的原生处理也可能不同。如果这些行为影响数据契约，请显式选择后端。

## 支持的类型转换

下表描述 `UniversalSerializer` 和递归接口的转换规则。对于 `orjson` 已支持的类型，适配器可能使用该后端的原生处理。

| Python 类型 | JSON 表示 |
| --- | --- |
| `datetime`、`date`、`time` | ISO 格式字符串 |
| `timedelta` | 以数值表示的总秒数 |
| `Decimal` | 浮点数 |
| `UUID` | 字符串 |
| `Enum` | 继续序列化其 `value` |
| `Path` | POSIX 风格路径字符串 |
| `set`、`tuple` | 数组 |
| NumPy `ndarray` / 标量 | 嵌套列表 / Python 原生值 |
| pandas `DataFrame` | 由行记录组成的数组 |
| 有名称的 pandas `Series` | 将字符串形式的名称映射到值列表的对象 |
| 无名称的 pandas `Series` | 索引到值的映射 |
| 自定义对象 | 依次尝试 `to_dict()`、`__dict__`、`__slots__`，受配置控制 |

`Decimal` 转为 `float` 可能损失精度。如果输出需要精确保留十进制值，可向 `dumps()` 传入 `default=str` 等显式转换函数，或在序列化前将数值转为字符串。

### 自定义对象与未知类型

```python
from cells.json import UniversalSerializer


class User:
    def __init__(self, name):
        self.name = name

    def to_dict(self):
        return {"name": self.name}


serializer = UniversalSerializer()
payload = serializer.dumps(User("Alice"))
```

- `strict=True` 禁用自定义对象的自动检查，包括 `to_dict()`。已支持的内置类型转换仍然可用。
- `ignore_unknown=True` 将仍无法处理的值转为 `null`，默认禁用属性检查。未启用严格模式时，已识别的 `to_dict()` 方法仍可使用。
- `use_dict=False` 禁用 `__dict__` 和 `__slots__` 检查；在非严格模式下仍可使用 `to_dict()`。
- `UniversalSerializer(default=callback)` 为无法处理的类型提供后备转换函数。

没有适用的后备处理时，未知类型会抛出 `JSONEncodeError`。自动检查属性可能包含内部属性；需要明确控制输出字段时，请定义 `to_dict()` 或禁用属性检查。

## 循环引用

需要递归处理循环引用时，使用 `safe_json_dumps()`。默认将循环引用替换为 `"<CircularReference dict>"` 等字符串；设置 `fail_on_circular=True` 则抛出 `CircularReferenceError`。

```python
from cells.json import CircularReferenceError, safe_json_dumps

node = {}
node["self"] = node

payload = safe_json_dumps(node)
assert "<CircularReference dict>" in payload

try:
    safe_json_dumps(node, fail_on_circular=True)
except CircularReferenceError:
    pass
```

`UniversalSerializer.dumps()` 默认不进行递归预转换，可通过 `recursive=True` 启用。适配器接口不提供相同的递归标记处理。

`safe_json_dumps(ignore_errors=True, default_value="null")` 会在捕获到该辅助函数所处理的序列化异常时返回后备字符串，并不会抑制所有可能的异常。

## 文件与辅助工具

```python
from pathlib import Path
from cells.json import dump, load
from cells.json.utils import load_json, save_json

path = Path("settings.json")

with path.open("w", encoding="utf-8") as stream:
    dump({"enabled": True}, stream, indent=2)

with path.open("r", encoding="utf-8") as stream:
    data = load(stream)

save_json({"enabled": True}, "output/settings.json", indent=2)
data = load_json("output/settings.json")
```

主接口 `dump()` / `load()` 操作已打开的流。UTF-8 文本流适用于两种后端。`save_json()` 自动创建父目录，并通过 `UniversalSerializer` 以 UTF-8 写入；`load_json()` 以 UTF-8 读取，并使用标准库 `json` 解析。

其他辅助工具：

- `prettify_json(data, indent=2)`：通过 `safe_json_dumps()` 将 Python 值序列化为带缩进的 JSON；也可从 `cells.json` 导入。
- `JsonSerializable`：提供 `to_dict()`、`to_json()` 和 `from_dict()` 的基类。
- `@json_serializable`：为类添加相同方法的装饰器。

类辅助工具从 `cells.json.utils` 导入。它们的 `from_dict()` 方法调用 `cls(**data)`，不会自动恢复日期、十进制数或其他原始类型。

## 异常处理

```python
from cells.json import JSONDecodeError, JSONEncodeError, dumps, loads

try:
    dumps(object(), strict=True)
except JSONEncodeError as exc:
    print(exc.obj_type, str(exc))

try:
    loads("{invalid}")
except JSONDecodeError as exc:
    print(exc.pos, exc.msg)
```

`JSONEncodeError` 继承自 `TypeError`；`CircularReferenceError` 是 `JSONEncodeError` 的子类。`JSONDecodeError` 继承自 `ValueError`，提供 `msg`、`doc` 和 `pos` 属性；它并非标准库的 `json.JSONDecodeError` 类。

使用 `orjson` 时，不支持的编码参数会报告为 `JSONEncodeError`，该异常同时也是 `TypeError`；不支持的解码参数会抛出 `TypeError`。错误信息会提示使用 `backend="json"`。

## 开发与性能评估

在本地源码目录中，使用 Python 3.14：

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest tests/test_serializer.py -v
```

未安装 NumPy 或 pandas 时，对应测试会提前返回。需要验证这些转换时，请单独安装相应依赖。

运行仓库提供的基准脚本：

```bash
python tests/test_performance.py
```

使用 `python tests/test_performance.py --markdown benchmark.md` 可写入报告。基准对比标准库 `json` 与 `cells-json` 的两种适配器模式，采用等价转换和字符串输出，并报告五轮测量的中位数。

推送 `v*` 标签会发布 GitHub Release，附带构建压缩包，并在说明中包含 benchmark 结果。推送 `main` 会更新 `rolling` 预发布及其标签，指向本次构建提交。通过 `GITHUB_TOKEN` 创建的 GitHub Release 不会触发独立的、由 release 事件驱动的 PyPI 工作流。

性能受数据内容、后端、转换路径、参数和运行环境影响。该脚本用于本地对比，不保证固定的性能提升倍数。

## 许可证

包元数据声明使用 Mozilla Public License 2.0（`MPL-2.0`）。
