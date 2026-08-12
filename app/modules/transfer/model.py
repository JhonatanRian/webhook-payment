from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class TransferRecord(BaseModel):
    __tablename__ = "transfer_records"

    stark_transfer_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    stark_invoice_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    event_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Gross amount in cents
    fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Fee in cents
    net_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Transferred amount in cents

    target_bank_code: Mapped[str] = mapped_column(String, nullable=False)
    target_branch: Mapped[str] = mapped_column(String, nullable=False)
    target_account: Mapped[str] = mapped_column(String, nullable=False)
    target_name: Mapped[str] = mapped_column(String, nullable=False)
    target_tax_id: Mapped[str] = mapped_column(String, nullable=False)
    target_account_type: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[str] = mapped_column(String, default="created", nullable=False)
