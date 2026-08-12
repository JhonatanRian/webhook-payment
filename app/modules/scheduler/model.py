from datetime import UTC, datetime
from uuid import UUID as UUIDType

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class ScheduleCycleRecord(BaseModel):
    __tablename__ = "schedule_cycles"

    cycle_index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    invoice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    batch_id: Mapped[UUIDType | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
