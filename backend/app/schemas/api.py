"""API Schemas —— Pydantic 请求/响应模型。"""

from pydantic import BaseModel, Field


class CreateDiscussionRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    expert_count: int = Field(default=4, ge=1, le=8)


class ParticipantResponse(BaseModel):
    id: int
    role: str  # host | expert
    name: str
    title: str
    stance: str
    color_code: str
    order: int


class CreateDiscussionResponse(BaseModel):
    discussion_id: int
    participants: list[ParticipantResponse]


class DiscussionListItem(BaseModel):
    id: int
    topic: str
    status: str
    participant_count: int
    created_at: str


class MessageResponse(BaseModel):
    id: int
    participant_id: int
    participant_name: str
    role: str
    content: str
    color_code: str
    created_at: str


class ErrorResponse(BaseModel):
    detail: str
