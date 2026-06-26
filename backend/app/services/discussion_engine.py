"""讨论引擎 —— 发言调度、Prompt 组装、完整讨论流编排。

核心原则：
1. 坚决不轮询，但确保每位专家都有公平的发言机会
2. 每次发言限制 1-2 句
3. 周期性提炼共识与分歧
4. 高级特性：滑动窗口 + 上下文记忆压缩，防止长程 Token 溢出
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from app.services.event_bus import EventBus
from app.services.llm_service import LlmService

# 高级特性：动态上下文压缩，优化 Token 开销并防止幻觉
COMPRESS_AFTER_ROUNDS = 8   # 超过此轮数触发压缩
KEEP_RAW_ROUNDS = 2          # 压缩后保留的原始轮数


class DiscussionEngine:
    """讨论引擎：公平发言 + 节奏控制 + 滑动窗口压缩。"""

    # ---- 公开测试方法 ----

    async def select_next_speaker(
        self,
        participants: list[dict],
        context: dict | None = None,
    ) -> int:
        ctx = context or {}
        last_id = ctx.get("last_speaker_id")
        history = ctx.get("history", [])
        _round = ctx.get("round", 0)

        if _round == 0 or last_id is None:
            return next(p for p in participants if p["role"] == "host")["id"]

        speaker_counts: dict[int, int] = {p["id"]: 0 for p in participants}
        for msg in history:
            pid = msg.get("participant_id") if isinstance(msg, dict) else None
            if pid in speaker_counts:
                speaker_counts[pid] += 1

        expert_ids = [p["id"] for p in participants if p["role"] == "expert"]
        zero_speakers = [eid for eid in expert_ids if speaker_counts.get(eid, 0) == 0]
        if zero_speakers:
            return random.choice(zero_speakers)

        sorted_by_count = sorted(speaker_counts, key=lambda x: speaker_counts[x])
        pool_size = max(2, len(sorted_by_count) // 2 + 1)
        pool = sorted_by_count[:pool_size]
        choice = random.choice(pool)

        if (
            random.random() < 0.10
            and choice == last_id
            and any(p["id"] == choice and p["role"] != "host" for p in participants)
        ):
            pass

        return choice

    def build_system_prompt(
        self, topic: str, participants: list[dict]
    ) -> str:
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
            "",
            "【输出格式】",
            "每次发言必须输出严格 JSON 格式：",
            "{\"thought\": \"你的内部思考过程...\", \"speak\": \"你实际说出口的 1-2 句话\"}",
            "要求：",
            "- thought 是内部思考，不会直接展示给观众",
            "- speak 是最终发言，控制在 1-2 句",
            "- 每次只输出一个 JSON 对象，不要包裹 markdown 代码块",
        ])
        return "\n".join(lines)

    # ---- 完整讨论编排 ----

    async def run_discussion(
        self,
        discussion_id: int,
        topic: str,
        participants: list[dict],
        event_bus: EventBus,
        max_rounds: int = 10,
    ) -> None:
        await event_bus.publish(discussion_id, {
            "type": "discussion_status",
            "status": "in_progress",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        system_prompt = self.build_system_prompt(topic, participants)
        host = next(p for p in participants if p["role"] == "host")
        experts = [p for p in participants if p["role"] == "expert"]
        participant_map = {p["id"]: p for p in participants}

        suggested_rounds = len(experts) * 2 + 3
        total_rounds = min(max_rounds, suggested_rounds)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"请以主持人「{host['name']}」的身份开始讨论，"
                    f"围绕「{topic}」做一个简短的开场。控制在 1-2 句。\n"
                    f"请以 JSON 格式输出：{{\"thought\":\"...\",\"speak\":\"...\"}}"
                ),
            },
        ]

        context = {
            "last_speaker_id": None,
            "round": 0,
            "history": [],
            "total_rounds": total_rounds,
        }

        # 压缩状态
        compressed_context = None
        compression_applied = False

        # ---- 主持人开场 ----
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

        # ---- 循环讨论 ----
        for round_num in range(1, total_rounds + 1):
            context["round"] = round_num
            rounds_left = total_rounds - round_num

            # 高级特性：动态上下文压缩，优化 Token 开销并防止幻觉
            if not compression_applied and round_num >= COMPRESS_AFTER_ROUNDS and len(messages) > 6:
                compressed = await self._compress_history(messages, topic)
                if compressed:
                    compressed_context = compressed
                    compression_applied = True
                    recent = self._get_recent_rounds(messages, KEEP_RAW_ROUNDS)
                    assistant_count = len([m for m in messages if m["role"] == "assistant"])
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "system",
                            "content": (
                                f"【前情提要】以下是对前期讨论的摘要"
                                f"（{assistant_count - len(recent)} 条历史发言压缩为）：\n"
                                f"{compressed_context}"
                            ),
                        },
                    ] + recent

            next_id = await self.select_next_speaker(participants, context)
            speaker = participant_map[next_id]
            context["last_speaker_id"] = next_id

            speaker_type = "主持人" if speaker["role"] == "host" else f"专家{speaker['name']}"

            if rounds_left <= 1:
                prompt = self._build_prompt(speaker_type, speaker, "ending", topic)
            elif round_num <= 3:
                prompt = self._build_prompt(speaker_type, speaker, "opening", topic)
            else:
                prompt = self._build_prompt(speaker_type, speaker, "middle", topic)

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

            if round_num % 3 == 0 or round_num == total_rounds:
                await self._extract_and_push_consensus(
                    discussion_id=discussion_id,
                    topic=topic,
                    messages=messages,
                    event_bus=event_bus,
                    is_final=(round_num == total_rounds),
                )

        # ---- 主持人总结 ----
        messages.append({
            "role": "user",
            "content": (
                f"讨论已接近尾声，请以主持人「{host['name']}」的身份"
                f"做一个简短的总结发言，概括各方的核心观点。控制在 2-3 句。\n"
                f"请以 JSON 格式输出：{{\"thought\":\"...\",\"speak\":\"...\"}}"
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

        # 高级特性：动态上下文压缩，优化 Token 开销并防止幻觉
        await self._generate_final_summary(
            discussion_id=discussion_id,
            topic=topic,
            messages=messages,
            event_bus=event_bus,
            compressed_context=compressed_context,
        )

        await event_bus.publish(discussion_id, {
            "type": "discussion_status",
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ---- Prompt 工厂 ----

    def _build_prompt(self, speaker_type: str, speaker: dict, phase: str, topic: str) -> str:
        base = (
            f"现在请{speaker_type}（{speaker['name']}，{speaker['title']}）发言。"
            f"你的立场：{speaker['stance']}\n\n"
        )

        if phase == "ending":
            return (
                base
                + "1. 控制在 1-2 句。\n"
                + "2. 讨论即将结束，请做最后的观点陈述。\n"
                + "3. 请以 JSON 格式输出：{\"thought\":\"...\",\"speak\":\"...\"}"
            )
        elif phase == "opening":
            return (
                base
                + "1. 控制在 1-2 句。\n"
                + "2. 结合你自己的立场发表核心见解。\n"
                + "3. 可以反驳或补充前面其他人的观点。\n"
                + "4. 请以 JSON 格式输出：{\"thought\":\"...\",\"speak\":\"...\"}"
            )
        else:
            return (
                base
                + "1. 控制在 1-2 句。\n"
                + "2. 请对前面的观点做出回应或反驳。\n"
                + "3. 提出你独特的见解。\n"
                + "4. 请以 JSON 格式输出：{\"thought\":\"...\",\"speak\":\"...\"}"
            )

    # ---- 滑动窗口压缩 ----

    async def _compress_history(self, messages: list[dict], topic: str) -> str | None:
        """将早期对话压缩为 200 字以内的前情提要。

        高级特性：动态上下文压缩，优化 Token 开销并防止幻觉
        """
        assistant_msgs = []
        for i, m in enumerate(messages):
            if m["role"] == "assistant":
                assistant_msgs.append((i, m))

        if len(assistant_msgs) < 4:
            return None

        compress_end = max(0, len(assistant_msgs) - KEEP_RAW_ROUNDS * 2)
        early_msgs = assistant_msgs[:compress_end]

        history_text = "\n".join([
            f"{m.get('name', '发言人')}: {m['content'][:120]}"
            for _, m in early_msgs
        ])

        prompt = (
            f"以下是关于「{topic}」的圆桌讨论早期发言记录。\n"
            f"请将它们压缩为一段 200 字以内的「前情提要」，"
            f"保留核心观点、分歧点和关键论据。只输出摘要文本，不要额外说明。\n\n"
            f"{history_text}"
        )

        try:
            summary = await LlmService._call_llm_sync([{"role": "user", "content": prompt}])
            summary = summary.strip()
            if len(summary) > 20:
                return summary
        except Exception:
            pass
        return None

    def _get_recent_rounds(self, messages: list[dict], keep_rounds: int) -> list[dict]:
        """提取最近 N 轮的用户+助手消息。"""
        pairs = []
        i = len(messages) - 1
        while i >= 0 and len(pairs) < keep_rounds:
            if messages[i]["role"] == "assistant":
                if i > 0 and messages[i - 1]["role"] == "user":
                    pairs.insert(0, [messages[i - 1], messages[i]])
                    i -= 2
                else:
                    pairs.insert(0, [messages[i]])
                    i -= 1
            elif messages[i]["role"] == "user":
                pairs.insert(0, [messages[i]])
                i -= 1
            else:
                i -= 1

        recent = []
        for pair in pairs:
            recent.extend(pair)
        return recent

    # ---- 终场总结 ----

    async def _generate_final_summary(
        self,
        discussion_id: int,
        topic: str,
        messages: list[dict],
        event_bus: EventBus,
        compressed_context: str | None = None,
    ) -> None:
        """生成纯自然语言的终场总结。

        高级特性：动态上下文压缩，优化 Token 开销并防止幻觉
        """
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        last_speeches = "\n".join([
            f"{m.get('name', '发言人')}: {m['content'][:150]}"
            for m in assistant_msgs[-6:]
        ])

        summary_prompt = (
            f"以下是关于「{topic}」的圆桌讨论。"
        )
        if compressed_context:
            summary_prompt += f"前期摘要：{compressed_context}\n"
        summary_prompt += (
            f"近期发言：\n{last_speeches}\n\n"
            f"请以主持人的身份，用 3-4 句自然语言总结整场讨论的核心成果。"
            f"不要使用 JSON，直接输出总结文字。"
        )

        try:
            summary = await LlmService._call_llm_sync([{"role": "user", "content": summary_prompt}])
            summary = summary.strip()
            if len(summary) > 20:
                await event_bus.publish(discussion_id, {
                    "event": "discussion_summary",
                    "data": {"summary": summary},
                })
        except Exception:
            pass

    # ---- 发言与共识 ----

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
        from app.services.llm_service import JsonStreamParser

        timestamp = datetime.now(timezone.utc).isoformat()
        parser = JsonStreamParser()
        collected_speak = ""
        speak_chunk_index = 0

        await event_bus.publish(discussion_id, {
            "event": "guest_status_change",
            "data": {"participant_id": speaker_id, "status": "thinking", "timestamp": timestamp},
        })

        async for raw_chunk in LlmService.stream_chat(messages):
            objects = parser.feed(raw_chunk)
            for obj in objects:
                if "thought" in obj and obj["thought"]:
                    await event_bus.publish(discussion_id, {
                        "event": "guest_status_change",
                        "data": {"participant_id": speaker_id, "status": "thinking",
                                 "timestamp": datetime.now(timezone.utc).isoformat()},
                    })
                if "speak" in obj and obj["speak"]:
                    collected_speak += obj["speak"]
                    await event_bus.publish(discussion_id, {
                        "event": "message_chunk",
                        "data": {"participant_id": speaker_id, "chunk_index": speak_chunk_index,
                                 "content": obj["speak"], "is_final": False},
                    })
                    speak_chunk_index += 1

        remaining = parser.flush()
        if remaining and "speak" in remaining and remaining["speak"]:
            collected_speak += remaining["speak"]
            await event_bus.publish(discussion_id, {
                "event": "message_chunk",
                "data": {"participant_id": speaker_id, "chunk_index": speak_chunk_index,
                         "content": remaining["speak"], "is_final": False},
            })
            speak_chunk_index += 1

        if not collected_speak:
            async for chunk in LlmService.stream_chat(messages):
                collected_speak += chunk

        message_id = hash((discussion_id, speaker_id, timestamp)) % (10**9)

        await event_bus.publish(discussion_id, {
            "event": "message_chunk",
            "data": {"participant_id": speaker_id, "chunk_index": speak_chunk_index,
                     "content": "", "is_final": True, "message_id": message_id},
        })

        messages.append({"role": "assistant", "content": collected_speak, "name": speaker_name})
        context["history"].append({"participant_id": speaker_id, "content": collected_speak})

        await event_bus.publish(discussion_id, {
            "event": "guest_status_change",
            "data": {"participant_id": speaker_id, "status": "idle",
                     "timestamp": datetime.now(timezone.utc).isoformat()},
        })

    async def _extract_and_push_consensus(
        self,
        discussion_id: int,
        topic: str,
        messages: list[dict],
        event_bus: EventBus,
        is_final: bool = False,
    ) -> None:
        consensus_prompt = (
            f"基于以上关于「{topic}」的讨论内容，请提炼出：\n"
            "1. agreements: 当前参与者已达成的共识要点\n"
            "2. divergences: 仍存在的分歧要点\n\n"
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