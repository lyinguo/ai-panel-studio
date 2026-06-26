"""API 路由 —— AI 圆桌讨论。

端点清单：
  POST /api/discussions          — 创建讨论（AI 自动生成参与者）
  GET  /api/discussions          — 获取讨论列表
  GET  /api/discussions/{id}     — 获取讨论详情 + 参与者
  GET  /api/discussions/{id}/messages — 获取历史消息
  GET  /api/discussions/{id}/events  — SSE 事件流
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db import get_db
from app.models import Consensus, Discussion, Message, Participant
from app.schemas.api import (
    CreateDiscussionRequest,
    CreateDiscussionResponse,
    DiscussionListItem,
    ErrorResponse,
    MessageResponse,
    ParticipantResponse,
)
from app.services.discussion_engine import DiscussionEngine
from app.services.event_bus import EventBus
from app.services.llm_service import LlmService

router = APIRouter(prefix="/api", tags=["discussions"])

# 全局事件总线（单例）
event_bus = EventBus()


# ============================================================
# POST /api/discussions — 创建讨论
# ============================================================

@router.post(
    "/discussions",
    response_model=CreateDiscussionResponse,
    status_code=201,
    responses={400: {"model": ErrorResponse}},
)
async def create_discussion(
    body: CreateDiscussionRequest,
    db: Session = Depends(get_db),
):
    """创建 AI 圆桌讨论。

    调用 LLM 自动生成 1 位主持人和 N 位专家。
    每位参与者拥有独立的身份设定和颜色标识。
    """
    # 1. 保存讨论记录
    discussion = Discussion(
        topic=body.topic,
        expert_count=body.expert_count,
        status="pending",
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)

    # 2. 调用 LLM 生成参与者
    try:
        participants_data = await LlmService.generate_participants(
            topic=body.topic,
            expert_count=body.expert_count,
        )
    except Exception:
        # LLM 不可用时使用兜底方案
        participants_data = LlmService._fallback_participants(body.expert_count)

    # 3. 持久化参与者
    participant_responses = []
    for p_data in participants_data:
        participant = Participant(
            discussion_id=discussion.id,
            role=p_data["role"],
            name=p_data["name"],
            title=p_data["title"],
            stance=p_data["stance"],
            color_code=p_data["color_code"],
            order=p_data["order"],
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)
        participant_responses.append(
            ParticipantResponse(
                id=participant.id,
                role=participant.role,
                name=participant.name,
                title=participant.title,
                stance=participant.stance,
                color_code=participant.color_code,
                order=participant.order,
            )
        )

    # 4. 创建初始共识记录
    consensus = Consensus(
        discussion_id=discussion.id,
        agreements="[]",
        divergences="[]",
    )
    db.add(consensus)
    db.commit()

    # 5. 在后端启动讨论（不阻塞响应）
    discussion_id = discussion.id  # 在 close 前捕获 id
    # 将带 ID 的参与者数据转为 dict 传给后台任务
    participant_dicts = [p.model_dump() for p in participant_responses]
    db.close()
    asyncio.create_task(_run_discussion_in_background(
        discussion_id=discussion_id,
        topic=body.topic,
        participants=participant_dicts,
    ))

    return CreateDiscussionResponse(
        discussion_id=discussion_id,
        participants=participant_responses,
    )


# ============================================================
# GET /api/discussions — 讨论列表
# ============================================================

@router.get("/discussions", response_model=list[DiscussionListItem])
def list_discussions(db: Session = Depends(get_db)):
    """获取所有讨论列表。"""
    discussions = (
        db.query(Discussion)
        .order_by(Discussion.created_at.desc())
        .all()
    )
    return [
        DiscussionListItem(
            id=d.id,
            topic=d.topic,
            status=d.status,
            participant_count=len(d.participants),
            created_at=d.created_at.isoformat(),
        )
        for d in discussions
    ]


# ============================================================
# GET /api/discussions/{id} — 讨论详情
# ============================================================

@router.get(
    "/discussions/{discussion_id}",
    responses={404: {"model": ErrorResponse}},
)
def get_discussion(discussion_id: int, db: Session = Depends(get_db)):
    """获取讨论详情及参与者列表。"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    return {
        "id": discussion.id,
        "topic": discussion.topic,
        "expert_count": discussion.expert_count,
        "status": discussion.status,
        "created_at": discussion.created_at.isoformat(),
        "participants": [
            {
                "id": p.id,
                "role": p.role,
                "name": p.name,
                "title": p.title,
                "stance": p.stance,
                "color_code": p.color_code,
                "order": p.order,
            }
            for p in discussion.participants
        ],
    }


# ============================================================
# GET /api/discussions/{id}/messages — 历史消息
# ============================================================

@router.get(
    "/discussions/{discussion_id}/messages",
    response_model=list[MessageResponse],
    responses={404: {"model": ErrorResponse}},
)
def get_messages(
    discussion_id: int,
    before_id: int | None = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取历史消息，按 id ASC 排序保证绝对时序。"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    query = db.query(Message).filter(
        Message.discussion_id == discussion_id
    )

    if before_id is not None:
        query = query.filter(Message.id < before_id)

    messages = query.order_by(Message.id.asc()).limit(limit).all()

    return [
        MessageResponse(
            id=m.id,
            participant_id=m.participant_id,
            participant_name=m.participant.name,
            role=m.participant.role,
            content=m.content,
            color_code=m.participant.color_code,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


# ============================================================
# GET /api/discussions/{id}/events — SSE 事件流
# ============================================================

@router.get(
    "/discussions/{discussion_id}/events",
    responses={404: {"model": ErrorResponse}},
)
async def stream_events(
    discussion_id: int,
    db: Session = Depends(get_db),
):
    """SSE 事件流接口。

    事件类型：
      - guest_status_change: 参与者状态变更（thinking/speaking/idle）
      - message_chunk: 文本流式输出
      - consensus_update: 共识动态更新
    """
    # 验证讨论存在
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    async def event_generator():
        async for event in event_bus.event_stream(discussion_id):
            yield {
                "event": event.get("event", event.get("type", "message")),
                "data": json.dumps(event.get("data", event)),
            }

    return EventSourceResponse(event_generator())


# ============================================================
# 后台任务 — 运行讨论
# ============================================================

async def _run_discussion_in_background(
    discussion_id: int,
    topic: str,
    participants: list[dict],
) -> None:
    """在后端运行完整的 AI 圆桌讨论流程。"""
    engine = DiscussionEngine()
    await engine.run_discussion(
        discussion_id=discussion_id,
        topic=topic,
        participants=participants,
        event_bus=event_bus,
        max_rounds=10,
    )
