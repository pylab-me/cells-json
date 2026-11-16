"""Core JSON serializer module. / JSON 序列化器核心模块。

Provide general serialization logic for a range of Python data types. / 提供通用的 JSON 序列化逻辑，支持多种 Python 数据类型的序列化。
"""

import json
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from .exceptions import CircularReferenceError, JSONEncodeError, JSONSerializationError


try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class UniversalSerializer:
    """General-purpose JSON serialization converter. / 通用 JSON 序列化转换器。

    Provide configurable serialization for the following types: / 提供灵活的类型序列化能力，支持以下类型：
    - **Dates and times**: `datetime`, `date`, `time` (ISO format), `timedelta` (total seconds). / **日期时间**: `datetime`, `date`, `time` (ISO 格式), `timedelta` (总秒数)。
    - **Numbers**: `Decimal` (converted to float). / **数值**: `Decimal` (转换为 float)。
    - **Identifiers**: `UUID` (converted to a string). / **标识符**: `UUID` (转换为字符串)。
    - **Enums**: `Enum` (converted to its value). / **枚举**: `Enum` (转换为其 value)。
    - **Paths**: `Path` (converted to a POSIX-style string). / **路径**: `Path` (转换为 POSIX 风格字符串)。
    - **Scientific computing**: / **科学计算**:
        - `numpy`: `ndarray` (converted to a list), `generic` (converted to a native type). / `numpy`: `ndarray` (转换为 list), `generic` 类型 (转换为对应原生类型)。
        - `pandas`: `DataFrame` (converted to records), `Series` (converted to a dict/list). / `pandas`: `DataFrame` (转换为记录列表), `Series` (转换为 dict/list)。
    - **Containers**: `set`, `tuple` (converted to a list). / **容器**: `set`, `tuple` (转换为 list)。
    - **Custom objects**: / **自定义对象**:
        - Prefer the `to_dict()` method. / 优先调用 `to_dict()` 方法。
        - Then try the `__dict__` or `__slots__` attributes. / 其次尝试使用 `__dict__` 或 `__slots__` 属性。

    Examples:
        ```python
        import json
        from datetime import datetime

        serializer = UniversalSerializer()
        data = {"now": datetime.now()}
        json.dumps(data, default=serializer.default)
        ```
    """

    def __init__(
        self,
        default: Callable[[Any], Any] | None = None,
        strict: bool = False,
        ignore_unknown: bool = False,
        fail_on_circular: bool = False,
        use_dict: bool | None = None,
    ):
        """Initialize the serializer. / 初始化序列化器。

        Args:
            default: Custom fallback serialization function. / 自定义的兜底序列化函数。
            strict: Strict mode; raise an exception for unknown types when True. / 严格模式。如果为 True，遇到未知类型将抛出异常。
            ignore_unknown: Whether to ignore unknown types by serializing them as None. / 是否忽略未知类型（序列化为 None）。
            fail_on_circular: Whether to raise on circular references; return a marker string when False. / 发现循环引用时是否抛出异常。如果为 False，则返回标记字符串。
            use_dict: Whether to inspect __dict__ or __slots__; the default depends on ignore_unknown. / 是否尝试通过 __dict__ 或 __slots__ 序列化自定义对象。默认根据 ignore_unknown 自动决定。
        """
        self._custom_default = default
        self._strict = strict
        self._ignore_unknown = ignore_unknown
        self._fail_on_circular = fail_on_circular
        self._use_dict = use_dict if use_dict is not None else not ignore_unknown
        self._seen: set[int] = set()
        self._type_cache: dict[type, Callable[[Any], Any]] = {}

    def _handle_unknown(self, obj: Any) -> Any:
        """Apply shared handling for unknown types. / 处理未知类型的统一逻辑。

        Args:
            obj: An object of an unknown type. / 未知类型的对象。

        Returns:
            Any: The converted result, such as None. / 转换后的结果（如 None）。

        Raises:
            JSONEncodeError: Raised when conversion fails and ignoring unknown types is disabled. / 当无法处理且未开启忽略模式时抛出。
        """
        if self._custom_default:
            return self._custom_default(obj)
        if self._ignore_unknown:
            return None
        raise JSONEncodeError(obj)

    def default(self, obj: Any) -> Any:
        """Provide a single-level callback for the JSON engine (fast path). / 提供给 JSON 引擎的单层回调 (Fast Path)。

        Args:
            obj: The object to convert. / 待转换的对象。

        Returns:
            Any: The converted object in a basic Python type. / 转换后的基础 Python 类型对象。

        Raises:
            JSONEncodeError: Raised when conversion fails. / 转换失败时抛出。
        """
        obj_type = type(obj)
        if handler := self._type_cache.get(obj_type):
            return handler(obj)

        handler = self._get_handler(obj)
        if handler:
            self._type_cache[obj_type] = handler
            return handler(obj)

        return self._handle_unknown(obj)

    def _get_handler(self, obj: Any) -> Callable[[Any], Any] | None:
        """Find and return a conversion handler for the object. / 查找并返回对象的转换函数。"""
        # 1. Basic types / 基础类型
        if isinstance(obj, (datetime, date, time)):
            return lambda o: o.isoformat()
        if isinstance(obj, timedelta):
            return lambda o: o.total_seconds()
        if isinstance(obj, Decimal):
            return lambda o: float(o)
        if isinstance(obj, UUID):
            return lambda o: str(o)
        if isinstance(obj, Enum):
            return lambda o: o.value
        if isinstance(obj, Path):
            return lambda o: o.as_posix()
        if isinstance(obj, (set, tuple)):
            return lambda o: list(o)

        # 2. Scientific computing / 科学计算
        if HAS_NUMPY:
            if isinstance(obj, np.ndarray):
                return lambda o: o.tolist()
            if isinstance(obj, np.generic):
                return lambda o: o.item()
        if HAS_PANDAS:
            if isinstance(obj, pd.DataFrame):
                return lambda o: o.to_dict("records")
            if isinstance(obj, pd.Series):
                if obj.name is not None:
                    return lambda o: {str(o.name): o.tolist()}
                return lambda o: o.to_dict()

        # 3. Custom objects / 自定义对象
        if not self._strict:
            if hasattr(obj, "to_dict") and callable(obj.to_dict):
                return lambda o: o.to_dict()
            if self._use_dict:
                if hasattr(obj, "__dict__"):
                    return lambda o: o.__dict__
                if hasattr(obj, "__slots__"):
                    return lambda o: {s: getattr(o, s) for s in o.__slots__ if hasattr(o, s)}

        return None

    def _serialize_recursive(self, obj: Any) -> Any:
        """Serialize recursively (safe path). / 递归序列化 (Safe Path)。

        Support circular reference detection and marker string generation. / 用于支持循环引用检测和标记字符串生成。

        Args:
            obj: The object to convert. / 待转换的对象。

        Returns:
            Any: The recursively converted value in basic Python types. / 递归转换后的基础 Python 类型。

        Raises:
            CircularReferenceError: Raised when a cycle is detected and fail_on_circular is enabled. / 检测到循环引用且开启了 fail_on_circular 时抛出。
        """
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        obj_id = id(obj)
        if obj_id in self._seen:
            if self._fail_on_circular:
                raise CircularReferenceError(obj)
            return f"<CircularReference {type(obj).__name__}>"

        self._seen.add(obj_id)
        try:
            if isinstance(obj, dict):
                return {str(k): self._serialize_recursive(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple, set)):
                return [self._serialize_recursive(item) for item in obj]

            # Try single-level conversion first for other types / 对于其他类型，先尝试单层转换
            try:
                res = self.default(obj)
                # Return None directly when conversion yields None and ignore_unknown is enabled / 如果返回的是 None 且开启了 ignore_unknown，直接返回 None
                if res is None and self._ignore_unknown:
                    return None
                # Continue recursively if conversion returns a new object / 如果返回了新对象，继续递归
                if res is not obj:
                    return self._serialize_recursive(res)
            except JSONEncodeError:
                pass

            return self._handle_unknown(obj)
        finally:
            self._seen.discard(obj_id)

    def encode(self, obj: Any) -> Any:
        """Convert the entire object tree to basic Python types. / 完整地将对象树转换为基础 Python 类型。

        Args:
            obj: The original object tree. / 原始对象树。

        Returns:
            Any: The converted object tree. / 转换后的对象树。
        """
        self._seen.clear()
        return self._serialize_recursive(obj)

    def dumps(self, obj: Any, recursive: bool = False, **kwargs: Any) -> str:
        """Serialize an object to a JSON string. / 将对象序列化为 JSON 字符串。

        Args:
            obj: The object to serialize. / 待序列化的对象。
            recursive: Whether to force recursive conversion before encoding. / 是否强制执行递归预转换。
            **kwargs: Arguments forwarded to json.dumps. / 透传给 json.dumps 的参数。

        Returns:
            str: JSON string. / JSON 字符串。

        Raises:
            JSONEncodeError: Raised when serialization fails. / 序列化失败时抛出。
            CircularReferenceError: Raised when a circular reference is detected. / 发现循环引用时抛出。
        """
        try:
            if recursive or self._fail_on_circular or not kwargs.get("check_circular", True):
                return json.dumps(self.encode(obj), **kwargs)
            else:
                return json.dumps(obj, default=self.default, **kwargs)
        except (TypeError, ValueError) as e:
            if "Circular reference" in str(e) and self._fail_on_circular:
                raise CircularReferenceError(obj)
            raise JSONEncodeError(obj, str(e)) from e

    def dump(self, obj: Any, fp, **kwargs: Any) -> None:
        """Serialize an object and write it to a file stream. / 将对象序列化并写入文件流。

        Args:
            obj: The object to serialize. / 待序列化的对象。
            fp: A file-like object. / 文件类对象。
            **kwargs: Additional arguments. / 额外参数。

        Raises:
            JSONEncodeError: Raised when serialization fails. / 序列化失败时抛出。
        """
        try:
            if self._fail_on_circular or not kwargs.get("check_circular", True):
                json.dump(self.encode(obj), fp, **kwargs)
            else:
                json.dump(obj, fp, default=self.default, **kwargs)
        except (TypeError, ValueError) as e:
            raise JSONEncodeError(obj, str(e)) from e


