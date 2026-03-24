from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import TEMPLATES_DIR, WORKITEM_TEMPLATES_DIR
from app.core.auth import get_current_user
from app.core.models import User
from app.db import get_session
from app.modules.workitems.models import WorkItemPriority, WorkItemStatus, WorkItemType
from app.modules.workitems.schemas import BlockUpdate, CommentCreate, ParticipantCreate, RedirectUpdate, StatusUpdate, WorkItemCreate
from app.modules.workitems.service import (
    add_comment,
    add_participant,
    change_status,
    create_work_item,
    get_users_map,
    get_work_item,
    list_work_items,
    redirect_work_item,
    save_file,
    set_block_state,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.loader.searchpath.append(str(WORKITEM_TEMPLATES_DIR))

router = APIRouter(prefix="/workitems", tags=["workitems"])


@router.get("/", response_class=HTMLResponse)
async def workitems_list(request: Request, session: AsyncSession = Depends(get_session)):
    buckets = await list_work_items(session)
    users = await get_users_map(session)
    return templates.TemplateResponse(
        request,
        "workitems/list.html",
        {"buckets": buckets, "users": users, "title": "Поручения и запросы"},
    )


@router.get("/new", response_class=HTMLResponse)
async def workitems_new(request: Request, session: AsyncSession = Depends(get_session)):
    users = await get_users_map(session)
    return templates.TemplateResponse(
        request,
        "workitems/new.html",
        {
            "users": users.values(),
            "types": list(WorkItemType),
            "priorities": list(WorkItemPriority),
            "statuses": list(WorkItemStatus),
            "title": "Создание WorkItem",
        },
    )


@router.post("/")
async def workitems_create(
    type: str = Form(...),
    title: str = Form(...),
    description: str | None = Form(default=None),
    assigner_id: int | None = Form(default=None),
    process_owner_id: int = Form(...),
    main_executor_id: int = Form(...),
    priority: str = Form(default=WorkItemPriority.MEDIUM),
    status: str = Form(default=WorkItemStatus.NEW),
    due_date: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    current_user = await get_current_user(session)
    payload = WorkItemCreate(
        type=type,
        title=title,
        description=description,
        assigner_id=assigner_id,
        process_owner_id=process_owner_id,
        main_executor_id=main_executor_id,
        priority=priority,
        status=status,
        due_date=due_date or None,
    )
    item = await create_work_item(session, payload, current_user)
    return RedirectResponse(url=f"/workitems/{item.id}", status_code=303)


@router.get("/{work_item_id}", response_class=HTMLResponse)
async def workitem_detail(request: Request, work_item_id: int, session: AsyncSession = Depends(get_session)):
    item = await get_work_item(session, work_item_id)
    users = await get_users_map(session)
    return templates.TemplateResponse(
        request,
        "workitems/detail.html",
        {"item": item, "users": users, "statuses": list(WorkItemStatus), "title": item.title},
    )


@router.post("/{work_item_id}/participants")
async def workitem_add_participant(work_item_id: int, user_id: int = Form(...), role: str = Form(...), order: int = Form(default=0), status: str = Form(default="pending"), session: AsyncSession = Depends(get_session)):
    current_user = await get_current_user(session)
    await add_participant(session, work_item_id, ParticipantCreate(user_id=user_id, role=role, order=order, status=status), current_user)
    return RedirectResponse(url=f"/workitems/{work_item_id}", status_code=303)


@router.post("/{work_item_id}/status")
async def workitem_change_status(work_item_id: int, status: str = Form(...), reason: str | None = Form(default=None), session: AsyncSession = Depends(get_session)):
    current_user = await get_current_user(session)
    await change_status(session, work_item_id, StatusUpdate(status=status, reason=reason), current_user)
    return RedirectResponse(url=f"/workitems/{work_item_id}", status_code=303)


@router.post("/{work_item_id}/block")
async def workitem_block(work_item_id: int, is_blocked: bool = Form(...), reason: str | None = Form(default=None), session: AsyncSession = Depends(get_session)):
    current_user = await get_current_user(session)
    await set_block_state(session, work_item_id, BlockUpdate(is_blocked=is_blocked, reason=reason), current_user)
    return RedirectResponse(url=f"/workitems/{work_item_id}", status_code=303)


@router.post("/{work_item_id}/redirect")
async def workitem_redirect(work_item_id: int, main_executor_id: int = Form(...), reason: str = Form(...), session: AsyncSession = Depends(get_session)):
    current_user = await get_current_user(session)
    await redirect_work_item(session, work_item_id, RedirectUpdate(main_executor_id=main_executor_id, reason=reason), current_user)
    return RedirectResponse(url=f"/workitems/{work_item_id}", status_code=303)


@router.post("/{work_item_id}/comments")
async def workitem_add_comment(work_item_id: int, text: str = Form(...), session: AsyncSession = Depends(get_session)):
    current_user = await get_current_user(session)
    await add_comment(session, work_item_id, CommentCreate(text=text), current_user)
    return RedirectResponse(url=f"/workitems/{work_item_id}", status_code=303)


@router.post("/{work_item_id}/files")
async def workitem_upload_file(work_item_id: int, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    current_user = await get_current_user(session)
    await save_file(session, work_item_id, file, current_user)
    return RedirectResponse(url=f"/workitems/{work_item_id}", status_code=303)
