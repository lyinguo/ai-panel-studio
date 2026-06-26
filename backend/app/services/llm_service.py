"""LLM 服务 — AI 参与者生成与流式对话。

关键修复：
1. API 路径自动探测（/v1/chat/completions 或 /chat/completions）
2. 无 API Key 时生成有意义的模拟对话
3. 严格状态机拦截  thinking... response
"""

from __future__ import annotations

import json
import re
import random
from typing import AsyncIterator

import httpx

from app.core.config import settings


# ============================================================
# ThinkTagStripper — 剥离思维链
# ============================================================

class ThinkTagStripper:
    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    def __init__(self):
        self._in_think = False
        self._buffer = ""

    def process(self, chunk: str) -> str:
        combined = self._buffer + chunk
        self._buffer = ""
        output = []

        if self._in_think:
            idx = combined.find(self.CLOSE_TAG)
            if idx >= 0:
                self._in_think = False
                combined = combined[idx + len(self.CLOSE_TAG):]
            else:
                self._buffer = self._partial_tag_suffix(combined, self.CLOSE_TAG)
                return ""

        while True:
            idx = combined.find(self.OPEN_TAG)
            if idx < 0:
                self._buffer = self._partial_tag_suffix(combined, self.OPEN_TAG)
                output.append(combined[:-len(self._buffer)] if self._buffer else combined)
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
        if not self._in_think and self._buffer:
            r = self._buffer
            self._buffer = ""
            return r
        self._buffer = ""
        return ""

    @staticmethod
    def _partial_tag_suffix(text: str, tag: str) -> str:
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return text[-i:]
        return ""


COLOR_PALETTE = [
    "#4A90D9", "#FF6B6B", "#50C878", "#FFD700",
    "#9B59B6", "#FF8C42", "#00CED1", "#E91E63", "#7F8C8D",
]

PARTICIPANT_PROMPT = """你是一个圆桌讨论策划。根据话题生成 {n} 位参与者（1 host + {m} experts）。

话题：{topic}

JSON 数组格式，每个元素包含：role, name, title, stance, color_code, order。
每位专家立场必须不同且有实质性分歧。"""


