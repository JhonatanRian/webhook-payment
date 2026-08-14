from collections.abc import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.infra.db.base import Base
from app.modules.invoice.model import InvoiceBatch, InvoiceRecord  # noqa: F401
from app.modules.scheduler.model import ScheduleCycleRecord, SchedulerStateRecord  # noqa: F401
from app.modules.transfer.model import TransferRecord  # noqa: F401
from app.modules.webhook.model import WebhookEventRecord  # noqa: F401

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except OperationalError as err:
        if "already exists" not in str(err).lower():
            raise
