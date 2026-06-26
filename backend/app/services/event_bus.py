"""事件总线 —— 按 discussion_id 严格隔离的 SSE 事件分发系统。

底层原则：不同讨论之间的事件流完全隔离。
每个 discussion_id 拥有独立的 asyncio.Queue，事件仅进入目标讨论的队列。
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator


class EventBus:
    """基于 asyncio.Queue 的事件总线，按 discussion_id 隔离。

    使用方式：
        bus = EventBus()
        await bus.publish(discussion_id=1, event={...})
        async for event in bus.subscribe(discussion_id=1):
            # 只收到 discussion_id=1 的事件
            ...
    """

    def __init__(self):
        self._queues: dict[int, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def publish(self, discussion_id: int, event: dict) -> None:
        """向指定讨论发布一个事件。

        如果尚未有人订阅，自动创建队列避免事件丢失。
        """
        async with self._lock:
            queue = self._queues.get(discussion_id)
            if queue is None:
                queue = asyncio.Queue()
                self._queues[discussion_id] = queue
        await queue.put(event)

    def subscribe(self, discussion_id: int) -> asyncio.Queue:
        """订阅指定讨论的事件流，返回一个 asyncio.Queue。

        调用者应从此队列中异步读取事件。
        """
        if discussion_id not in self._queues:
            self._queues[discussion_id] = asyncio.Queue()
        return self._queues[discussion_id]

    def unsubscribe(self, discussion_id: int) -> None:
        """取消订阅并清理讨论的事件队列。"""
        self._queues.pop(discussion_id, None)

    async def event_stream(
        self, discussion_id: int, sentinel: object = None
    ) -> AsyncIterator[dict]:
        """为指定讨论创建异步事件流迭代器。

        当读取到 sentinel（默认 None）时停止迭代。
        用于 SSE 端点持续 yield 事件到前端。

        Args:
            discussion_id: 讨论 ID
            sentinel: 终止标记，读取到此值时停止迭代

        Yields:
            按 FIFO 顺序产出事件字典
        """
        queue = self.subscribe(discussion_id)
        try:
            while True:
                event = await queue.get()
                if event is sentinel:
                    break
                yield event
        finally:
            self.unsubscribe(discussion_id)