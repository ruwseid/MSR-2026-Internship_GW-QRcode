"""アプリケーション全体で使う設定値をまとめます。"""

from pathlib import Path

# このファイルの2階層上がプロジェクトルートです。
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "records.csv"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

# 通常はPC内蔵カメラが 0 です。外付けカメラなら 1 などへ変更します。
CAMERA_DEVICE_INDEX = 0

# 同じQRコードをカメラへ向け続けても連続登録しないための待ち時間です。
QR_DUPLICATE_COOLDOWN_SECONDS = 5.0

