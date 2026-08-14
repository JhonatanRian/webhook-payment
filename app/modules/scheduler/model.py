from datetime import UTC, datetime
from uuid import UUID as UUIDType

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class ScheduleCycleRecord(BaseModel):
    __tablename__ = "schedule_cycles"

    cycle_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    trigger_type: Mapped[str] = mapped_column(String, default="scheduled", nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    invoice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    batch_id: Mapped[UUIDType | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class SchedulerStateRecord(BaseModel):
    __tablename__ = "scheduler_state"

    key: Mapped[str] = mapped_column(String, unique=True, default="default", index=True)
    mode: Mapped[str] = mapped_column(String, default="once", nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_scheduled_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
