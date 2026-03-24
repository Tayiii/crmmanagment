from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class WorkItemType(StrEnum):
    ASSIGNMENT = "assignment"
    REQUEST = "request"


class WorkItemPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkItemStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"
    SENT = "sent"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ParticipantRole(StrEnum):
    MAIN_EXECUTOR = "main_executor"
    CO_EXECUTOR = "co_executor"
    OBSERVER = "observer"


class ParticipantStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"


class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(nullable=False)
    number: Mapped[str] = mapped_column(unique=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    process_owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    main_executor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    priority: Mapped[str] = mapped_column(default=WorkItemPriority.MEDIUM)
    status: Mapped[str] = mapped_column(default=WorkItemStatus.NEW)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants: Mapped[list["WorkItemParticipant"]] = relationship(back_populates="work_item", cascade="all, delete-orphan")
    history: Mapped[list["WorkItemHistory"]] = relationship(back_populates="work_item", cascade="all, delete-orphan")
    comments: Mapped[list["WorkItemComment"]] = relationship(back_populates="work_item", cascade="all, delete-orphan")
    files: Mapped[list["WorkItemFile"]] = relationship(back_populates="work_item", cascade="all, delete-orphan")


class WorkItemParticipant(Base):
    __tablename__ = "work_item_participants"
    __table_args__ = (UniqueConstraint("work_item_id", "user_id", "role", name="uq_work_item_participant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(default=ParticipantStatus.PENDING)

    work_item: Mapped[WorkItem] = relationship(back_populates="participants")


class WorkItemHistory(Base):
    __tablename__ = "work_item_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_item: Mapped[WorkItem] = relationship(back_populates="history")


class WorkItemComment(Base):
    __tablename__ = "work_item_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_item: Mapped[WorkItem] = relationship(back_populates="comments")


class WorkItemFile(Base):
    __tablename__ = "work_item_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_item: Mapped[WorkItem] = relationship(back_populates="files")
