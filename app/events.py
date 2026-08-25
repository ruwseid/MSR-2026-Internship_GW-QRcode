"""Server-Sent Events (SSE) でブラウザへ更新を知らせます。"""

import asyncio

from app.models import Record


class EventBroker:
    """接続中のブラウザごとに通知用キューを用意する簡易ブローカーです。"""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[Record]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """カメラスレッドからメインのイベントループへ通知するため保存します。"""
        self._loop = loop

    async def subscribe(self):
        """ブラウザ接続中だけキューを登録し、切断時には必ず削除します。"""
        queue: asyncio.Queue[Record] = asyncio.Queue(maxsize=10)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    async def publish(self, record: Record) -> None:
        """すべての接続中ブラウザへ同じ読取結果を配ります。"""
        for queue in tuple(self._subscribers):
            if not queue.full():
                queue.put_nowait(record)

    def publish_from_thread(self, record: Record) -> None:
        """OpenCVの別スレッドから安全に非同期通知を予約します。"""
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.publish(record), self._loop)

