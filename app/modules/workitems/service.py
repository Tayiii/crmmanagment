from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import UPLOAD_DIR
from app.core.models import User
from app.modules.workitems.models import (
    ParticipantRole,
    WorkItem,
    WorkItemComment,
    WorkItemFile,
    WorkItemHistory,
    WorkItemParticipant,
    WorkItemStatus,
    WorkItemType,
)
from app.modules.workitems.schemas import (
    BlockUpdate,
    CommentCreate,
    ParticipantCreate,
    RedirectUpdate,
    StatusUpdate,
    WorkItemCreate,
)


def build_number(item_type: str, sequence: int) -> str:
    prefix = "POR" if item_type == WorkItemType.ASSIGNMENT else "REQ"
    return f"{prefix}-{datetime.utcnow():%Y}-{sequence:04d}"


async def get_users_map(session: AsyncSession) -> dict[int, User]:
    users = (await session.execute(select(User))).scalars().all()
    return {user.id: user for user in users}


async def list_work_items(session: AsyncSession) -> dict[str, list[WorkItem]]:
    result = await session.execute(select(WorkItem).order_by(WorkItem.due_date.is_(None), WorkItem.due_date, WorkItem.created_at.desc()))
    items = result.scalars().all()
    today = date.today()
    week_end = today + timedelta(days=7)
    buckets = {"overdue": [], "today": [], "week": [], "no_due_date": []}
    for item in items:
        if item.due_date is None:
            buckets["no_due_date"].append(item)
        elif item.due_date < today and item.status not in {WorkItemStatus.DONE, WorkItemStatus.CANCELLED, WorkItemStatus.REJECTED}:
            buckets["overdue"].append(item)
        elif item.due_date == today:
            buckets["today"].append(item)
        elif today < item.due_date <= week_end:
            buckets["week"].append(item)
    return buckets


async def get_work_item(session: AsyncSession, work_item_id: int) -> WorkItem:
    stmt = select(WorkItem).where(WorkItem.id == work_item_id).options(
        selectinload(WorkItem.participants),
        selectinload(WorkItem.history),
        selectinload(WorkItem.comments),
        selectinload(WorkItem.files),
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    return item


async def append_history(session: AsyncSession, work_item_id: int, user_id: int, action: str, old_value: str | None = None, new_value: str | None = None, reason: str | None = None) -> None:
    session.add(WorkItemHistory(work_item_id=work_item_id, user_id=user_id, action=action, old_value=old_value, new_value=new_value, reason=reason))


async def create_work_item(session: AsyncSession, payload: WorkItemCreate, current_user: User) -> WorkItem:
    sequence = (await session.execute(select(WorkItem.id))).scalars().all()
    item = WorkItem(
        type=payload.type,
        number=build_number(payload.type, len(sequence) + 1),
        title=payload.title,
        description=payload.description,
        initiator_id=current_user.id,
        assigner_id=payload.assigner_id or current_user.id,
        process_owner_id=payload.process_owner_id,
        main_executor_id=payload.main_executor_id,
        priority=payload.priority,
        status=payload.status,
        due_date=payload.due_date,
    )
    session.add(item)
    await session.flush()
    session.add(WorkItemParticipant(work_item_id=item.id, user_id=payload.main_executor_id, role=ParticipantRole.MAIN_EXECUTOR, order=0, status="active"))
    await append_history(session, item.id, current_user.id, "created", new_value=f"{item.type}:{item.status}")
    await session.commit()
    return await get_work_item(session, item.id)


async def add_participant(session: AsyncSession, work_item_id: int, payload: ParticipantCreate, current_user: User) -> None:
    await get_work_item(session, work_item_id)
    session.add(WorkItemParticipant(work_item_id=work_item_id, user_id=payload.user_id, role=payload.role, order=payload.order, status=payload.status))
    await append_history(session, work_item_id, current_user.id, "participant_added", new_value=f"user={payload.user_id}, role={payload.role}")
    await session.commit()


async def change_status(session: AsyncSession, work_item_id: int, payload: StatusUpdate, current_user: User) -> None:
    item = await get_work_item(session, work_item_id)
    old_status = item.status
    item.status = payload.status
    if payload.status == WorkItemStatus.DONE:
        item.completed_at = datetime.utcnow()
    await append_history(session, work_item_id, current_user.id, "status_changed", old_value=old_status, new_value=payload.status, reason=payload.reason)
    await session.commit()


async def set_block_state(session: AsyncSession, work_item_id: int, payload: BlockUpdate, current_user: User) -> None:
    item = await get_work_item(session, work_item_id)
    item.is_blocked = payload.is_blocked
    item.block_reason = payload.reason
    item.status = WorkItemStatus.BLOCKED if payload.is_blocked else WorkItemStatus.IN_PROGRESS
    await append_history(session, work_item_id, current_user.id, "block_changed", old_value=str(not payload.is_blocked), new_value=str(payload.is_blocked), reason=payload.reason)
    await session.commit()


async def redirect_work_item(session: AsyncSession, work_item_id: int, payload: RedirectUpdate, current_user: User) -> None:
    item = await get_work_item(session, work_item_id)
    old_executor = item.main_executor_id
    item.main_executor_id = payload.main_executor_id
    item.redirect_reason = payload.reason
    session.add(WorkItemParticipant(work_item_id=work_item_id, user_id=payload.main_executor_id, role=ParticipantRole.MAIN_EXECUTOR, order=0, status="active"))
    await append_history(session, work_item_id, current_user.id, "redirected", old_value=str(old_executor), new_value=str(payload.main_executor_id), reason=payload.reason)
    await session.commit()


async def add_comment(session: AsyncSession, work_item_id: int, payload: CommentCreate, current_user: User) -> None:
    await get_work_item(session, work_item_id)
    session.add(WorkItemComment(work_item_id=work_item_id, user_id=current_user.id, text=payload.text))
    await append_history(session, work_item_id, current_user.id, "comment_added")
    await session.commit()


async def save_file(session: AsyncSession, work_item_id: int, upload: UploadFile, current_user: User) -> None:
    await get_work_item(session, work_item_id)
    UPLOAD_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid4().hex}_{upload.filename}"
    destination = Path(UPLOAD_DIR) / unique_name
    content = await upload.read()
    destination.write_bytes(content)
    session.add(WorkItemFile(work_item_id=work_item_id, filename=upload.filename or unique_name, path=str(destination), uploaded_by_id=current_user.id))
    await append_history(session, work_item_id, current_user.id, "file_added", new_value=upload.filename)
    await session.commit()
