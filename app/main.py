from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import UPLOAD_DIR
from app.core.models import Department, Role, User
from app.db import AsyncSessionLocal, Base, engine
from app.modules.workitems.router import router as workitems_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        if (await session.execute(select(User).limit(1))).scalar_one_or_none() is None:
            dept = Department(name="Диспетчерская")
            role_admin = Role(name="admin")
            role_manager = Role(name="manager")
            session.add_all([dept, role_admin, role_manager])
            await session.flush()
            session.add_all([
                User(full_name="Иван Петров", email="ivan@example.com", hashed_password="demo", department_id=dept.id, role_id=role_admin.id),
                User(full_name="Мария Смирнова", email="maria@example.com", hashed_password="demo", department_id=dept.id, role_id=role_manager.id),
                User(full_name="Олег Кузнецов", email="oleg@example.com", hashed_password="demo", department_id=dept.id, role_id=role_manager.id),
            ])
            await session.commit()
    yield


app = FastAPI(title="WorkItems MVP", lifespan=lifespan)
app.include_router(workitems_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/workitems/")
