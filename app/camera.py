"""バックグラウンドでカメラ画像からQRコードを読み取ります。"""

import logging
import threading
import time
from collections.abc import Callable
from urllib.parse import unquote

import cv2
import os


from app.models import Record

from app.csv_store import CsvStore

from pathlib import Path
from app.config import CSV_PATH

logger = logging.getLogger(__name__)


class CameraScanner:
    """FastAPIとは別のスレッドでOpenCVの読取ループを動かします。"""

    def __init__(
        self,
        camera_index: int,
        cooldown_seconds: float,
        on_detected: Callable[[str, str], Record],
        on_saved: Callable[[Record], None],
    ) -> None:
        self.camera_index = camera_index
        self.cooldown_seconds = cooldown_seconds
        self.on_detected = on_detected
        self.on_saved = on_saved
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_text = ""
        self._last_detected_at = 0.0
        self._read_fail_count = 0
        self._last_read_log_at = 0.0

    def start(self) -> None:
        """デーモンスレッドを開始します。すでに起動中なら何もしません。"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """サーバ終了時に読取ループを止めます。"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _scan_loop(self) -> None:
        
        os.environ["NO_PROXY"] = "192.168.0.90"
        os.environ["no_proxy"] = "192.168.0.90"

        # URLによりIPカメラのフレームを指定して取り込む
        capture = cv2.VideoCapture("http://root:DXPort_pass@192.168.0.90/axis-cgi/mjpg/video.cgi")
        # capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)  USBカメラを使う場合はこちら

        if not capture.isOpened():
            logger.warning("カメラを開けません。手動登録APIは引き続き利用できます。")
            capture.release()
            return

        detector = cv2.QRCodeDetector()
        logger.info("QRコードのカメラ読取を開始しました。 camera_index=%s", self.camera_index)
        try:
            while not self._stop_event.is_set():
                success, frame = capture.read()
                if not success or frame is None or frame.size == 0:
                    self._log_read_failure(frame)
                    time.sleep(0.1)
                    continue

                self._log_read_success(frame)

                try:
                    qr_text, _points, _straight = detector.detectAndDecode(frame)
                except cv2.error as error:
                    # QRコードの輪郭候補が壊れているフレームなどでは、OpenCV内部が
                    # cv2.errorを送出することがあります。カメラ処理全体を止めず、
                    # 問題の1フレームだけを読み飛ばして次の画像を処理します。
                    logger.warning("QR解析に失敗したフレームを読み飛ばします: %s", error)
                    time.sleep(0.1)
                    continue
                        
                # HACK 同じQRコードを読んだ場合は5秒沈黙を一旦無効化
                # if qr_text and not self._is_duplicate(qr_text):
                if qr_text :
                    normalized_qr_text = self._normalize_qr_text(qr_text)
                    logger.info(
                        "QR読取結果: raw=%r normalized=%r",
                        qr_text,
                        normalized_qr_text,
                    )

                    f = open(CSV_PATH, encoding="utf-8-sig")
                    s = f.read()
                    f.close()
                    if normalized_qr_text not in s:
                        record = self.on_detected(normalized_qr_text, "camera")
                        self.on_saved(record)
                    

                time.sleep(0.05)  # CPU使用率が上がりすぎないよう短く待機します。
        finally:
            capture.release()
            logger.info("QRコードのカメラ読取を終了しました。")

    def _log_read_failure(self, frame) -> None:
        self._read_fail_count += 1
        if self._read_fail_count == 1 or self._read_fail_count % 10 == 0:
            frame_info = "frame=None"
            if frame is not None:
                frame_info = f"frame.shape={getattr(frame, 'shape', 'unknown')}, frame.size={getattr(frame, 'size', 'unknown')}"
            logger.warning(
                "カメラフレーム取得失敗: count=%s, camera_index=%s, %s",
                self._read_fail_count,
                self.camera_index,
                frame_info,
            )

    def _log_read_success(self, frame) -> None:
        now = time.monotonic()
        if self._read_fail_count > 0:
            logger.info(
                "カメラフレーム取得回復: previous_fail_count=%s, camera_index=%s, frame.shape=%s",
                self._read_fail_count,
                self.camera_index,
                getattr(frame, "shape", "unknown"),
            )
            self._read_fail_count = 0
            self._last_read_log_at = now
            return

        if now - self._last_read_log_at >= 10:
            # logger.info(
            #     "カメラフレーム取得正常: camera_index=%s, frame.shape=%s",
            #     self.camera_index,
            #     getattr(frame, "shape", "unknown"),
            # )
            self._last_read_log_at = now

    def _normalize_qr_text(self, qr_text: str) -> str:
        """OpenCVが返した文字列をアプリ向けに正規化します。"""
        if "%" in qr_text:
            try:
                decoded = unquote(qr_text, encoding="utf-8", errors="strict")
                if decoded != qr_text:
                    logger.info("URLエンコードされたQR文字列をUTF-8として復元しました。")
                    return decoded
            except UnicodeDecodeError:
                logger.warning("URLデコードに失敗しました。生文字列をそのまま使います。 raw=%r", qr_text)

        mojibake_fixed = self._try_decode_shift_jis_mojibake(qr_text)
        if mojibake_fixed is not None:
            logger.info("Shift_JIS文字化けを復元しました。 restored=%r", mojibake_fixed)
            return mojibake_fixed

        return qr_text

    def _try_decode_shift_jis_mojibake(self, qr_text: str) -> str | None:
        """Shift_JISのバイト列が誤って文字列化された値を復元します。"""
        try:
            raw_bytes = qr_text.encode("latin-1")
        except UnicodeEncodeError:
            return None

        for encoding in ("cp932", "shift_jis"):
            try:
                restored = raw_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
            if self._looks_like_valid_restored_text(restored):
                return restored
        return None

    def _looks_like_valid_restored_text(self, text: str) -> bool:
        """復元結果が人間向け文字列らしいかを緩く判定します。"""
        if not text or any(ord(char) < 32 and char not in "\r\n\t" for char in text):
            return False
        return any(ord(char) > 127 for char in text)

    def _is_duplicate(self, qr_text: str) -> bool:
        now = time.monotonic()
        duplicate = (
            qr_text == self._last_text
            and now - self._last_detected_at < self.cooldown_seconds
        )
        if not duplicate:
            self._last_text = qr_text
            self._last_detected_at = now
        return duplicate
