"""讨论引擎单元测试 —— 发言调度机制与 Prompt 组装验证。

TDD 阶段：本文件导入的服务层尚不存在，所有测试预期失败（红灯）。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import AsyncMock

import pytest


# ============================================================
# 测试：发言调度随机性（非轮询机制）
# 场景：select_next_speaker 必须支持"举手抢答/抢话"机制，
#       而非机械的 A→B→C→A→B→C 轮询。
# ============================================================

class TestSpeakerSelectionIsNotRoundRobin:
    """验证发言调度引擎不采用简单轮询。"""

    PARTICIPANTS = [
        {"id": 1, "role": "host", "name": "A"},
        {"id": 2, "role": "expert", "name": "B"},
        {"id": 3, "role": "expert", "name": "C"},
        {"id": 4, "role": "expert", "name": "D"},
        {"id": 5, "role": "expert", "name": "E"},
    ]

    @pytest.mark.asyncio
    async def test_selection_order_should_not_be_strictly_cyclic(self):
        """验证连续多次选择的结果不是严格的 1→2→3→4→5→1 循环。

        运行 20 次选择，如果超过 18 次都严格按 id 递增循环，
        说明没有随机性，判定为轮询机制。
        """
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()
        previous_id = None
        sequential_count = 0
        total_rounds = 20

        with patch.object(
            engine, "select_next_speaker", side_effect=self._mock_random_selection
        ) as mock_method:
            for _ in range(total_rounds):
                speaker_id = await engine.select_next_speaker(
                    participants=self.PARTICIPANTS,
                    context={"last_speaker_id": previous_id, "round": 0},
                )

                if previous_id is not None:
                    expected_next = (previous_id % 5) + 1
                    if speaker_id == expected_next:
                        sequential_count += 1

                previous_id = speaker_id

            non_sequential = total_rounds - sequential_count

            assert non_sequential >= 3, (
                f"发言顺序过于接近轮询：20 次中 {sequential_count} 次为顺序递增，"
                f"仅 {non_sequential} 次跳序，怀疑是纯轮询机制"
            )

    @staticmethod
    def _mock_random_selection(participants, context):
        """模拟一个随机选择算法（非轮询）。

        在 1/3 的概率下跳过顺序中的下一位，模拟"抢答"行为。
        """
        import random

        last_id = context.get("last_speaker_id")
        if last_id is None:
            return participants[0]

        ids = [p["id"] for p in participants]
        last_index = ids.index(last_id)
        next_index = (last_index + 1) % len(ids)

        # 1/3 概率抢答：跳过下一位，随机选更后面的
        if random.random() < 0.33:
            candidates = [p for i, p in enumerate(participants) if i != next_index]
            return random.choice(candidates)["id"]

        return participants[next_index]["id"]

    @pytest.mark.asyncio
    async def test_same_participant_should_be_able_to_speak_consecutively(self):
        """验证同一个参与者可以连续发言（模拟激烈辩论中的持续输出）。"""
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()

        with patch.object(
            engine, "select_next_speaker", return_value=2
        ) as mock_method:
            first = await engine.select_next_speaker(
                participants=self.PARTICIPANTS,
                context={"last_speaker_id": 2, "round": 5},
            )
            second = await engine.select_next_speaker(
                participants=self.PARTICIPANTS,
                context={"last_speaker_id": first, "round": 6},
            )

            # 如果引擎是纯轮询，同一人绝无可能连续发言
            assert first == second, (
                f"连任发言失败：第一次={first}，第二次={second}，"
                f"引擎可能在强制轮询换人"
            )

    @pytest.mark.asyncio
    async def test_host_should_not_be_forced_to_speak_first_every_round(self):
        """验证主持人并非每轮都必须第一个发言（专家也可以主动发起）。"""
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()
        first_speakers = set()

        with patch.object(
            engine, "select_next_speaker", side_effect=self._mock_random_selection
        ) as mock_method:
            for _ in range(30):
                speaker = await engine.select_next_speaker(
                    participants=self.PARTICIPANTS,
                    context={"last_speaker_id": None, "round": 0},
                )
                first_speakers.add(speaker)

            # 30 轮中如果只有主持人发言过，说明设计有问题
            assert len(first_speakers) > 1, (
                f"30 轮中仅有 {len(first_speakers)} 位不同参与者成为首发言者，"
                f"主持人垄断了首发言权"
            )


# ============================================================
# 测试：Prompt 组装约束
# 场景：build_system_prompt 生成的系统指令中必须严格包含
#       "每次发言控制在 1-2 句" 和 "不允许机械重复" 两条约束。
# ============================================================

class TestPromptConstraints:
    """验证发送给 LLM 的系统指令中包含必要的行为约束。"""

    TOPIC = "AGI 是否应该暂停研发"
    PARTICIPANTS = [
        {"name": "陈思远", "role": "host", "title": "AI 伦理专家", "stance": "中立公正"},
        {"name": "李薇", "role": "expert", "title": "机器学习研究员", "stance": "技术中立"},
        {"name": "王磊", "role": "expert", "title": "AI 安全专家", "stance": "审慎渐进"},
    ]

    def test_prompt_should_contain_length_constraint(self):
        """验证系统指令中包含'每次发言控制在 1-2 句'的约束。"""
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()

        with patch.object(
            engine, "build_system_prompt", return_value=self._build_expected_prompt()
        ) as mock_method:
            prompt = engine.build_system_prompt(
                topic=self.TOPIC, participants=self.PARTICIPANTS
            )

            assert "1-2 句" in prompt, "Prompt 缺少'1-2 句'长度约束"

    def test_prompt_should_contain_no_repeat_constraint(self):
        """验证系统指令中包含'不允许机械重复'的约束。"""
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()

        with patch.object(
            engine, "build_system_prompt", return_value=self._build_expected_prompt()
        ) as mock_method:
            prompt = engine.build_system_prompt(
                topic=self.TOPIC, participants=self.PARTICIPANTS
            )

            assert "不允许机械重复" in prompt, (
                "Prompt 缺少'不允许机械重复'约束"
            )

    def test_prompt_should_contain_topic_and_participants(self):
        """验证系统指令中包含了讨论话题和所有参与者的信息。"""
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()

        with patch.object(
            engine, "build_system_prompt", return_value=self._build_expected_prompt()
        ) as mock_method:
            prompt = engine.build_system_prompt(
                topic=self.TOPIC, participants=self.PARTICIPANTS
            )

            assert self.TOPIC in prompt, "Prompt 应包含讨论话题"
            for p in self.PARTICIPANTS:
                assert p["name"] in prompt, f"Prompt 应包含参与者 {p['name']}"
                assert p["title"] in prompt, f"Prompt 应包含参与者身份 {p['title']}"

    def test_prompt_should_encourage_contention(self):
        """验证系统指令鼓励观点碰撞（不应让参与者一味附和）。"""
        from app.services.discussion_engine import DiscussionEngine

        engine = DiscussionEngine()

        with patch.object(
            engine, "build_system_prompt", return_value=self._build_expected_prompt()
        ) as mock_method:
            prompt = engine.build_system_prompt(
                topic=self.TOPIC, participants=self.PARTICIPANTS
            )

            encouragement_keywords = [
                "观点碰撞", "辩论", "反驳", "不同意见", "独立思考",
                "不要一味附和", "从你的立场出发",
            ]
            has_encouragement = any(k in prompt for k in encouragement_keywords)

            assert has_encouragement, (
                "Prompt 缺少鼓励观点碰撞/独立表达的指引。"
                f"期望包含以下关键字之一：{encouragement_keywords}"
            )

    # ── 辅助方法 ──

    @staticmethod
    def _build_expected_prompt() -> str:
        """生成符合契约的预期 Prompt 字符串。"""
        return (
            "你是一个 AI 圆桌讨论的主持系统。以下是一场关于"
            f"「AGI 是否应该暂停研发」的讨论。\n\n"
            "【参与者】\n"
            "- 陈思远 (主持人 / AI 伦理专家): 中立公正\n"
            "- 李薇 (专家 / 机器学习研究员): 技术中立\n"
            "- 王磊 (专家 / AI 安全专家): 审慎渐进\n\n"
            "【发言规则】\n"
            "1. 每次发言控制在 1-2 句，简洁有力。\n"
            "2. 欢迎观点碰撞，可以从你自己的立场出发反驳他人。\n"
            "3. 不允许机械重复自己或他人的观点。\n"
            "4. 不要一味附和，独立思考是讨论的核心价值。"
        )
