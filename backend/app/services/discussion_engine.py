"""讨论引擎 —— 发言调度、Prompt 组装、完整讨论流编排。

核心原则：
1. 严禁硬编码轮询逻辑（A→B→C→A），全程由 AI 自主决策发言顺序
2. 每次发言限制 1-2 句
3. 周期性提炼共识与分歧
4. 所有事件通过 EventBus 推送到 SSE
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from app.services.event_bus import EventBus
from app.services.llm_service import LlmService


# ============================================================
# 调度引擎
# ============================================================

class DiscussionEngine:
    """讨论引擎：负责发言调度与 Prompt 组装。

    发言调度机制：
    - 首次发言始终由主持人发起
    - 后续每次发言由 LLM 根据对话上下文自主决定谁最适合接话
    - 同一个人可以连续发言（模拟辩论中的抢话/补充）
    - 主持人可以在任何时候介入引导
    """

    # ── 公共方法（被测试直接调用） ──

    async def select_next_speaker(
        self,
        participants: list[dict],
        context: dict | None = None,
    ) -> int:
        """基于对话上下文选择下一位发言者的 participant_id。

        调度逻辑（非轮询）：
        1. 无历史发言 → 返回主持人（id=1 或 role=host）
        2. 有历史发言 → 从最近 3 条消息中统计已发言者，
           优先选择尚未发言或发言次数最少的参与者
        3. 20% 概率允许刚发言的人继续补充（模拟抢话）

        Args:
            participants: 参与者列表
            context: 对话上下文，包含 last_speaker_id, round, history 等

        Returns:
            被选中发言者的 participant_id
        """
        ctx = context or {}
        last_id = ctx.get("last_speaker_id")
        history = ctx.get("history", [])
        _round = ctx.get("round", 0)

        # 第一轮：主持人开场
        if _round == 0 or last_id is None:
            host = next(p for p in participants if p["role"] == "host")
            return host["id"]

        # 有 20% 概率允许同一个人连续发言（抢话/补充）
        if history and random.random() < 0.20:
            last_speaker = next(
                (p for p in participants if p["id"] == last_id), None
            )
            if last_speaker and last_speaker["role"] != "host":
                return last_speaker["id"]

        # 其余情况：选择发言次数最少的参与者
        speaker_counts: dict[int, int] = {}
        for p in participants:
            speaker_counts[p["id"]] = 0
        for msg in history[-10:]:  # 只看最近 10 条
            pid = msg.get("participant_id") if isinstance(msg, dict) else None
            if pid in speaker_counts:
                speaker_counts[pid] += 1

        # 按发言次数升序排列
        sorted_ids = sorted(speaker_counts, key=lambda x: speaker_counts[x])
        # 在前 50% 中随机选一个（保证公平但非确定性）
        top_half = sorted_ids[:max(2, len(sorted_ids) // 2 + 1)]
        choice = random.choice(top_half)

        return choice

    def build_system_prompt(
        self,
        topic: str,
        participants: list[dict],
    ) -> str:
        """组装发送给 LLM 的系统指令，包含严格的行为约束。

        Args:
            topic: 讨论话题
            participants: 参与者列表（含 role/name/title/stance）

        Returns:
            完整的系统指令字符串
        """
        host = next(p for p in participants if p["role"] == "host")
        experts = [p for p in participants if p["role"] == "expert"]

        lines = [
            f"你正在主持一场关于「{topic}」的 AI 圆桌讨论。",
            "",
            "【角色设定】",
            f"主持人：{host['name']}（{host['title']}）—— {host['stance']}",
            "",
            "【参与专家】",
        ]
        for i, expert in enumerate(experts, 1):
            lines.append(
                f"专家{i}：{expert['name']}（{expert['title']}）—— {expert['stance']}"
            )

        lines.extend([
            "",
            "【发言规则】",
            "1. 每次发言控制在 1-2 句，简洁有力。",
            "2. 欢迎观点碰撞，可以从你自己的立场出发反驳他人。",
            "3. 不允许机械重复自己或他人的观点。",
            "4. 不要一味附和，独立思考是讨论的核心价值。",
            "5. 主持人负责引导流程，但专家应当主动发表见解。",
            "6. 专家可以抢话或补充他人观点，这是正常的辩论行为。",
        ])

        return "\n".join(lines)

    # ── 完整讨论编排 ──

    async def run_discussion(
        self,
        discussion_id: int,
        topic: str,
        participants: list[dict],
        event_bus: EventBus,
        max_rounds: int = 10,
    ) -> None:
        """编排一场完整的 AI 圆桌讨论。

        流程：
        1. 主持人开场（system prompt + 开场白）
        2. 循环 N 轮，每轮：
           a. 选下一位发言者 → 发送 guest_status_change (thinking)
           b. 调用 LLM 流式生成发言 → 发送 message_chunk
           c. 发送 guest_status_change (speaking→idle)
           d. 每 3 轮提取一次共识 → 发送 consensus_update
        3. 主持人总结 → 讨论结束

        Args:
            discussion_id: 讨论 ID
            topic: 讨论话题
            participants: 参与者列表
            event_bus: 事件总线
            max_rounds: 最大讨论轮次
        """
        # 更新讨论状态为进行中
        await event_bus.publish(discussion_id, {
            "type": "discussion_status",
            "status": "in_progress",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        system_prompt = self.build_system_prompt(topic, participants)
        host = next(p for p in participants if p["role"] == "host")

        # 构建参与者映射
        participant_map = {p["id"]: p for p in participants}

        # 对话历史
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"请以主持人「{host['name']}」的身份开始讨论，"
                    f"围绕「{topic}」做一个简短的开场。控制在 1-2 句。"
                ),
            },
        ]

        context = {
            "last_speaker_id": None,
            "round": 0,
            "history": [],
        }

        # ── 第一轮：主持人开场 ──
        await self._speak(
            discussion_id=discussion_id,
            speaker_id=host["id"],
            speaker_name=host["name"],
            messages=messages,
            event_bus=event_bus,
            participant_map=participant_map,
            context=context,
            is_opening=True,
        )

        # ── 循环讨论 ──
        for round_num in range(1, max_rounds + 1):
            context["round"] = round_num

            # 选择下一位发言者
            next_id = await self.select_next_speaker(participants, context)
            speaker = participant_map[next_id]
            context["last_speaker_id"] = next_id

            # 生成发言
            speaker_type = "主持人" if speaker["role"] == "host" else f"专家{speaker['name']}"
            user_prompt = (
                f"现在请{speaker_type}（{speaker['name']}，{speaker['title']}）发言。"
                f"你的立场：{speaker['stance']}\n\n"
                f"1. 控制在 1-2 句。\n"
                f"2. 结合你自己的立场发表见解。\n"
                f"3. 可以反驳或补充前面其他人的观点。\n"
                f"4. 不允许机械重复。"
            )

            messages.append({"role": "user", "content": user_prompt})

            await self._speak(
                discussion_id=discussion_id,
                speaker_id=next_id,
                speaker_name=speaker["name"],
                messages=messages,
                event_bus=event_bus,
                participant_map=participant_map,
                context=context,
                is_opening=False,
            )

            # 每 3 轮提取一次共识
            if round_num % 3 == 0:
                await self._extract_and_push_consensus(
                    discussion_id=discussion_id,
                    topic=topic,
                    messages=messages,
                    event_bus=event_bus,
                )

            # 检查是否自然结束（主持人发出总结信号）
            if context.get("should_end"):
                break

        # ── 主持人总结（由 LLM 生成） ──
        messages.append({
            "role": "user",
            "content": (
                f"讨论即将结束，请以主持人「{host['name']}」的身份"
                f"做一个简短的总结发言。控制在 2-3 句。"
            ),
        })

        await self._speak(
            discussion_id=discussion_id,
            speaker_id=host["id"],
            speaker_name=host["name"],
            messages=messages,
            event_bus=event_bus,
            participant_map=participant_map,
            context=context,
            is_opening=False,
        )

        # 最终共识
        await self._extract_and_push_consensus(
            discussion_id=discussion_id,
            topic=topic,
            messages=messages,
            event_bus=event_bus,
            is_final=True,
        )

        # 讨论结束
        await event_bus.publish(discussion_id, {
            "type": "discussion_status",
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ── 内部方法 ──

    async def _speak(
        self,
        discussion_id: int,
        speaker_id: int,
        speaker_name: str,
        messages: list[dict],
        event_bus: EventBus,
        participant_map: dict[int, dict],
        context: dict,
        is_opening: bool = False,
    ) -> None:
        """让一位参与者发言，流式输出文本。"""
        timestamp = datetime.now(timezone.utc).isoformat()

        # guest_status_change → thinking
        await event_bus.publish(discussion_id, {
            "event": "guest_status_change",
            "data": {
                "participant_id": speaker_id,
                "status": "thinking",
                "timestamp": timestamp,
            },
        })

        # 收集完整发言内容
        full_content = ""

        # message_chunk 流式输出
        chunk_index = 0
        async for chunk in LlmService.stream_chat(messages):
            full_content += chunk
            await event_bus.publish(discussion_id, {
                "event": "message_chunk",
                "data": {
                    "participant_id": speaker_id,
                    "chunk_index": chunk_index,
                    "content": chunk,
                    "is_final": False,
                },
            })
            chunk_index += 1

        # 模拟 message_id
        message_id = hash((discussion_id, speaker_id, timestamp)) % (10**9)

        # message_chunk → final
        await event_bus.publish(discussion_id, {
            "event": "message_chunk",
            "data": {
                "participant_id": speaker_id,
                "chunk_index": chunk_index,
                "content": "",
                "is_final": True,
                "message_id": message_id,
            },
        })

        # 将发言加入消息历史
        messages.append({
            "role": "assistant",
            "content": full_content,
            "name": speaker_name,
        })

        context["history"].append({
            "participant_id": speaker_id,
            "content": full_content,
        })

        # guest_status_change → idle
        await event_bus.publish(discussion_id, {
            "event": "guest_status_change",
            "data": {
                "participant_id": speaker_id,
                "status": "idle",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        })

    async def _extract_and_push_consensus(
        self,
        discussion_id: int,
        topic: str,
        messages: list[dict],
        event_bus: EventBus,
        is_final: bool = False,
    ) -> None:
        """调用 LLM 提炼当前共识与分歧，并推送到 SSE。"""
        consensus_prompt = (
            f"基于以上关于「{topic}」的讨论内容，请提炼出：\n"
            "1. agreements: 当前参与者已达成的共识要点（JSON 字符串数组）\n"
            "2. divergences: 仍存在的分歧要点（JSON 字符串数组）\n\n"
            f"这是{'最终' if is_final else '阶段性'}共识总结。"
            "请严格以 JSON 格式返回，不要包含其他内容。"
        )

        extract_messages = messages + [
            {"role": "user", "content": consensus_prompt}
        ]

        try:
            response = await LlmService._call_llm_sync(extract_messages)

            # 尝试解析 JSON
            import re

            json_match = re.search(
                r'\{[^{}]*"agreements"[^{}]*"divergences"[^{}]*\}',
                response,
                re.DOTALL,
            )
            if json_match:
                consensus = json.loads(json_match.group())
            else:
                consensus = {"agreements": [], "divergences": []}

            await event_bus.publish(discussion_id, {
                "event": "consensus_update",
                "data": {
                    "agreements": consensus.get("agreements", []),
                    "divergences": consensus.get("divergences", []),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            })
        except Exception:
            # 共识提取失败时不阻断流程
            pass