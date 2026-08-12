from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvoiceCreate(BaseModel):
    amount: int = Field(..., description="Amount in cents (e.g., 1000 for R$10.00)")
    tax_id: str = Field(..., description="CPF or CNPJ of recipient")
    name: str = Field(..., description="Name of recipient")


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stark_invoice_id: str | None = None
    batch_id: UUID | None = None
    amount: int
    tax_id: str
    name: str
    status: str
    created: datetime


class InvoiceBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cycle_index: int
    invoice_count: int
    status: str
    created: datetime
    invoices: list[InvoiceResponse] = []
