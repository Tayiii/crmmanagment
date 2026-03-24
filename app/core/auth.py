from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import User


async def get_current_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).order_by(User.id).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        raise RuntimeError("No users available for demo authentication")
    return user
