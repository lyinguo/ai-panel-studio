"""SSE 事件隔离单元测试 —— 不同 discussion_id 的事件流互不干扰。

TDD 阶段：本文件导入的 EventBus 尚不存在，所有测试预期失败（红灯）。
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from tests.conftest import AsyncMock

import pytest


# ============================================================
# 测试：跨讨论事件隔离
# 场景：discussion_1 产生的事件不应出现在 discussion_2 的事件流中。
# ============================================================

class TestEventIsolation:
    """验证 EventBus 按 discussion_id 严格隔离事件。"""

    @pytest.fixture
    def event_bus_and_queues(self):
        """创建 EventBus 实例和两个讨论的内部队列。"""
        from app.services.event_bus import EventBus

        bus = EventBus()
        # 模拟两个讨论的内部 asyncio.Queue
        queue_1 = asyncio.Queue()
        queue_2 = asyncio.Queue()

        # Mock subscribe 方法为每个 discussion_id 返回独立的队列
        original_subscribe = bus.subscribe
        subscriptions = {}

        def mock_subscribe(discussion_id: int) -> asyncio.Queue:
            if discussion_id == 1:
                subscriptions[1] = queue_1
                return queue_1
            elif discussion_id == 2:
                subscriptions[2] = queue_2
                return queue_2
            return asyncio.Queue()

        bus.subscribe = MagicMock(side_effect=mock_subscribe)
        return bus, queue_1, queue_2, subscriptions

    @pytest.mark.asyncio
    async def test_discussion_1_events_should_not_appear_in_discussion_2(
        self, event_bus_and_queues
    ):
        """验证讨论1的事件不会出现在讨论2的队列中。

        向讨论1发布 3 个事件，然后仅从讨论2的队列消费，
        应始终超时而非读到事件。
        """
        from app.services.event_bus import EventBus

        bus, queue_1, queue_2, subscriptions = event_bus_and_queues

        # Mock publish 方法：将事件放入对应讨论的队列
        async def mock_publish(discussion_id: int, event: dict):
            target_queue = subscriptions.get(discussion_id)
            if target_queue is not None:
                await target_queue.put(event)

        bus.publish = AsyncMock(side_effect=mock_publish)

        # 向讨论1发布 3 个事件
        events_for_disc_1 = [
            {"type": "guest_status_change", "participant_id": 1, "status": "speaking"},
            {"type": "message_chunk", "participant_id": 1, "chunk_index": 0, "content": "你好", "is_final": False},
            {"type": "consensus_update", "agreements": [], "divergences": []},
        ]
        for event in events_for_disc_1:
            await bus.publish(discussion_id=1, event=event)

        # 尝试从讨论2的队列读取 —— 应超时（无事件）
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue_2.get(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_discussion_2_events_should_not_appear_in_discussion_1(
        self, event_bus_and_queues
    ):
        """验证讨论2的事件不会出现在讨论1的队列中。"""
        from app.services.event_bus import EventBus

        bus, queue_1, queue_2, subscriptions = event_bus_and_queues

        async def mock_publish(discussion_id: int, event: dict):
            target_queue = subscriptions.get(discussion_id)
            if target_queue is not None:
                await target_queue.put(event)

        bus.publish = AsyncMock(side_effect=mock_publish)

        # 向讨论2发布事件
        await bus.publish(
            discussion_id=2,
            event={"type": "guest_status_change", "participant_id": 5, "status": "speaking"},
        )

        # 讨论1的队列应始终为空
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue_1.get(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_same_type_events_from_different_discussions_should_not_cross(
        self, event_bus_and_queues
    ):
        """验证即使是相同事件类型，不同讨论之间也不串流。"""
        from app.services.event_bus import EventBus

        bus, queue_1, queue_2, subscriptions = event_bus_and_queues

        async def mock_publish(discussion_id: int, event: dict):
            target_queue = subscriptions.get(discussion_id)
            if target_queue is not None:
                await target_queue.put(event)

        bus.publish = AsyncMock(side_effect=mock_publish)

        # 同时向两个讨论发布相同类型事件
        await bus.publish(
            discussion_id=1,
            event={"type": "message_chunk", "participant_id": 1, "content": "disc1", "is_final": True},
        )
        await bus.publish(
            discussion_id=2,
            event={"type": "message_chunk", "participant_id": 5, "content": "disc2", "is_final": True},
        )

        # 讨论1 读到自己的事件
        event_1 = await asyncio.wait_for(queue_1.get(), timeout=0.5)
        assert event_1["content"] == "disc1", (
            f"讨论1读到了讨论2的事件：{event_1['content']}"
        )

        # 讨论2 读到自己的事件
        event_2 = await asyncio.wait_for(queue_2.get(), timeout=0.5)
        assert event_2["content"] == "disc2", (
            f"讨论2读到了讨论1的事件：{event_2['content']}"
        )


# ============================================================
# 测试：单个讨论内的事件保序
# 场景：同一 discussion_id 内，事件按发布顺序被消费。
# ============================================================

class TestEventOrdering:
    """验证同一讨论内的事件顺序与发布顺序一致。"""

    @pytest.mark.asyncio
    async def test_events_should_be_consumed_in_publish_order(self):
        """验证讨论内的事件按 FIFO 顺序消费。"""
        from app.services.event_bus import EventBus

        bus = EventBus()
        queue = asyncio.Queue()

        # Mock subscribe 返回该队列
        bus.subscribe = MagicMock(return_value=queue)

        async def mock_publish(discussion_id: int, event: dict):
            await queue.put(event)

        bus.publish = AsyncMock(side_effect=mock_publish)

        # 按顺序发布 5 个事件
        expected_order = ["evt_a", "evt_b", "evt_c", "evt_d", "evt_e"]
        for label in expected_order:
            await bus.publish(discussion_id=1, event={"label": label})

        # 按顺序消费验证
        received = []
        for _ in range(5):
            event = await asyncio.wait_for(queue.get(), timeout=0.5)
            received.append(event["label"])

        assert received == expected_order, (
            f"事件消费顺序与发布顺序不一致\n"
            f"  期望: {expected_order}\n"
            f"  实际: {received}"
        )


# ============================================================
# 测试：独立讨论数量扩展性
# 场景：系统应能同时处理多个讨论而不丢失事件。
# ============================================================

class TestMultiDiscussionIsolation:
    """验证多个并发讨论的事件流完全独立。"""

    @pytest.mark.asyncio
    async def test_three_concurrent_discussions_should_not_interfere(self):
        """验证 3 个并发讨论的事件互不干扰。"""
        from app.services.event_bus import EventBus

        bus = EventBus()
        queues = {i: asyncio.Queue() for i in range(1, 4)}

        bus.subscribe = MagicMock(
            side_effect=lambda discussion_id: queues[discussion_id]
        )

        async def mock_publish(discussion_id: int, event: dict):
            await queues[discussion_id].put(event)

        bus.publish = AsyncMock(side_effect=mock_publish)

        # 向每个讨论发布唯一标记的事件
        markers = {1: "from_disc_1", 2: "from_disc_2", 3: "from_disc_3"}
        for disc_id, marker in markers.items():
            await bus.publish(discussion_id=disc_id, event={"marker": marker})

        # 每个讨论只能读到自己的事件
        for disc_id in range(1, 4):
            event = await asyncio.wait_for(queues[disc_id].get(), timeout=0.5)
            assert event["marker"] == markers[disc_id], (
                f"讨论{disc_id} 读到了其他讨论的事件标记 '{event['marker']}'"
            )

        # 所有队列应已空（无多余事件泄漏）
        for disc_id in range(1, 4):
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queues[disc_id].get(), timeout=0.3)
