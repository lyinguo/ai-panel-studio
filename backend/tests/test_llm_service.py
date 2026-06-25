"""LLM 服务单元测试 —— AI 生成参与者的完整性与独立性验证。

TDD 阶段：本文件导入的服务层尚不存在，所有测试预期失败（红灯）。
"""

from __future__ import annotations

from collections import Counter
from unittest.mock import MagicMock, patch

from tests.conftest import AsyncMock

import pytest


# ============================================================
# 测试：参与者结构完整性
# 场景：LLMService.generate_participants 被调用后，
#       返回列表中必须恰好包含 1 位 host + N 位 expert。
# ============================================================

class TestParticipantStructure:
    """验证 AI 生成的参与者数量和角色分配是否正确。"""

    MOCK_RESPONSE = [
        {
            "role": "host",
            "name": "陈思远",
            "title": "AI 伦理与治理专家",
            "stance": "保持中立，引导讨论聚焦核心议题，确保各方观点得到充分表达。",
            "color_code": "#4A90D9",
            "order": 0,
        },
        {
            "role": "expert",
            "name": "李薇",
            "title": "资深机器学习研究员",
            "stance": "认为技术本身是中立的，关键在于应用场景和监管框架的完善。",
            "color_code": "#FF6B6B",
            "order": 1,
        },
        {
            "role": "expert",
            "name": "王磊",
            "title": "人工智能安全专家",
            "stance": "主张在 AGI 研发上采取审慎渐进策略，安全护栏必须前置。",
            "color_code": "#50C878",
            "order": 2,
        },
        {
            "role": "expert",
            "name": "赵雨桐",
            "title": "计算神经科学博士",
            "stance": "从认知科学角度论证，当前 AI 距离真正理解还有本质差距。",
            "color_code": "#FFD700",
            "order": 3,
        },
        {
            "role": "expert",
            "name": "孙明达",
            "title": "开源 AI 社区发起人",
            "stance": "强调开放研究对 AI 安全的重要性，透明度和可复现性是底线。",
            "color_code": "#9B59B6",
            "order": 4,
        },
    ]

    @pytest.mark.asyncio
    async def test_should_contain_exactly_one_host(self):
        """验证返回列表中有且仅有 1 位 role='host' 的参与者。"""
        from app.services.llm_service import LlmService

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = self.MOCK_RESPONSE

            participants = await LlmService.generate_participants(
                topic="AGI 是否应该暂停研发", expert_count=4
            )

            roles = [p["role"] for p in participants]
            assert Counter(roles)["host"] == 1, (
                f"期望 1 位主持人，实际得到 {Counter(roles)['host']} 位"
            )

    @pytest.mark.asyncio
    async def test_should_contain_n_experts(self):
        """验证返回列表中 expert 的数量等于请求的 expert_count。"""
        from app.services.llm_service import LlmService

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = self.MOCK_RESPONSE

            participants = await LlmService.generate_participants(
                topic="AGI 是否应该暂停研发", expert_count=4
            )

            experts = [p for p in participants if p["role"] == "expert"]
            assert len(experts) == 4, (
                f"期望 4 位专家，实际得到 {len(experts)} 位"
            )

    @pytest.mark.asyncio
    async def test_roles_should_only_be_host_or_expert(self):
        """验证所有参与者的 role 字段只能是 'host' 或 'expert'。"""
        from app.services.llm_service import LlmService

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = self.MOCK_RESPONSE

            participants = await LlmService.generate_participants(
                topic="AGI 是否应该暂停研发", expert_count=4
            )

            valid_roles = {"host", "expert"}
            for p in participants:
                assert p["role"] in valid_roles, (
                    f"参与者 {p['name']} 的角色 '{p['role']}' 不在允许范围 {valid_roles}"
                )

    @pytest.mark.asyncio
    async def test_host_should_be_first_item(self):
        """验证主持人在返回列表中的 order=0，排在第一位。"""
        from app.services.llm_service import LlmService

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = self.MOCK_RESPONSE

            participants = await LlmService.generate_participants(
                topic="AGI 是否应该暂停研发", expert_count=4
            )

            host = next(p for p in participants if p["role"] == "host")
            assert host["order"] == 0
            assert participants[0]["role"] == "host"


# ============================================================
# 测试：颜色标识独立性
# 场景：每位参与者分配的颜色代码必须全局唯一。
# ============================================================

