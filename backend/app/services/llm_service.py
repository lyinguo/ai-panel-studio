"""LLM 服务 —— AI 参与者生成与流式输出处理。

核心职责：
1. 调用 DeepSeek API，根据话题动态生成 1 位主持人 + N 位专家
2. 为每位参与者分配独立的身份设定（姓名、Title、立场、颜色标识）
3. 使用状态机拦截并丢弃 <think>...</think> 思维链内容
"""

from __future__ import annotations

import json
import re
from typing import AsyncIterator

import httpx

from app.core.config import settings


# ============================================================
# ThinkTagStripper — 严格状态机拦截思维链
# ============================================================

class ThinkTagStripper:
    """流式状态机：从 DeepSeek 流式输出中剥离 <think>...</think> 思维链。

    状态转移：
      NORMAL  ── 遇到 <think> ──► IN_THINK  ── 遇到 </think> ──► NORMAL
      输出内容     丢弃全部内容        恢复输出

    支持标签跨 chunk 边界（如 "<th" + "ink>" 分属两次 process 调用）。
    """

    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    def __init__(self):
        self._in_think = False
        self._buffer = ""

    def process(self, chunk: str) -> str:
        """处理一个文本块，返回剥离 think 标签后的纯净内容。"""
        combined = self._buffer + chunk
        self._buffer = ""
        output = []

        if self._in_think:
            idx = combined.find(self.CLOSE_TAG)
            if idx >= 0:
                self._in_think = False
                combined = combined[idx + len(self.CLOSE_TAG):]
            else:
                # 检查尾部是否有 </think> 的部分前缀
                self._buffer = self._partial_tag_suffix(combined, self.CLOSE_TAG)
                return ""

        # NORMAL 状态：提取 <think> 外部的全部文本
        while True:
            idx = combined.find(self.OPEN_TAG)
            if idx < 0:
                # 检查尾部是否有 <think> 的部分前缀
                self._buffer = self._partial_tag_suffix(combined, self.OPEN_TAG)
                if self._buffer:
                    output.append(combined[:-len(self._buffer)])
                else:
                    output.append(combined)
                break

            output.append(combined[:idx])
            after_open = combined[idx + len(self.OPEN_TAG):]
            close_idx = after_open.find(self.CLOSE_TAG)

            if close_idx < 0:
                self._in_think = True
                self._buffer = self._partial_tag_suffix(after_open, self.CLOSE_TAG)
                break

            combined = after_open[close_idx + len(self.CLOSE_TAG):]

        return "".join(output)

    def flush(self) -> str:
        """流结束时调用，返回残留的 buffer 内容。"""
        if not self._in_think and self._buffer:
            result = self._buffer
            self._buffer = ""
            return result
        self._buffer = ""
        return ""

    @staticmethod
    def _partial_tag_suffix(text: str, tag: str) -> str:
        """检查文本末尾是否是某个标签的部分前缀，返回匹配的后缀。"""
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return text[-i:]
        return ""


# ============================================================
# Color palette — 为每位参与者分配唯一颜色
# ============================================================

COLOR_PALETTE = [
    "#4A90D9",  # 蓝色（默认给主持人）
    "#FF6B6B",  # 红色
    "#50C878",  # 绿色
    "#FFD700",  # 金色
    "#9B59B6",  # 紫色
    "#FF8C42",  # 橙色
    "#00CED1",  # 青色
    "#E91E63",  # 粉红
    "#7F8C8D",  # 灰色
]


# ============================================================
# LlmService — 参与者生成
# ============================================================

PARTICIPANT_GENERATION_PROMPT = """你是一个 AI 圆桌讨论的策划者。请根据话题生成讨论参与者。

话题：{topic}

要求：
1. 生成 1 位主持人（host），负责引导讨论、保持中立
2. 生成 {expert_count} 位专家（expert），每位专家必须有**不同的立场**，彼此之间要能形成观点碰撞
3. 每位参与者必须包含以下字段：
   - role: "host" 或 "expert"
   - name: 中文姓名
   - title: 职业/领域头衔
   - stance: 核心立场描述（30-80 字），每位专家的立场必须不同
   - color_code: 颜色十六进制代码
   - order: 排序号（主持人=0，专家从 1 开始递增）

务必确保：
- 专家的立场之间有实质性分歧，能产生辩论
- 主持人保持中立
- 所有参与者的职业和立场与话题相关
- 严格按照 JSON 数组格式返回，不要包含任何其他内容"""


