from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransferStatus(StrEnum):
    PENDING = "pending"
    CREATED = "created"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class TargetAccountType(StrEnum):
    PAYMENT = "payment"
    CHECKING = "checking"
    SAVINGS = "savings"
    SALARY = "salary"


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stark_transfer_id: str | None = None
    stark_invoice_id: str | None = None
    event_id: str | None = None
    amount: int
    fee: int
    net_amount: int
    target_bank_code: str
    target_branch: str
    target_account: str
    target_name: str
    target_tax_id: str
    target_account_type: str
    status: str
    created: datetime
