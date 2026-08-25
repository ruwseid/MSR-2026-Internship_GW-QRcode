from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.camera import CameraScanner
from app.csv_store import CsvStore
from app.main import app


def test_csv_store_add_and_list(tmp_path: Path) -> None:
    store = CsvStore(tmp_path / "records.csv")
    saved = store.add_record("TEST-001", "test")

    assert saved.id == 1
    assert store.list_records()[0].qr_text == "TEST-001"


def test_index_page_is_displayed() -> None:
    # lifespanを起動しない書き方にして、テスト時は実カメラへ接続しません。
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "QRコード受付" in response.text


def test_camera_scanner_survives_opencv_error() -> None:
    """1フレームのQR解析失敗でカメラスレッド全体が異常終了しないことを確認します。"""
    capture = MagicMock()
    capture.isOpened.return_value = True
    capture.read.side_effect = [
        (True, np.zeros((10, 10, 3), dtype=np.uint8)),
        (False, None),
    ]

    scanner = CameraScanner(0, 5.0, MagicMock(), MagicMock())

    def stop_after_error(_seconds: float) -> None:
        scanner._stop_event.set()

    with (
        patch("app.camera.cv2.VideoCapture", return_value=capture),
        patch(
            "app.camera.cv2.QRCodeDetector.detectAndDecode",
            side_effect=cv2.error("QR解析エラー"),
        ),
        patch("app.camera.time.sleep", side_effect=stop_after_error),
    ):
        scanner._scan_loop()

    capture.release.assert_called_once()


def test_camera_scanner_normalize_qr_text_restores_shift_jis_mojibake() -> None:
    scanner = CameraScanner(0, 5.0, MagicMock(), MagicMock())

    mojibake_text = "\x82±\x82ê\x82Í\x83T\x83C\x83g\x82Å\x90¶\x90¬\x82µ\x82½QR\x83R\x81[\x83h\x82Å\x82·"

    assert scanner._normalize_qr_text(mojibake_text) == "これはサイトで生成したQRコードです"


def test_camera_scanner_normalize_qr_text_keeps_ascii_text() -> None:
    scanner = CameraScanner(0, 5.0, MagicMock(), MagicMock())

    assert scanner._normalize_qr_text("4969757163214") == "4969757163214"