class LlmService:
    """大模型服务：封装与 DeepSeek API 的通信。"""

    @staticmethod
    def _get_client() -> httpx.AsyncClient:
        """获取 LLM API 的 HTTP 客户端。"""
        base_url = settings.deepseek_api_base_url.rstrip("/")
        return httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    @classmethod
    async def generate_participants(
        cls, topic: str, expert_count: int
    ) -> list[dict]:
        """调用 LLM 根据话题生成参与者列表。

        Args:
            topic: 讨论话题
            expert_count: 专家人数 (1~8)

        Returns:
            包含 1 位主持人和 N 位专家的参与者列表。
        """
        prompt = PARTICIPANT_GENERATION_PROMPT.format(
            topic=topic, expert_count=expert_count
        )

        response_text = await cls._call_llm(prompt)

        # 清理响应，提取 JSON
        participants = cls._parse_participants(response_text, expert_count)

        # 分配颜色标识
        cls._assign_colors(participants)

        return participants

    @classmethod
    async def _call_llm(cls, prompt: str) -> str:
        """调用 LLM API 并返回完整响应文本。"""
        stripper = ThinkTagStripper()
        full_response = ""

        async with cls._get_client() as client:
            async with client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": settings.deepseek_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "temperature": 0.8,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            cleaned = stripper.process(content)
                            full_response += cleaned
                    except json.JSONDecodeError:
                        continue

        full_response += stripper.flush()
        return full_response

    @classmethod
    async def _call_llm_sync(cls, messages: list[dict]) -> str:
        """非流式调用 LLM 并返回完成文本（用于共识提取等非流式场景）。"""
        stripper = ThinkTagStripper()

        async with cls._get_client() as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": settings.deepseek_model,
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            cleaned = stripper.process(content) + stripper.flush()
            return cleaned

    @classmethod
    async def stream_chat(
        cls, messages: list[dict]
    ) -> AsyncIterator[str]:
        """流式调用 LLM 并逐个 yield 已剥离 think 标签的文本块。"""
        stripper = ThinkTagStripper()

        async with cls._get_client() as client:
            async with client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": settings.deepseek_model,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.8,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            cleaned = stripper.process(content)
                            if cleaned:
                                yield cleaned
                    except json.JSONDecodeError:
                        continue

                # flush 残留 buffer
                remaining = stripper.flush()
                if remaining:
                    yield remaining

    # ── 辅助方法 ──

    @classmethod
    def _parse_participants(
        cls, raw: str, expected_expert_count: int
    ) -> list[dict]:
        """从 LLM 的原始响应中解析参与者列表。"""
        # 尝试提取 JSON 数组
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            try:
                participants = json.loads(json_match.group())
                if isinstance(participants, list) and len(participants) > 0:
                    return cls._validate_participants(
                        participants, expected_expert_count
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        # 退路：如果 JSON 解析失败，用兜底数据
        return cls._fallback_participants(expected_expert_count)

    @classmethod
    def _validate_participants(
        cls, participants: list[dict], expected_expert_count: int
    ) -> list[dict]:
        """验证参与者数据完整性，补全缺失字段。"""
        validated = []
        for i, p in enumerate(participants):
            participant = {
                "role": p.get("role", "expert" if i > 0 else "host"),
                "name": p.get("name", f"专家{i}"),
                "title": p.get("title", "领域专家"),
                "stance": p.get("stance", ""),
                "color_code": p.get("color_code", COLOR_PALETTE[i % len(COLOR_PALETTE)]),
                "order": p.get("order", i),
            }
            validated.append(participant)

        # 确保有且只有 1 个 host
        hosts = [p for p in validated if p["role"] == "host"]
        if len(hosts) == 0:
            validated[0]["role"] = "host"
            validated[0]["order"] = 0
        elif len(hosts) > 1:
            for h in hosts[1:]:
                h["role"] = "expert"

        return validated

    @classmethod
    def _assign_colors(cls, participants: list[dict]) -> None:
        """为没有颜色的参与者分配颜色，确保同一讨论内不重复。"""
        used = set()
        for p in participants:
            if p.get("color_code") and p["color_code"] not in used:
                used.add(p["color_code"])
                continue
            for color in COLOR_PALETTE:
                if color not in used:
                    p["color_code"] = color
                    used.add(color)
                    break

    @staticmethod
    def _fallback_participants(expert_count: int) -> list[dict]:
        """API 不可用时的兜底数据，确保创建流程不中断。"""
        from datetime import datetime

        fallback = [
            {
                "role": "host",
                "name": "主持人",
                "title": "AI 圆桌主持",
                "stance": "保持中立，公正引导各方讨论。",
                "color_code": COLOR_PALETTE[0],
                "order": 0,
            }
        ]
        for i in range(expert_count):
            fallback.append({
                "role": "expert",
                "name": f"专家{i+1}",
                "title": "领域专家",
                "stance": f"从专业角度分享见解。",
                "color_code": COLOR_PALETTE[(i + 1) % len(COLOR_PALETTE)],
                "order": i + 1,
            })
        return fallback
