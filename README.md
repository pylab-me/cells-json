# cells-json

[English](README.md) | [简体中文](README-CN.md) | [日本語](README-JP.md)

JSON serialization utilities for Python applications, published as `cells-json` and imported as `cells.json`.

The library combines an `orjson`-first adapter with a configurable serializer for dates, decimals, identifiers, scientific data, and custom objects. It provides familiar `dump`, `dumps`, `load`, and `loads` entry points, plus recursive conversion when circular references need explicit handling.

## Features

- An `orjson`-first adapter with an explicitly selectable standard-library backend.
- Extended type conversion with cached type handlers.
- Recursive serialization with circular-reference markers or exceptions.
- Configurable handling of unknown types and custom objects.
- Shared encoding and decoding exceptions for the main APIs.
- File helpers, formatting utilities, and class serialization helpers.

## Installation

```bash
python -m pip install cells-json
```

`orjson` is a required package dependency. NumPy and pandas support is enabled when those packages are installed separately.

Use **Python 3.14** for the current source tree: it uses exception syntax introduced in Python 3.14. Package metadata currently declares `Python >=3.9`; that declaration does not reflect the syntax requirement of the current source. The CI test job is configured for Python 3.14 on Linux and Windows.

## Quick start

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

`dumps()` returns `str` by default. With the `orjson` backend, `ensure_str=False` returns `bytes`; the standard-library backend returns `str`. `loads()` accepts `str`, `bytes`, or `bytearray` and returns ordinary Python values.

## Choosing a serialization API

| API | Purpose | Encoding path |
| --- | --- | --- |
| `dumps()` / `dump()` | Serialize with a familiar standard-library-style interface | Prefers `orjson`; select `backend="json"` explicitly |
| `loads()` / `load()` | Parse JSON text or a readable stream | Same backend selection as the adapter |
| `safe_json_dumps()` | Recursively convert an object tree and handle circular references | Standard-library `json` after conversion |
| `UniversalSerializer` | Reuse type conversion rules or provide a `default` callback | Its `dumps()` and `dump()` use standard-library `json` |
| `JSONAdapter` | Reuse an adapter with a fixed backend and serializer configuration | Configurable adapter |

For recursive conversion:

```python
from datetime import date
from cells.json import safe_json_dumps

payload = safe_json_dumps(
    {"date": date(2026, 1, 1), "tags": {"python", "json"}},
    ensure_ascii=False,
    indent=2,
)
```

`safe_json_dumps()` stringifies dictionary keys and converts tuples and sets to lists before encoding. Set element order is not guaranteed. It does not preserve the original Python types when the JSON is loaded again.

## Backend behavior and compatibility

The adapter resembles standard-library `json`, but does not promise identical behavior for every option or value.

- `backend="auto"` prefers `orjson` when available and otherwise uses standard-library `json`.
- `backend="orjson"` requires `orjson`; constructing the adapter without it raises `RuntimeError`.
- `backend="json"` explicitly selects standard-library encoding and decoding while retaining the library's extended type callback.

Unsupported options do not trigger an automatic backend switch. Select `backend="json"` when standard-library parameter semantics are required.

| Option | Active `orjson` backend |
| --- | --- |
| `ensure_ascii=True` | Supported by escaping non-ASCII characters after encoding; this is the default |
| `sort_keys=True` | Supported |
| `indent=2` | Supported; other non-`None` indentation values require `backend="json"` |
| `separators=(",", ":")` | Supported; other explicit separators require `backend="json"` |
| `skipkeys=True` | Filters unsupported dictionary keys before encoding |
| `check_circular=False` | Accepted; does not guarantee standard-library circular-reference semantics |
| `allow_nan=False` | Requires `backend="json"` |
| Custom encoder/decoder `cls` | Requires `backend="json"` |
| `object_hook`, `object_pairs_hook`, `parse_float`, `parse_int`, `parse_constant` | Require `backend="json"` |

For example, use the standard-library backend to preserve decimal values while parsing:

```python
from decimal import Decimal
from cells.json import dumps, loads

payload = dumps({"b": 1, "a": 2}, sort_keys=True, indent=2)
data = loads('{"amount": 19.95}', parse_float=Decimal, backend="json")

assert data["amount"] == Decimal("19.95")
```

