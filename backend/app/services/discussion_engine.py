"""讨论引擎 —— 发言调度、Prompt 组装、完整讨论流编排。

核心原则：
1. 坚决不轮询，但确保每位专家都有公平的发言机会
2. 每次发言限制 1-2 句
3. 周期性提炼共识与分歧
4. 主持人控制节奏，讨论到达上限时自然结束
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from app.services.event_bus import EventBus
from app.services.llm_service import LlmService


class DiscussionEngine:
    """讨论引擎：确保公平发言 + 主持人节奏控制。"""

    # ── 公开测试方法 ──

    async def select_next_speaker(
        self,
        participants: list[dict],
        context: dict | None = None,
    ) -> int:
        """公平选择下一位发言者。

        调度策略（非轮询，但确保公平）：
        1. round=0 → 主持人开场
        2. 还有专家从未发言 → 优先从未发言者中选
        3. 正常轮次 → 选择发言次数最少的参与者（从最少的前 50% 随机）
        4. 10% 概率允许刚发言的非主持人继续补充（模拟抢话）
        """
        ctx = context or {}
        last_id = ctx.get("last_speaker_id")
        history = ctx.get("history", [])
        _round = ctx.get("round", 0)

        # 第 0 轮：主持人开场
        if _round == 0 or last_id is None:
            return next(p for p in participants if p["role"] == "host")["id"]

        # 统计每个人的发言次数
        speaker_counts: dict[int, int] = {p["id"]: 0 for p in participants}
        for msg in history:
            pid = msg.get("participant_id") if isinstance(msg, dict) else None
            if pid in speaker_counts:
                speaker_counts[pid] += 1

        expert_ids = [p["id"] for p in participants if p["role"] == "expert"]

        # 阶段 1：有专家还没发过言 → 强制给机会
        zero_speakers = [eid for eid in expert_ids if speaker_counts.get(eid, 0) == 0]
        if zero_speakers:
            return random.choice(zero_speakers)

        # 阶段 2：正常选择 — 发言最少者优先
        sorted_by_count = sorted(speaker_counts, key=lambda x: speaker_counts[x])
        pool_size = max(2, len(sorted_by_count) // 2 + 1)
        pool = sorted_by_count[:pool_size]
        choice = random.choice(pool)

        # 10% 概率：同一个非主持人继续补充（抢话）
        if (
            random.random() < 0.10
            and choice == last_id
            and any(p["id"] == choice and p["role"] != "host" for p in participants)
        ):
            pass  # 允许同一个人继续

        return choice

    def build_system_prompt(
        self, topic: str, participants: list[dict]
    ) -> str:
        """组装系统指令。"""
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
            "5. 主持人负责引导流程，确保每位专家都有发言机会。",
            "6. 讨论接近上限时，主持人应引导总结并结束讨论。",
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
        """编排一场完整的 AI 圆桌讨论，确保公平发言 + 节奏控制。"""
        await event_bus.publish(discussion_id, {
            "type": "discussion_status",
            "status": "in_progress",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        system_prompt = self.build_system_prompt(topic, participants)
        host = next(p for p in participants if p["role"] == "host")
        experts = [p for p in participants if p["role"] == "expert"]
        participant_map = {p["id"]: p for p in participants}

        # 计算合理的讨论轮数：每位专家至少 2 次 + 主持人 3 次
        suggested_rounds = len(experts) * 2 + 3
        total_rounds = min(max_rounds, suggested_rounds)

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
            "total_rounds": total_rounds,
        }

        # ── 主持人开场 ──
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
        for round_num in range(1, total_rounds + 1):
            context["round"] = round_num

            next_id = await self.select_next_speaker(participants, context)
            speaker = participant_map[next_id]
            context["last_speaker_id"] = next_id

            speaker_type = "主持人" if speaker["role"] == "host" else f"专家{speaker['name']}"

            # 不同的轮次使用不同的 prompt 风格
            rounds_left = total_rounds - round_num

            if rounds_left <= 1:
                # 最后一轮前，主持人催促
                prompt = (
                    f"现在请{speaker_type}（{speaker['name']}，{speaker['title']}）发言。"
                    f"你的立场：{speaker['stance']}\n\n"
                    f"1. 控制在 1-2 句。\n"
                    f"2. 讨论即将结束，请做最后的观点陈述。\n"
                    f"3. 可以简要反驳或补充之前的观点。"
                )
            elif round_num <= 3:
                # 前几轮：深入探讨
                prompt = (
                    f"现在请{speaker_type}（{speaker['name']}，{speaker['title']}）发言。"
                    f"你的立场：{speaker['stance']}\n\n"
                    f"1. 控制在 1-2 句。\n"
                    f"2. 结合你自己的立场发表核心见解。\n"
                    f"3. 可以反驳或补充前面其他人的观点。\n"
                    f"4. 不允许机械重复。"
                )
            else:
                # 中段：观点碰撞
                prompt = (
                    f"现在请{speaker_type}（{speaker['name']}，{speaker['title']}）发言。"
                    f"你的立场：{speaker['stance']}\n\n"
                    f"1. 控制在 1-2 句。\n"
                    f"2. 请对前面的观点做出回应或反驳。\n"
                    f"3. 提出你独特的见解。\n"
                    f"4. 不允许机械重复。"
                )

            messages.append({"role": "user", "content": prompt})

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
            if round_num % 3 == 0 or round_num == total_rounds:
                await self._extract_and_push_consensus(
                    discussion_id=discussion_id,
                    topic=topic,
                    messages=messages,
                    event_bus=event_bus,
                    is_final=(round_num == total_rounds),
                )

            if context.get("should_end"):
                break

        # ── 主持人总结 ──
        messages.append({
            "role": "user",
            "content": (
                f"讨论已接近尾声，请以主持人「{host['name']}」的身份"
                f"做一个简短的总结发言，概括各方的核心观点。控制在 2-3 句。"
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
        """让一位参与者发言，流式输出。"""
        timestamp = datetime.now(timezone.utc).isoformat()

        await event_bus.publish(discussion_id, {
            "event": "guest_status_change",
            "data": {
                "participant_id": speaker_id,
                "status": "thinking",
                "timestamp": timestamp,
            },
        })

        full_content = ""
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

        message_id = hash((discussion_id, speaker_id, timestamp)) % (10**9)

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

        messages.append({
            "role": "assistant",
            "content": full_content,
            "name": speaker_name,
        })

        context["history"].append({
            "participant_id": speaker_id,
            "content": full_content,
        })

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
        """提炼共识与分歧。"""
        consensus_prompt = (
            f"基于以上关于「{topic}」的讨论内容，请提炼出：\n"
            "1. agreements: 当前参与者已达成的共识要点（JSON 字符串数组）\n"
            "2. divergences: 仍存在的分歧要点（JSON 字符串数组）\n\n"
            f"这是{'最终' if is_final else '阶段性'}共识总结。"
            "请严格以 JSON 格式返回，不要包含其他内容。"
        )

        try:
            response = await LlmService._call_llm_sync(
                messages + [{"role": "user", "content": consensus_prompt}]
            )

            import re
            json_match = re.search(
                r'\{[^{}]*"agreements"[^{}]*"divergences"[^{}]*\}',
                response, re.DOTALL,
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
            pass