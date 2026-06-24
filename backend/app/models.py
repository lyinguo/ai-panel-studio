"""AI Panel Studio — SQLAlchemy 数据模型

底层原则：所有数据表以 discussion_id 作为隔离外键。
任何一次查询都必须携带讨论归属过滤，禁止跨会话读取。
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db import Base


class Discussion(Base):
    """讨论组 —— 隔离核心，所有关联数据以此为界。"""

    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(200), nullable=False)
    expert_count = Column(Integer, nullable=False, default=4)
    status = Column(String(20), nullable=False, default="pending")  # pending | in_progress | completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 关联
    participants = relationship("Participant", back_populates="discussion", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="discussion", cascade="all, delete-orphan")
    consensus = relationship("Consensus", back_populates="discussion", uselist=False, cascade="all, delete-orphan")


class Participant(Base):
    """参与者（AI 动态生成，包含完整身份设定）。"""

    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(10), nullable=False)  # host | expert
    name = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    stance = Column(Text, nullable=False)
    color_code = Column(String(7), nullable=False)  # 如 #FF6B6B
    order = Column(Integer, nullable=False, default=0)  # 主持人为 0，专家从 1 起
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 关联
    discussion = relationship("Discussion", back_populates="participants")
    messages = relationship("Message", back_populates="participant", cascade="all, delete-orphan")


class Message(Base):
    """发言记录 —— SSE 流式累积完成后写入。

    查询时必须严格按 ORDER BY id ASC 排序，保证绝对时序。
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 关联
    discussion = relationship("Discussion", back_populates="messages")
    participant = relationship("Participant", back_populates="messages")


class Consensus(Base):
    """动态共识 —— 每讨论严格一对一（discussion_id UNIQUE）。

    存储实时生成的共识要点与分歧要点。
    不保留历史版本，前端只关心最新共识。
    """

    __tablename__ = "consensus"

    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(
        Integer,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 数据库级 1:1 硬约束
        index=True,
    )
    agreements = Column(Text, nullable=False, default="[]")  # JSON Array
    divergences = Column(Text, nullable=False, default="[]")  # JSON Array
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 关联
    discussion = relationship("Discussion", back_populates="consensus")

    __table_args__ = (
        UniqueConstraint("discussion_id", name="uq_consensus_discussion"),
    )
