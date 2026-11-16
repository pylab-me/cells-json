# cells-json

[English](README.md) | [简体中文](README-CN.md) | [日本語](README-JP.md)

Python アプリケーション向けの JSON シリアライズユーティリティです。配布パッケージ名は `cells-json`、インポートパスは `cells.json` です。

`orjson` を優先するアダプターと、設定可能なシリアライザーを組み合わせ、日時、十進数、識別子、科学計算データ、カスタムオブジェクトを扱います。`dump`、`dumps`、`load`、`loads` に加え、循環参照を明示的に処理するための再帰変換も提供します。

## 主な機能

- `orjson` を優先するアダプターと、明示的に選択できる標準ライブラリのバックエンド。
- 型ハンドラーのキャッシュを備えた拡張型変換。
- 循環参照をマーカー文字列または例外で処理する再帰シリアライズ。
- 未対応の型やカスタムオブジェクトの処理方針を設定可能。
- 主要 API で共通のエンコード例外とデコード例外。
- ファイル操作、整形、クラスのシリアライズを支援するユーティリティ。

## インストール

```bash
python -m pip install cells-json
```

`orjson` は必須の依存パッケージです。NumPy と pandas は個別にインストールすると、対応する型変換が有効になります。

現在のソースには **Python 3.14** を使用してください。Python 3.14 で導入された例外構文を使用しています。パッケージメタデータには現在 `Python >=3.9` と記載されていますが、これは現在のソースの構文要件を反映していません。CI のテストジョブは、Linux と Windows 上の Python 3.14 で実行する設定です。

## クイックスタート

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

`dumps()` はデフォルトで `str` を返します。`orjson` バックエンドでは `ensure_str=False` を指定すると `bytes` を返し、標準ライブラリのバックエンドでは `str` を返します。`loads()` は `str`、`bytes`、`bytearray` を受け取り、通常の Python の値を返します。

## シリアライズ API の選択

| API | 用途 | エンコード経路 |
| --- | --- | --- |
| `dumps()` / `dump()` | 標準ライブラリに近いインターフェースでシリアライズ | `orjson` を優先。明示的に `backend="json"` を選択可能 |
| `loads()` / `load()` | JSON テキストや読み取り可能なストリームを解析 | アダプターと同じバックエンド選択 |
| `safe_json_dumps()` | オブジェクトツリーを再帰変換し、循環参照を処理 | 変換後に標準ライブラリの `json` を使用 |
| `UniversalSerializer` | 型変換ルールを再利用、または `default` コールバックを提供 | `dumps()` と `dump()` は標準ライブラリの `json` を使用 |
| `JSONAdapter` | バックエンドとシリアライズ設定を固定してアダプターを再利用 | 設定可能なアダプター |

再帰変換の例：

```python
from datetime import date
from cells.json import safe_json_dumps

payload = safe_json_dumps(
    {"date": date(2026, 1, 1), "tags": {"python", "json"}},
    ensure_ascii=False,
    indent=2,
)
```

`safe_json_dumps()` はエンコード前に辞書のキーを文字列に、タプルと集合をリストに変換します。集合の要素順序は保証されません。JSON を再度読み込んでも、元の Python の型は復元されません。

## バックエンドの動作と互換性

アダプターのインターフェースは標準ライブラリの `json` に似ていますが、すべてのオプションや値について同一の動作を保証するものではありません。

- `backend="auto"` は、利用可能なら `orjson` を優先し、それ以外は標準ライブラリの `json` を使用します。
- `backend="orjson"` には `orjson` が必要です。未インストールの場合、アダプターの作成時に `RuntimeError` が発生します。
- `backend="json"` は標準ライブラリのエンコードとデコードを明示的に選択し、本ライブラリの拡張型コールバックも維持します。

未対応のオプションによってバックエンドが自動的に切り替わることはありません。標準ライブラリのパラメーター動作が必要な場合は、`backend="json"` を指定してください。

| オプション | `orjson` バックエンド使用時 |
| --- | --- |
| `ensure_ascii=True` | 対応。エンコード後に非 ASCII 文字をエスケープ。デフォルト値 |
| `sort_keys=True` | 対応 |
| `indent=2` | 対応。`None` 以外のほかの字下げ指定には `backend="json"` が必要 |
| `separators=(",", ":")` | 対応。ほかの明示的な区切り文字には `backend="json"` が必要 |
| `skipkeys=True` | エンコード前に未対応の辞書キーを除外 |
| `check_circular=False` | 受け付けるが、標準ライブラリと同じ循環参照の動作は保証しない |
| `allow_nan=False` | `backend="json"` が必要 |
| カスタムエンコーダー・デコーダーの `cls` | `backend="json"` が必要 |
| `object_hook`、`object_pairs_hook`、`parse_float`、`parse_int`、`parse_constant` | `backend="json"` が必要 |

たとえば、解析時に十進数の値を保持する場合は、標準ライブラリのバックエンドを使用します。

```python
from decimal import Decimal
from cells.json import dumps, loads

payload = dumps({"b": 1, "a": 2}, sort_keys=True, indent=2)
data = loads('{"amount": 19.95}', parse_float=Decimal, backend="json")

assert data["amount"] == Decimal("19.95")
```

