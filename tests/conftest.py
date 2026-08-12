from collections.abc import AsyncGenerator

import pytest
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.db.session import Base
from app.modules.invoice.model import InvoiceBatch, InvoiceRecord  # noqa: F401
from app.modules.scheduler.model import ScheduleCycleRecord  # noqa: F401
from app.modules.transfer.model import TransferRecord  # noqa: F401
from app.modules.webhook.model import WebhookEventRecord  # noqa: F401


@pytest.fixture(scope="session")
def faker_instance() -> Faker:
    return Faker("pt_BR")


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session