class LlmService:
    """大模型服务。"""

    # 缓存的 API 路径（探测后缓存）
    _api_path: str | None = None

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
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
    async def _resolve_api_path(cls) -> str:
        """探测可用的 API 路径，结果缓存到类变量。"""
        if cls._api_path:
            return cls._api_path

        candidates = ["/v1/chat/completions", "/chat/completions"]
        base = settings.deepseek_api_base_url.rstrip("/")

        # 跳过探测：如果 base 已经是 api.deepseek.com，直接用 /chat/completions
        if "api.deepseek.com" in base:
            cls._api_path = "/chat/completions"
            return cls._api_path

        for path in candidates:
            try:
                async with httpx.AsyncClient(base_url=base, timeout=5.0) as c:
                    resp = await c.post(path, json={
                        "model": settings.deepseek_model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "stream": False,
                        "max_tokens": 1,
                    }, headers={
                        "Authorization": f"Bearer {settings.deepseek_api_key}",
                        "Content-Type": "application/json",
                    })
                    if resp.status_code < 500:
                        cls._api_path = path
                        return path
            except Exception:
                continue

        cls._api_path = candidates[0]  # 默认
        return cls._api_path

    # ════════════════════════════════════════════
    # 参与者生成
    # ════════════════════════════════════════════

    @classmethod
    async def generate_participants(cls, topic: str, expert_count: int) -> list[dict]:
        """调用 LLM 生成 1 host + N experts。"""
        prompt = PARTICIPANT_PROMPT.format(topic=topic, n=expert_count + 1, m=expert_count)
        try:
            text = await cls._call_llm(prompt)
            participants = cls._parse_participants(text, expert_count)
        except Exception:
            participants = cls._fallback_participants(topic, expert_count)

        cls._assign_colors(participants)
        return participants

    # ════════════════════════════════════════════
    # LLM 调用（流式 + 非流式）
    # ════════════════════════════════════════════

    @classmethod
    async def _call_llm(cls, prompt: str) -> str:
        """非流式调用，返回完整文本。"""
        if not settings.deepseek_api_key:
            return cls._fallback_any(prompt)

        path = await cls._resolve_api_path()
        stripper = ThinkTagStripper()
        full = ""

        try:
            async with cls._get_client() as client:
                async with client.stream("POST", path, json={
                    "model": settings.deepseek_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "temperature": 0.8,
                }) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        d = line[6:].strip()
                        if d == "[DONE]":
                            break
                        try:
                            delta = json.loads(d).get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                full += stripper.process(delta)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"[LLM] API call failed: {e}")  # stderr, visible in server log
            return cls._fallback_any(prompt)

        full += stripper.flush()
        return full or cls._fallback_any(prompt)

    @classmethod
    async def _call_llm_sync(cls, messages: list[dict]) -> str:
        """非流式调用（共识提取用）。"""
        if not settings.deepseek_api_key:
            return cls._fallback_any(messages[-1].get("content", "") if messages else "")

        path = await cls._resolve_api_path()
        stripper = ThinkTagStripper()

        try:
            async with cls._get_client() as client:
                resp = await client.post(path, json={
                    "model": settings.deepseek_model,
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                })
                resp.raise_for_status()
                content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                return stripper.process(content) + stripper.flush()
        except Exception as e:
            print(f"[LLM] Sync call failed: {e}")
            return cls._fallback_any(messages[-1].get("content", "") if messages else "")

    @classmethod
    async def stream_chat(cls, messages: list[dict]) -> AsyncIterator[str]:
        """流式调用，逐块 yield。"""
        if not settings.deepseek_api_key:
            yield cls._fallback_any(messages[-1].get("content", "") if messages else "")
            return

        path = await cls._resolve_api_path()
        stripper = ThinkTagStripper()

        try:
            async with cls._get_client() as client:
                async with client.stream("POST", path, json={
                    "model": settings.deepseek_model,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.8,
                }) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        d = line[6:].strip()
                        if d == "[DONE]":
                            break
                        try:
                            delta = json.loads(d).get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                cleaned = stripper.process(delta)
                                if cleaned:
                                    yield cleaned
                        except json.JSONDecodeError:
                            continue
                    remaining = stripper.flush()
                    if remaining:
                        yield remaining
        except Exception as e:
            print(f"[LLM] Stream call failed: {e}")
            yield cls._fallback_any(messages[-1].get("content", "") if messages else "")

    # ════════════════════════════════════════════
    # 智能回退：根据提示词生成上下文相关的模拟内容
    # ════════════════════════════════════════════

    @classmethod
    def _fallback_any(cls, prompt: str) -> str:
        """根据提示词上下文，生成合理的模拟回复。"""
        # 共识提取请求
        if "agreements" in prompt and "divergences" in prompt:
            return json.dumps({
                "agreements": ["各方都认同需要深入探讨", "安全与创新需要平衡"],
                "divergences": ["具体实施路径存在分歧", "优先级排序看法不一"],
            })

        # 参与者生成请求
        if "圆桌讨论策划" in prompt:
            return json.dumps([
                {"role": "host", "name": "陈思远", "title": "AI 伦理与治理专家",
                 "stance": "保持中立，引导各方聚焦核心议题，确保讨论深入有序。", "color_code": "#4A90D9", "order": 0},
                {"role": "expert", "name": "李薇", "title": "资深机器学习研究员",
                 "stance": "技术本身是中立的，关键在于应用场景和监管框架的完善。", "color_code": "#FF6B6B", "order": 1},
                {"role": "expert", "name": "王磊", "title": "AI 安全专家",
                 "stance": "主张审慎渐进策略，安全护栏必须前置，不可盲目推进。", "color_code": "#50C878", "order": 2},
                {"role": "expert", "name": "赵雨桐", "title": "计算神经科学博士",
                 "stance": "从认知科学论证，当前 AI 距离真正理解还有本质差距。", "color_code": "#FFD700", "order": 3},
                {"role": "expert", "name": "孙明达", "title": "开源社区发起人",
                 "stance": "强调开放研究的重要性，透明度和可复现性是安全的底线。", "color_code": "#9B59B6", "order": 4},
            ])

        # 发言生成：从 prompt 中提取发言者身份和立场
        return cls._generate_speech(prompt)

    @classmethod
    def _generate_speech(cls, prompt: str) -> str:
        """从发言 prompt 中提取上下文，生成 1-2 句模拟发言。"""
        name = "发言人"
        stance = ""
        topic = "当前话题"
        is_opening = "开场的" in prompt or "开场" in prompt
        is_summary = "总结" in prompt or "结束" in prompt

        # 提取姓名
        m = re.search(r'（([^）]+)', prompt)
        if m:
            name = m.group(1)

        # 提取立场
        m = re.search(r'立场[：:]\s*([^\n。]+)', prompt)
        if m:
            stance = m.group(1).strip()

        # 提取话题
        m = re.search(r'「([^」]+)」', prompt)
        if m:
            topic = m.group(1)

        # 根据角色生成不同发言
        if is_opening:
            return (
                f"欢迎各位来到关于「{topic}」的圆桌讨论。"
                f"今天这个话题非常有价值，在座各位都有深入的见解。"
                f"让我们依次分享观点，碰撞出思想的火花。"
            )

        if is_summary:
            return (
                f"感谢各位的精彩发言。今天我们听到了多元的视角，"
                f"虽然在一些具体问题上存在分歧，但在核心方向上达成了基本共识。"
                f"这场讨论为我们提供了宝贵的思考框架。"
            )

        # 普通发言：根据立场生成
        if "技术中立" in stance:
            return (
                f"关于「{topic}」，我认为技术本身没有善恶之分。"
                f"关键在于我们如何建立有效的监管和应用框架，"
                f"让技术真正服务于人类需求。"
            )
        elif "审慎" in stance or "渐进" in stance or "安全" in stance:
            return (
                f"我同意大家的关注，但想强调安全必须前置。"
                f"在没有充分理解潜在风险之前，保持审慎态度是对社会负责的表现。"
            )
        elif "认知" in stance or "差距" in stance:
            return (
                f"我想从基础认知的视角补充一点。"
                f"当前系统本质上是高级模式匹配，距离真正的理解还有本质差距。"
                f"我们需要更务实地评估现状。"
            )
        elif "开源" in stance or "透明" in stance:
            return (
                f"无论技术发展到哪一步，开放透明都是最好的安全机制。"
                f"开源社区的研究和讨论能汇聚全球智慧，降低闭门造车的风险。"
            )
        elif "中立" in stance or "引导" in stance:
            return (
                f"让我引导一下讨论方向。关于「{topic}」，"
                f"我们是否可以从正反两面各梳理一下核心论据？"
            )
        else:
            # 随机发言
            opinions = [
                f"关于「{topic}」，我认为需要从多个维度来审视。",
                f"这个问题的核心在于我们如何平衡发展与安全的关系。",
                f"我基本认同前面的观点，但想补充一个不同的视角。",
                f"从我的专业领域来看，这个问题比表面看起来要复杂得多。",
                f"我们是否忽略了另一个重要的影响因素？",
            ]
            return random.choice(opinions)

    # ════════════════════════════════════════════
    # 参与者解析与兜底
    # ════════════════════════════════════════════

    @classmethod
    def _parse_participants(cls, raw: str, expected: int) -> list[dict]:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                p = json.loads(m.group())
                if isinstance(p, list) and len(p) > 0:
                    return cls._validate(p, expected)
            except Exception:
                pass
        return cls._fallback_participants("", expected)

    @classmethod
    def _validate(cls, participants: list[dict], expected: int) -> list[dict]:
        validated = []
        for i, p in enumerate(participants):
            validated.append({
                "role": p.get("role", "expert" if i > 0 else "host"),
                "name": p.get("name", f"专家{i}"),
                "title": p.get("title", "领域专家"),
                "stance": p.get("stance", ""),
                "color_code": p.get("color_code", COLOR_PALETTE[i % len(COLOR_PALETTE)]),
                "order": p.get("order", i),
            })
        hosts = [p for p in validated if p["role"] == "host"]
        if not hosts:
            validated[0]["role"] = "host"
            validated[0]["order"] = 0
        return validated

    @classmethod
    def _assign_colors(cls, participants: list[dict]) -> None:
        used = set()
        for p in participants:
            if p.get("color_code") and p["color_code"] not in used:
                used.add(p["color_code"])
                continue
            for c in COLOR_PALETTE:
                if c not in used:
                    p["color_code"] = c
                    used.add(c)
                    break

    @classmethod
    def _fallback_participants(cls, topic: str, count: int) -> list[dict]:
        """有意义的兜底参与者。"""
        stances = [
            ("陈思远", "AI 伦理与治理专家", "保持中立，引导各方聚焦核心议题，确保讨论深入有序。"),
            ("李薇", "资深机器学习研究员", "技术本身是中立的，关键在于应用场景和监管框架的完善。"),
            ("王磊", "AI 安全专家", "主张审慎渐进策略，安全护栏必须前置，不可盲目推进。"),
            ("赵雨桐", "计算神经科学博士", "从认知科学论证，当前 AI 距离真正理解还有本质差距。"),
            ("孙明达", "开源社区发起人", "强调开放研究的重要性，透明度和可复现性是安全的底线。"),
        ]
        fallback = [{
            "role": "host", "name": stances[0][0], "title": stances[0][1],
            "stance": stances[0][2], "color_code": COLOR_PALETTE[0], "order": 0,
        }]
        for i in range(min(count, len(stances) - 1)):
            fallback.append({
                "role": "expert", "name": stances[i + 1][0], "title": stances[i + 1][1],
                "stance": stances[i + 1][2],
                "color_code": COLOR_PALETTE[(i + 1) % len(COLOR_PALETTE)],
                "order": i + 1,
            })
        # 如果专家数超过预设列表，用通用名补充
        for i in range(len(stances) - 1, count):
            fallback.append({
                "role": "expert", "name": f"专家{i+1}", "title": "领域专家",
                "stance": "从专业角度分享见解。",
                "color_code": COLOR_PALETTE[(i + 1) % len(COLOR_PALETTE)],
                "order": i + 1,
            })
        return fallback