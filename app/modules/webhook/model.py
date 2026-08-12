from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class WebhookEventRecord(BaseModel):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    subscription: Mapped[str | None] = mapped_column(String, nullable=True)
    log_type: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
