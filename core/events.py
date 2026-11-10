"""任务事件：节点进度、阶段结果、完成 / 失败。

用“只追加的事件日志 + 游标”代替一次性队列：
    - 任意线程都能 emit（LLM 调用在线程池里跑，节点进度从那里发出来）；
    - 多个订阅者各自按游标读，互不抢事件；断线重连时带上 Last-Event-ID 就能从断点续读，不丢也不重。
"""
import asyncio
import threading
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

TERMINAL_TYPES = ("completed", "error")


class EventLog:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._changed: Optional[asyncio.Event] = None
        self._lock = threading.Lock()

    def bind(self) -> "EventLog":
        """在事件循环里调用一次，之后其他线程 emit 时才能唤醒等待中的订阅者。"""
        self._loop = asyncio.get_running_loop()
        self._changed = asyncio.Event()
        return self

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self.events.append({"type": event_type, "payload": payload or {}})
        loop, changed = self._loop, self._changed
        if loop is None or changed is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            changed.set()
        else:
            loop.call_soon_threadsafe(changed.set)

    async def read(self, cursor: int = 0, timeout: Optional[float] = None) -> Tuple[List[Dict[str, Any]], int]:
        """返回 cursor 之后的事件和新游标；没有新事件时最多等 timeout 秒（超时返回空列表）。"""
        if cursor >= len(self.events) and self._changed is not None:
            self._changed.clear()
            if cursor >= len(self.events):  # clear 之后再看一眼，避免错过刚 emit 的事件
                try:
                    await asyncio.wait_for(self._changed.wait(), timeout)
                except asyncio.TimeoutError:
                    return [], cursor
        new = self.events[cursor:]
        return new, cursor + len(new)

    async def stream(self, cursor: int = 0, keepalive: float = 15.0) -> AsyncIterator[Tuple[int, Optional[Dict[str, Any]]]]:
        """逐条产出 (事件序号, 事件)；空闲超过 keepalive 秒产出 (序号, None) 供上层发心跳。遇到终止事件后结束。"""
        while True:
            new, nxt = await self.read(cursor, keepalive)
            if not new:
                yield cursor, None
                continue
            for offset, ev in enumerate(new, start=1):
                yield cursor + offset, ev
                if ev.get("type") in TERMINAL_TYPES:
                    return
            cursor = nxt


def emit(shared: Dict[str, Any], event_type: str, payload: Dict[str, Any]) -> None:
    """节点里发进度事件。shared 里没有事件日志（如离线测试）时什么都不做。"""
    sink = shared.get("events")
    if sink is not None:
        sink.emit(event_type, payload)
