"""JSON serialization utilities / JSON 序列化工具模块

Provide general JSON serialization for common Python serialization needs: / 提供通用的 JSON 序列化能力，处理 Python 中常见的序列化问题：
- Serialize datetime/date objects / datetime/date 对象序列化
- Serialize Decimal objects / Decimal 对象序列化
- Serialize UUID objects / UUID 对象序列化
- Serialize NumPy arrays / numpy 数组序列化
- Serialize custom objects / 自定义对象的序列化
- Serialize complex data structures / 复杂数据结构的序列化
- Support multiple JSON backends (json, orjson) / 多种 JSON 后端支持（json、orjson）
"""

from .adapter import JSONAdapter, dump, dumps, load, loads
from .exceptions import (
    CircularReferenceError,
    JSONDecodeError,
    JSONEncodeError,
    JSONSerializationError,
    UnsupportedTypeError,
)
from .serializer import UniversalSerializer, safe_json_dumps
from .utils import prettify_json
from .version import __VERSION__


__all__ = [
    # Core serializers / 核心序列化器
    "UniversalSerializer",
    "safe_json_dumps",
    # Exception classes / 异常类
    "JSONSerializationError",
    "JSONEncodeError",
    "JSONDecodeError",
    "CircularReferenceError",
    "UnsupportedTypeError",
    # Adapter (supports multiple JSON backends) / 适配器（支持多种 JSON 后端）
    "JSONAdapter",
    "dump",
    "dumps",
    "load",
    "loads",
    "prettify_json",
    "__VERSION__",
]
