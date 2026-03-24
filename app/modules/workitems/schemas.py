from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.modules.workitems.models import ParticipantRole, WorkItemPriority, WorkItemStatus, WorkItemType


class WorkItemCreate(BaseModel):
    type: WorkItemType
    title: str
    description: str | None = None
    assigner_id: int | None = None
    process_owner_id: int
    main_executor_id: int
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    status: WorkItemStatus = WorkItemStatus.NEW
    due_date: date | None = None

    @model_validator(mode="after")
    def validate_roles(self) -> "WorkItemCreate":
        if self.process_owner_id == self.main_executor_id:
            raise ValueError("process_owner_id must differ from main_executor_id")
        return self


class ParticipantCreate(BaseModel):
    user_id: int
    role: ParticipantRole
    order: int = 0
    status: str = Field(default="pending")


class StatusUpdate(BaseModel):
    status: WorkItemStatus
    reason: str | None = None


class BlockUpdate(BaseModel):
    is_blocked: bool
    reason: str | None = None


class RedirectUpdate(BaseModel):
    main_executor_id: int
    reason: str


class CommentCreate(BaseModel):
    text: str
