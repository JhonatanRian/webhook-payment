from uuid import UUID as UUIDType

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import BaseModel


class InvoiceBatch(BaseModel):
    __tablename__ = "invoice_batches"

    cycle_index: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="completed", nullable=False)

    invoices: Mapped[list["InvoiceRecord"]] = relationship(
        "InvoiceRecord",
        back_populates="batch",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InvoiceRecord(BaseModel):
    __tablename__ = "invoice_records"

    stark_invoice_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    batch_id: Mapped[UUIDType | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoice_batches.id"), nullable=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # in cents
    tax_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="created", nullable=False)

    batch: Mapped[InvoiceBatch | None] = relationship(
        "InvoiceBatch", back_populates="invoices", lazy="selectin"
    )
