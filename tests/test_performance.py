"""Compare cells-json with standard-library json. / 对比 cells-json 与 Python 标准库 json。"""

import argparse
import decimal
import gc
import json
import platform
import sys
import timeit
import uuid
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from statistics import median
from typing import Any


# Use the local checkout when running this script directly. / 直接运行脚本时使用本地源码。
sys.path.insert(0, str(Path(__file__).parent.parent))

from cells.json import UniversalSerializer
from cells.json.adapter import JSONAdapter


def get_simple_data(size: int = 1000) -> dict[str, Any]:
    """Build a dictionary of basic values. / 构造包含基础类型的字典。"""
    return {f"key_{i}": i for i in range(size)}


def get_complex_data(size: int = 1000) -> dict[str, Any]:
    """Build data requiring extended type conversion. / 构造需要扩展类型转换的数据。"""
    return {
        f"id_{i}": {
            "uuid": uuid.uuid4(),
            "time": datetime.now(),
            "price": decimal.Decimal("199.99"),
            "path": Path("/usr/bin/python"),
            "tags": [f"tag_{i}"] * 5,
        }
        for i in range(size)
    }


class PerformanceRunner:
    """Measure equivalent string-output serialization. / 测量等价字符串输出的序列化性能。"""

    def __init__(self, data: Any, iterations: int = 100, repeats: int = 5):
        self.data = data
        self.iterations = iterations
        self.repeats = repeats
        # Require orjson so CI cannot silently benchmark a fallback. / 要求 orjson，避免 CI 静默测试回退后端。
        self.adapter_auto = JSONAdapter(backend="orjson", use_builtin=True)
        self.adapter_custom = JSONAdapter(backend="orjson", use_builtin=False)
        self.serializer = UniversalSerializer()

    def run_benchmark(self, label: str) -> list[tuple[str, float]]:
        """Return median durations for each implementation. / 返回各实现的耗时中位数。"""
        options = {"ensure_ascii": False, "separators": (",", ":")}
        serializers = [
            (
                "Standard json.dumps",
                lambda: json.dumps(self.data, default=self.serializer.default, **options),
            ),
            ("cells-json (built-in)", lambda: self.adapter_auto.dumps(self.data, **options)),
            ("cells-json (universal)", lambda: self.adapter_custom.dumps(self.data, **options)),
        ]

        # Verify output types and values before timing; this also warms handlers. / 计时前验证输出类型和值，同时预热处理函数。
        expected = json.loads(serializers[0][1]())
        for name, serialize in serializers:
            payload = serialize()
            if not isinstance(payload, str) or json.loads(payload) != expected:
                raise AssertionError(f"{name} produced a different JSON value or output type")

        print(f"\n{label}: {self.iterations} iterations, median of {self.repeats} repeats")
        results = []
        for name, serialize in serializers:
            gc.collect()
            duration = median(timeit.repeat(serialize, number=self.iterations, repeat=self.repeats))
            results.append((name, duration))
            print(f"{name:<28}: {self.iterations / duration:>12,.2f} ops/sec")
        return results


def core_main(markdown: Path | None = None) -> None:
    """Run both scenarios and optionally write a Markdown report. / 运行两个场景并可选写入 Markdown 报告。"""
    lines = [
        "## Serialization benchmark",
        "",
        f"- Python: {platform.python_implementation()} {platform.python_version()}",
        f"- Platform: {platform.platform()}",
        f"- Processor: {platform.processor() or platform.machine()}",
        f"- orjson: {version('orjson')}",
        "- Metric: serializations/second; median of 5 repeats.",
        "- All implementations return str, use ensure_ascii=False and compact separators.",
        "- Extended types use equivalent conversions; decoded values are checked before timing.",
        "- Data construction, validation and file I/O are excluded from the timed region.",
        "",
        "| Scenario | Iterations/repeat | Implementation | ops/sec | Relative to stdlib |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    scenarios = [
        ("Simple dictionary (2k keys)", get_simple_data(2000), 500),
        ("Complex objects (500 entries)", get_complex_data(500), 100),
    ]
    for label, data, iterations in scenarios:
        runner = PerformanceRunner(data, iterations)
        results = runner.run_benchmark(label)
        baseline = results[0][1]
        for name, duration in results:
            lines.append(
                f"| {label} | {iterations} | {name} | {iterations / duration:,.2f} "
                f"| {baseline / duration:.2f}x |"
            )
    lines.extend(
        ["", "Results describe this runner and payload; they are not a fixed speed guarantee.", ""]
    )
    if markdown is not None:
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nMarkdown report: {markdown}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", type=Path, help="Write benchmark results to a Markdown file")
    core_main(parser.parse_args().markdown)
