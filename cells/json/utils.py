"""JSON serialization helpers / JSON 序列化辅助工具模块

Provide convenience decorators and helper functions. / 提供便捷的装饰器和辅助函数。
"""

from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from .serializer import UniversalSerializer, safe_json_dumps


T = TypeVar("T")


class JsonSerializable:
    """Base class for serializable objects / 可序列化的基类

    Subclasses inherit automatic JSON serialization support. / 子类可以通过继承此类获得自动的 JSON 序列化能力。

    Example:
        >>> class User(JsonSerializable):
        ...     def __init__(self, name, age):
        ...         self.name = name
        ...         self.age = age
        >>> user = User("Alice", 25)
        >>> user.to_json()
        '{"name": "Alice", "age": 25}'
    """

    def to_dict(self) -> dict:
        """Convert an object to a dictionary / 将对象转换为字典

        :return: Dictionary representation of the object / 对象的字典表示
        """
        result = {}
        if hasattr(self, "__dict__"):
            result.update(self.__dict__)
        return result

    def to_json(self, **kwargs: Any) -> str:
        """Serialize an object to a JSON string / 将对象序列化为 JSON 字符串

        :param kwargs: Additional arguments for json.dumps / json.dumps 的额外参数
        :return: JSON string / JSON 字符串
        """
        serializer = UniversalSerializer()
        return serializer.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls: type[T], data: dict) -> T:
        """Create an object from a dictionary / 从字典创建对象

        :param data: Dictionary containing the object data / 包含对象数据的字典
        :return: The created object instance / 创建的对象实例
        """
        return cls(**data)


def json_serializable[T](cls: type[T]) -> type[T]:
    """Class decorator that adds JSON serialization support / 类装饰器，使类具有 JSON 序列化能力

    Example:
        >>> @json_serializable
        ... class Point:
        ...     def __init__(self, x, y):
        ...         self.x = x
        ...         self.y = y
        >>> point = Point(10, 20)
        >>> point.to_json()
        '{"x": 10, "y": 20}'
    """

    original_init = cls.__init__

    @wraps(original_init)
    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

    def to_dict(self) -> dict:
        """Convert an object to a dictionary / 将对象转换为字典"""
        result = {}
        if hasattr(self, "__dict__"):
            result.update(self.__dict__)
        elif hasattr(self, "__slots__"):
            for slot in self.__slots__:
                if hasattr(self, slot):
                    result[slot] = getattr(self, slot)
        return result

    def to_json(self, **kwargs: Any) -> str:
        """Serialize an object to a JSON string / 将对象序列化为 JSON 字符串"""
        serializer = UniversalSerializer()
        return serializer.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, data: dict):
        """Create an object from a dictionary / 从字典创建对象"""
        return cls(**data)

    cls.__init__ = __init__
    cls.to_dict = to_dict
    cls.to_json = to_json
    cls.from_dict = from_dict

    return cls


def save_json(data: Any, filepath: str | Path, **kwargs: Any) -> None:
    """Save data to a JSON file / 将数据保存为 JSON 文件

    :param data: The data to save / 待保存的数据
    :param filepath: File path / 文件路径
    :param kwargs: Additional arguments for json.dump / json.dump 的额外参数
    :raises JSONSerializationError: If serialization fails / 如果序列化失败

    Example:
        >>> data = {"name": "Alice", "age": 25}
        >>> save_json(data, "user.json")
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    serializer = UniversalSerializer()
    with open(filepath, "w", encoding="utf-8") as f:
        serializer.dump(data, f, **kwargs)


def load_json(filepath: str | Path, **kwargs: Any) -> Any:
    """Load data from a JSON file / 从 JSON 文件加载数据

    :param filepath: File path / 文件路径
    :param kwargs: Additional arguments for json.load / json.load 的额外参数
    :return: The loaded data / 加载的数据

    Example:
        >>> data = load_json("user.json")
        >>> print(data)
        {'name': 'Alice', 'age': 25}
    """
    import json

    filepath = Path(filepath)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f, **kwargs)


def prettify_json(data: Any, indent: int = 2, **kwargs: Any) -> str:
    """Format a JSON string for readable output / 格式化 JSON 字符串（美化输出）

    :param data: The data to serialize / 待序列化的数据
    :param indent: Indentation width in spaces; defaults to 2 / 缩进空格数，默认为 2
    :param kwargs: Additional arguments for json.dumps / json.dumps 的额外参数
    :return: The formatted JSON string / 格式化后的 JSON 字符串

    Example:
        >>> data = {"name": "Alice", "age": 25}
        >>> print(prettify_json(data))
        {
          "name": "Alice",
          "age": 25
        }
    """
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("sort_keys", False)
    return safe_json_dumps(data, indent=indent, **kwargs)