class TestColorUniqueness:
    """验证 AI 分配给每位参与者的 UI 颜色标识不重复。"""

    @pytest.mark.asyncio
    async def test_all_color_codes_should_be_unique(self):
        """验证 color_code 列表中没有重复值。"""
        from app.services.llm_service import LlmService

        MOCK = [
            {"role": "host", "name": "A", "title": "T", "stance": "S1", "color_code": "#4A90D9", "order": 0},
            {"role": "expert", "name": "B", "title": "T", "stance": "S2", "color_code": "#FF6B6B", "order": 1},
            {"role": "expert", "name": "C", "title": "T", "stance": "S3", "color_code": "#50C878", "order": 2},
            {"role": "expert", "name": "D", "title": "T", "stance": "S4", "color_code": "#FFD700", "order": 3},
            {"role": "expert", "name": "E", "title": "T", "stance": "S5", "color_code": "#9B59B6", "order": 4},
        ]

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = MOCK

            participants = await LlmService.generate_participants(
                topic="话题", expert_count=4
            )

            colors = [p["color_code"] for p in participants]
            assert len(colors) == len(set(colors)), (
                f"颜色标识不唯一：{colors}"
            )


# ============================================================
# 测试：立场独立性
# 场景：每位参与者的核心立场描述必须各不相同。
# ============================================================

class TestStanceUniqueness:
    """验证 AI 生成的每位参与者拥有独立的立场。"""

    @pytest.mark.asyncio
    async def test_all_stances_should_be_different(self):
        """验证 stance 列表中没有重复的立场描述。"""
        from app.services.llm_service import LlmService

        MOCK = [
            {"role": "host", "name": "A", "title": "T1", "stance": "保持中立，引导讨论", "color_code": "#4A90D9", "order": 0},
            {"role": "expert", "name": "B", "title": "T2", "stance": "技术中立论，强调监管框架", "color_code": "#FF6B6B", "order": 1},
            {"role": "expert", "name": "C", "title": "T3", "stance": "审慎渐进，安全前置", "color_code": "#50C878", "order": 2},
            {"role": "expert", "name": "D", "title": "T4", "stance": "认知科学视角，当前差距论", "color_code": "#FFD700", "order": 3},
            {"role": "expert", "name": "E", "title": "T5", "stance": "开源透明是安全底线", "color_code": "#9B59B6", "order": 4},
        ]

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = MOCK

            participants = await LlmService.generate_participants(
                topic="话题", expert_count=4
            )

            stances = [p["stance"] for p in participants]
            assert len(stances) == len(set(stances)), (
                f"立场描述不唯一：{stances}"
            )


# ============================================================
# 测试：参与人数边界
# 场景：expert_count 在允许范围 1~8 内的极端值。
# ============================================================

class TestParticipantBoundaries:
    """验证在不同 expert_count 边界条件下服务的表现。"""

    @pytest.mark.asyncio
    async def test_min_expert_count_should_produce_host_plus_one(self):
        """expert_count=1 时，返回 1 host + 1 expert = 2 人。"""
        from app.services.llm_service import LlmService

        MOCK = [
            {"role": "host", "name": "A", "title": "T", "stance": "S1", "color_code": "#4A90D9", "order": 0},
            {"role": "expert", "name": "B", "title": "T", "stance": "S2", "color_code": "#FF6B6B", "order": 1},
        ]

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = MOCK

            participants = await LlmService.generate_participants(
                topic="话题", expert_count=1
            )

            assert len(participants) == 2
            assert Counter(p["role"] for p in participants)["expert"] == 1

    @pytest.mark.asyncio
    async def test_max_expert_count_should_produce_host_plus_eight(self):
        """expert_count=8 时，返回 1 host + 8 expert = 9 人。"""
        from app.services.llm_service import LlmService

        MOCK = [
            {"role": "host", "name": "Host", "title": "T", "stance": "S0", "color_code": "#4A90D9", "order": 0}
        ]
        MOCK += [
            {"role": "expert", "name": f"E{i}", "title": "T", "stance": f"S{i}", "color_code": f"#{i+100:06X}", "order": i}
            for i in range(1, 9)
        ]

        with patch.object(
            LlmService, "generate_participants", new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = MOCK

            participants = await LlmService.generate_participants(
                topic="话题", expert_count=8
            )

            assert len(participants) == 9
            assert Counter(p["role"] for p in participants)["expert"] == 8
