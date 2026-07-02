"""
对话会话表模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from atguigu.models.base import Base


class DialogueSessionRecord(Base):
    """对话会话记录"""
    __tablename__ = "dialogue_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户唯一标识")
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="会话ID")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="会话开始时间")
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="最后活动时间")
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="会话关闭时间")
    turns_json: Mapped[str] = mapped_column(Text, nullable=False, comment="对话轮次JSON")
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="会话标题")
    message_count: Mapped[int] = mapped_column(Integer, default=0, comment="消息数量")
    last_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="最后一条消息摘要")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index("uk_sender_session", "sender_id", "session_id", unique=True),
        Index("idx_sender_id", "sender_id"),
        Index("idx_started_at", "started_at"),
        Index("idx_last_activity", "last_activity_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