def universal_serializer(obj: Any) -> Any:
    """Convenience serialization callback. / 快捷回调函数。

    Args:
        obj: The object to convert. / 待转换的对象。

    Returns:
        Any: The conversion result. / 转换结果。
    """
    return UniversalSerializer().default(obj)


def safe_json_dumps(
    data: Any,
    *,
    ignore_errors: bool = False,
    default_value: str = "null",
    strict: bool = False,
    ignore_unknown: bool = False,
    fail_on_circular: bool = False,
    use_dict: bool | None = None,
    **kwargs: Any,
) -> str:
    """Serialize JSON safely with explicit configuration parameters. / 安全的 JSON 序列化函数 (显式参数版)。

    Args:
        data: The data to serialize. / 待序列化的数据。
        ignore_errors: Whether to return default_value for handled serialization errors. / 发生错误时是否忽略并返回 default_value。
        default_value: Fallback string returned when errors are ignored. / 忽略错误时返回的默认字符串。
        strict: Strict mode; raise an exception for unknown types. / 严格模式，遇到未知类型抛出异常。
        ignore_unknown: Ignore unknown types by serializing them as None. / 忽略未知类型，序列化为 None。
        fail_on_circular: Raise on circular references (return a marker string when False). / 发现循环引用时抛出异常 (False 则返回 marker 字符串)。
        use_dict: Whether to automatically serialize custom objects using __dict__. / 是否自动使用 __dict__ 序列化自定义对象。
        **kwargs: Arguments passed to json.dumps, such as indent and ensure_ascii. / 传递给 json.dumps 的参数 (如 indent, ensure_ascii 等)。

    Returns:
        str: JSON string. / JSON 字符串。

    Raises:
        JSONEncodeError: Raised when serialization fails and ignore_errors is disabled. / 序列化失败且未开启 ignore_errors 时抛出。
        CircularReferenceError: Raised when a cycle is detected and fail_on_circular is enabled. / 发现循环引用且开启了 fail_on_circular时抛出。

    Examples:
        ```python
        from datetime import datetime

        data = {"time": datetime.now()}
        safe_json_dumps(data, indent=2)
        ```
    """
    try:
        serializer = UniversalSerializer(
            strict=strict,
            ignore_unknown=ignore_unknown,
            fail_on_circular=fail_on_circular,
            use_dict=use_dict,
        )
        return serializer.dumps(data, recursive=True, **kwargs)
    except (JSONSerializationError, JSONEncodeError, CircularReferenceError):
        if ignore_errors:
            return default_value
        raise
