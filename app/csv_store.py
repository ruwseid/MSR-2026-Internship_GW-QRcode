"""CSVファイルへの読み書きを担当します。

教材用に処理を分け、Web画面やカメラ処理がCSVの細部を知らなくてもよい構成にしています。
"""

import csv
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models import Record

CSV_COLUMNS = ["id", "qr_text", "read_at", "source"]
# 日本には夏時間がなく、UTCとの差は常に+9時間です。
# ZoneInfo("Asia/Tokyo")はWindowsで別途tzdataが必要になるため、
# この最小構成サンプルでは標準ライブラリだけで表現できる固定オフセットを使います。
JST = timezone(timedelta(hours=9), name="JST")


class CsvStore:
    """小規模な演習用CSVストア。

    FastAPIのリクエスト処理とカメラスレッドが同時にアクセスする可能性があるため、
    Lockを使い、1回に1つの処理だけがCSVを触るようにします。
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._prepare_file()

    def _prepare_file(self) -> None:
        """保存先ディレクトリとヘッダー行を初回だけ作ります。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            with self.path.open("w", newline="", encoding="utf-8-sig") as file:
                csv.DictWriter(file, fieldnames=CSV_COLUMNS).writeheader()

    def list_records(self) -> list[Record]:
        """画面表示用に全件を新しい順で返します。"""
        with self._lock:
            with self.path.open("r", newline="", encoding="utf-8-sig") as file:
                records = [Record(**row) for row in csv.DictReader(file)]
        return list(reversed(records))

    def add_record(self, qr_text: str, source: str) -> Record:
        """CSVの末尾へ1件追加し、追加したデータを返します。"""
        with self._lock:
            # 演習用のため、既存行数+1を単純なIDとして使います。
            with self.path.open("r", newline="", encoding="utf-8-sig") as file:
                next_id = sum(1 for _ in csv.DictReader(file)) + 1

            record = Record(
                id=next_id,
                qr_text=qr_text,
                read_at=datetime.now(JST).isoformat(timespec="seconds"),
                source=source,
            )

            # print(self.list_records())
            # if qr_text in self.list_records(): 
            #     return 

            with self.path.open("a", newline="", encoding="utf-8-sig") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
                writer.writerow(record.model_dump())
        return record
