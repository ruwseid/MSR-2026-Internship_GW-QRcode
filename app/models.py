"""アプリケーション内で扱うデータ構造を定義します。"""

from pydantic import BaseModel, Field


class Record(BaseModel):
    """CSVに保存する1件分の読取記録です。"""

    id: int
    qr_text: str
    read_at: str
    source: str


class ManualRecordRequest(BaseModel):
    """動作確認用の手動登録APIが受け取るJSONです。"""

    qr_text: str = Field(min_length=1, max_length=500)

