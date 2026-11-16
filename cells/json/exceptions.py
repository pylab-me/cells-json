"""JSON exceptions / JSON 异常模块

Define shared JSON exceptions for consistent API behavior. / 定义统一的 JSON 异常体系，确保 API 接口一致性。
"""

from typing import Any


class JSONError(Exception):
    """Base JSON exception. / JSON 基础异常。"""

    pass


class JSONSerializationError(JSONError, TypeError):
    """Base serialization exception. / 序列化基础异常。

    Inherit TypeError for compatibility with standard-library json. / 继承 TypeError 以保持与标准库 json 的兼容性。

    Attributes:
        obj: The object that cannot be serialized. / 无法序列化的对象。
        obj_type: The object's type. / 对象的类型。

    Examples:
        ```python
        try:
            raise JSONSerializationError(complex_obj)
        except JSONSerializationError as e:
            print(e.obj_type)
        ```
    """

    def __init__(self, obj: Any = None, message: str = None):
        """Initialize a serialization exception. / 初始化序列化异常。

        Args:
            obj: The object that caused the exception. / 导致异常的对象。
            message: Custom error message; generated automatically if omitted. / 自定义错误消息。如果未提供，将自动生成。
        """
        self.obj = obj
        self.obj_type = type(obj) if obj is not None else None
        if message is None:
            if self.obj_type:
                message = f"Object of type {self.obj_type.__name__} is not JSON serializable"
            else:
                message = "JSON serialization error"
        super().__init__(message)


class JSONEncodeError(JSONSerializationError):
    """Shared encoding exception. / 统一的编码异常。

    Examples:
        ```python
        try:
            dumps(set([1, 2]))
        except JSONEncodeError as e:
            print(e)
        ```
    """

    pass


class JSONDecodeError(JSONError, ValueError):
    """Shared decoding exception. / 统一的解码异常。

    Inherit ValueError for compatibility with standard-library json. / 继承 ValueError 以保持与标准库 json 的兼容性。

    Attributes:
        msg: Error message. / 错误消息。
        doc: The JSON document being parsed. / 被解析的 JSON 文档。
        pos: Index of the error position. / 错误发生的位置索引。

    Examples:
        ```python
        try:
            loads('{"invalid": json}')
        except JSONDecodeError as e:
            print(f"Error at {e.pos}: {e.msg}")
        ```
    """

    def __init__(self, message: str, doc: str = "", pos: int = 0):
        """Initialize a decoding exception. / 初始化解码异常。

        Args:
            message: Error description. / 错误描述。
            doc: JSON document content. / JSON 文档内容。
            pos: Byte position of the error in the document. / 错误在文档中的字节位置。
        """
        super().__init__(message)
        self.msg = message
        self.doc = doc
        self.pos = pos

    def __str__(self):
        """Return the formatted error message. / 返回格式化的错误消息。"""
        return f"{self.msg}: line 1 column 1 (char {self.pos})" if self.pos > 0 else self.msg


class CircularReferenceError(JSONEncodeError):
    """Circular reference exception. / 循环引用异常。

    Attributes:
        path: Object path where the circular reference was detected. / 发现循环引用的对象路径。

    Examples:
        ```python
        a = {}
        a["self"] = a
        try:
            safe_json_dumps(a, fail_on_circular=True)
        except CircularReferenceError as e:
            print(e)
        ```
    """

    def __init__(self, obj: Any, path: str = ""):
        """Initialize a circular reference exception. / 初始化循环引用异常。

        Args:
            obj: The object involved in the circular reference. / 循环引用的对象。
            path: Access path to the object. / 对象的访问路径。
        """
        message = f"Circular reference detected for object of type {type(obj).__name__}"
        if path:
            message += f" at path: {path}"
        super().__init__(obj, message)
        self.path = path


class UnsupportedTypeError(JSONSerializationError):
    """Unsupported type exception. / 不支持的类型异常。

    Attributes:
        hint: Hint for serializing this type. / 解决该类型序列化问题的建议。

    Examples:
        ```python
        raise UnsupportedTypeError(
            complex_obj, hint="Implement a to_dict() method / 请实现 to_dict() 方法"
        )
        ```
    """

    def __init__(self, obj: Any, hint: str = ""):
        """Initialize an unsupported type exception. / 初始化不支持类型异常。

        Args:
            obj: The unsupported object. / 不支持的对象。
            hint: Suggested solution or hint. / 解决建议或提示。
        """
        message = f"Unsupported type: {type(obj).__name__}"
        if hint:
            message += f". {hint}"
        super().__init__(obj, message)
        self.hint = hint