Backend-native behavior can also differ for non-finite numbers, integer ranges, and dictionary keys. Choose the backend explicitly when these details matter to your data contract.

## Supported type conversions

These conversions describe `UniversalSerializer` and the recursive API. The adapter may use `orjson`'s native support for types that backend already handles.

| Python type | JSON representation |
| --- | --- |
| `datetime`, `date`, `time` | ISO-formatted string |
| `timedelta` | Total seconds as a number |
| `Decimal` | Floating-point number |
| `UUID` | String |
| `Enum` | Its `value`, serialized in turn |
| `Path` | POSIX-style path string |
| `set`, `tuple` | Array |
| NumPy `ndarray` / scalar | Nested lists / native Python value |
| pandas `DataFrame` | Array of row records |
| Named pandas `Series` | Object mapping its stringified name to a value list |
| Unnamed pandas `Series` | Index-to-value mapping |
| Custom object | `to_dict()`, then `__dict__`, then `__slots__`, subject to configuration |

`Decimal` conversion to `float` can lose precision. For exact decimal output, provide an explicit conversion such as `default=str` to `dumps()`, or convert values to strings before serialization.

### Custom objects and unknown types

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

- `strict=True` disables automatic custom-object inspection, including `to_dict()`. Built-in supported conversions remain available.
- `ignore_unknown=True` converts otherwise unhandled values to `null` and disables attribute inspection by default. A recognized `to_dict()` method can still be used unless strict mode is enabled.
- `use_dict=False` disables `__dict__` and `__slots__` inspection while leaving `to_dict()` available outside strict mode.
- `UniversalSerializer(default=callback)` supplies a fallback for unhandled types.

Unknown types raise `JSONEncodeError` when no fallback applies. Automatic attribute inspection can include internal attributes; define `to_dict()` or disable inspection when you need explicit field selection.

## Circular references

Use `safe_json_dumps()` for recursive circular-reference handling. The default behavior replaces a cycle with a string such as `"<CircularReference dict>"`; `fail_on_circular=True` raises `CircularReferenceError`.

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

`UniversalSerializer.dumps()` does not recursively preconvert by default. Use `recursive=True` for that behavior. The adapter APIs do not provide the same recursive marker handling.

`safe_json_dumps(ignore_errors=True, default_value="null")` returns the fallback string for serialization exceptions handled by that helper. It does not suppress every possible exception.

## Files and utilities

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

The main `dump()` / `load()` APIs operate on open streams. UTF-8 text streams work with both backends. `save_json()` creates parent directories and writes UTF-8 using `UniversalSerializer`; `load_json()` reads UTF-8 using standard-library `json`.

Additional helpers:

- `prettify_json(data, indent=2)`: serializes a Python value with indentation through `safe_json_dumps()`; also exported from `cells.json`.
- `JsonSerializable`: base class providing `to_dict()`, `to_json()`, and `from_dict()`.
- `@json_serializable`: decorator adding the same methods to a class.

Import the class helpers from `cells.json.utils`. Their `from_dict()` methods call `cls(**data)`; they do not automatically restore dates, decimals, or other original types.

## Error handling

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

`JSONEncodeError` inherits from `TypeError`; `CircularReferenceError` is a subclass of `JSONEncodeError`. `JSONDecodeError` inherits from `ValueError` and exposes `msg`, `doc`, and `pos`. It is not the standard library's `json.JSONDecodeError` class.

Unsupported encoding options on the active `orjson` path are reported as `JSONEncodeError`, which is also a `TypeError`. Unsupported decoding options raise `TypeError`. These messages direct callers to `backend="json"`.

## Development and performance

From a local checkout, using Python 3.14:

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest tests/test_serializer.py -v
```

Tests for NumPy and pandas return early when those optional packages are absent. Install them separately to exercise those conversions.

Run the included benchmark with:

```bash
python tests/test_performance.py
```

Performance depends on the payload, backend, conversion path, options, and environment. The benchmark is a local comparison tool; no fixed speedup is guaranteed.

## License

The package metadata declares the Mozilla Public License 2.0 (`MPL-2.0`).