非有限数、整数の範囲、辞書キーに対するバックエンド固有の動作も異なる場合があります。これらがデータの契約に関わる場合は、バックエンドを明示的に選択してください。

## 対応する型変換

次の表は `UniversalSerializer` と再帰 API の変換ルールです。アダプターは、`orjson` が既に対応している型には、そのバックエンドのネイティブ処理を使用する場合があります。

| Python の型 | JSON 表現 |
| --- | --- |
| `datetime`、`date`、`time` | ISO 形式の文字列 |
| `timedelta` | 合計秒数を表す数値 |
| `Decimal` | 浮動小数点数 |
| `UUID` | 文字列 |
| `Enum` | その `value` をさらにシリアライズ |
| `Path` | POSIX 形式のパス文字列 |
| `set`、`tuple` | 配列 |
| NumPy の `ndarray` / スカラー | 入れ子のリスト / Python のネイティブ値 |
| pandas の `DataFrame` | 行レコードの配列 |
| 名前付きの pandas `Series` | 文字列化した名前を値のリストに対応付けるオブジェクト |
| 名前のない pandas `Series` | インデックスと値のマッピング |
| カスタムオブジェクト | 設定に従い、`to_dict()`、`__dict__`、`__slots__` の順に使用 |

`Decimal` を `float` に変換すると、精度が失われる場合があります。十進数を正確に出力する必要がある場合は、`dumps()` に `default=str` などの変換関数を渡すか、シリアライズ前に値を文字列へ変換してください。

### カスタムオブジェクトと未対応の型

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

- `strict=True` は、`to_dict()` を含むカスタムオブジェクトの自動検査を無効にします。組み込みで対応している型変換は引き続き利用できます。
- `ignore_unknown=True` は、ほかの方法でも処理できない値を `null` に変換し、デフォルトで属性の検査を無効にします。厳密モードが無効なら、認識された `to_dict()` メソッドは引き続き使用できます。
- `use_dict=False` は `__dict__` と `__slots__` の検査を無効にします。厳密モードでなければ `to_dict()` は使用できます。
- `UniversalSerializer(default=callback)` は未対応の型に対するフォールバック変換を指定します。

適用できるフォールバックがない場合、未対応の型は `JSONEncodeError` を発生させます。属性の自動検査では内部属性も含まれる場合があります。出力フィールドを明示的に選択するには、`to_dict()` を定義するか、属性の検査を無効にしてください。

## 循環参照

循環参照を再帰的に処理する場合は、`safe_json_dumps()` を使用します。デフォルトでは循環参照を `"<CircularReference dict>"` などの文字列に置き換えます。`fail_on_circular=True` を指定すると `CircularReferenceError` を発生させます。

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

`UniversalSerializer.dumps()` はデフォルトでは再帰的な事前変換を行いません。`recursive=True` で有効にできます。アダプター API は、同じ再帰的なマーカー処理を提供しません。

`safe_json_dumps(ignore_errors=True, default_value="null")` は、このヘルパーが処理対象とするシリアライズ例外を捕捉した場合に、フォールバック文字列を返します。あらゆる例外を抑制するわけではありません。

## ファイルとユーティリティ

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

主要 API の `dump()` / `load()` は、開かれたストリームを操作します。UTF-8 のテキストストリームは両バックエンドで使用できます。`save_json()` は親ディレクトリを作成し、`UniversalSerializer` を使って UTF-8 で書き込みます。`load_json()` は UTF-8 で読み込み、標準ライブラリの `json` で解析します。

その他のヘルパー：

- `prettify_json(data, indent=2)`：`safe_json_dumps()` を使い、Python の値を字下げ付き JSON にシリアライズします。`cells.json` からもインポートできます。
- `JsonSerializable`：`to_dict()`、`to_json()`、`from_dict()` を提供する基底クラス。
- `@json_serializable`：同じメソッドをクラスに追加するデコレーター。

クラス用ヘルパーは `cells.json.utils` からインポートします。`from_dict()` は `cls(**data)` を呼び出します。日時、十進数などの元の型は自動的には復元しません。

## 例外処理

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

`JSONEncodeError` は `TypeError` を継承し、`CircularReferenceError` は `JSONEncodeError` のサブクラスです。`JSONDecodeError` は `ValueError` を継承し、`msg`、`doc`、`pos` を提供します。標準ライブラリの `json.JSONDecodeError` クラスとは異なります。

`orjson` 使用時の未対応のエンコードオプションは、`TypeError` でもある `JSONEncodeError` として報告されます。未対応のデコードオプションは `TypeError` を発生させます。これらのメッセージは `backend="json"` の使用を案内します。

## 開発と性能評価

ローカルのソースディレクトリで、Python 3.14 を使用します。

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest tests/test_serializer.py -v
```

NumPy または pandas が未インストールの場合、対応するテストは途中で終了します。これらの変換を検証するには、必要なパッケージを個別にインストールしてください。

同梱のベンチマークを実行するには：

```bash
python tests/test_performance.py
```

性能はデータ、バックエンド、変換経路、オプション、実行環境に依存します。このスクリプトはローカルでの比較用であり、一定の高速化率を保証するものではありません。

## ライセンス

パッケージメタデータには Mozilla Public License 2.0（`MPL-2.0`）が指定されています。
