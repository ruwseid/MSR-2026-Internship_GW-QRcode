"""FastAPIアプリケーションの入口です。"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.camera import CameraScanner
from app.config import (
    CAMERA_DEVICE_INDEX,
    CSV_PATH,
    QR_DUPLICATE_COOLDOWN_SECONDS,
    STATIC_DIR,
    TEMPLATE_DIR,
)
from app.csv_store import CsvStore
from app.events import EventBroker
from app.models import ManualRecordRequest, Record

logging.basicConfig(level=logging.INFO)

store = CsvStore(CSV_PATH)
broker = EventBroker()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def save_camera_result(qr_text: str, source: str) -> Record:
    """カメラスレッドから呼ばれ、CSV保存だけを担当します。"""
    return store.add_record(qr_text, source)


scanner = CameraScanner(
    camera_index=CAMERA_DEVICE_INDEX,
    cooldown_seconds=QR_DUPLICATE_COOLDOWN_SECONDS,
    on_detected=save_camera_result,
    on_saved=broker.publish_from_thread,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """サーバの開始・終了に合わせてカメラスレッドも開始・終了します。"""
    broker.bind_loop(asyncio.get_running_loop())
    scanner.start()
    yield
    scanner.stop()


app = FastAPI(title="QRコード受付サンプル", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """CSVを読み、Jinja2テンプレートへ渡して一覧画面を作ります。"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"records": store.list_records()},
    )


@app.get("/api/records", response_model=list[Record])
async def list_records(
    sort_by: Literal["id", "read_at"] = "read_at",
    order: Literal["asc", "desc"] = "desc",
    source: Literal["all", "camera", "manual"] = "all",
) -> list[Record]:
    """指定された条件で絞り込み・並べ替えた読取履歴を返します。"""
    return store.list_records(sort_by=sort_by, order=order, source=source)


@app.post("/api/records", response_model=Record, status_code=201)
async def create_record(request: ManualRecordRequest) -> Record:
    """カメラがない環境でも試せる手動登録APIです。"""
    record = store.add_record(request.qr_text.strip(), "manual")
    await broker.publish(record)
    return record


@app.get("/events")
async def events() -> StreamingResponse:
    """CSVへの追加をSSE形式でブラウザへ配信します。"""

    async def event_stream():
        async for record in broker.subscribe():
            # SSEは「data: JSON + 空行」という単純なテキスト形式です。
            data = json.dumps(record.model_dump(), ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
