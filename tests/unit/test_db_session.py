from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db, init_db


async def test_init_db() -> None:
    await init_db()


async def test_get_db_generator() -> None:
    gen = get_db()
    session = await anext(gen)
    assert isinstance(session, AsyncSession)
    await gen.aclose()
