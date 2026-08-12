from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.invoice.schema import InvoiceBatchResponse
from app.modules.invoice.service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.post("/batch", response_model=InvoiceBatchResponse, status_code=status.HTTP_201_CREATED)
async def trigger_invoice_batch(
    cycle_index: int = Query(default=1, ge=1, description="Cycle index (1-8)"),
    count: int | None = Query(default=None, ge=1, le=50, description="Optional invoice count"),
    db: AsyncSession = Depends(get_db),
) -> InvoiceBatchResponse:
    service = InvoiceService(session=db)
    batch = await service.issue_batch(cycle_index=cycle_index, count=count)
    return InvoiceBatchResponse.model_validate(batch)


@router.get("/batches", response_model=list[InvoiceBatchResponse])
async def list_invoice_batches(
    db: AsyncSession = Depends(get_db),
) -> Sequence[InvoiceBatchResponse]:
    service = InvoiceService(session=db)
    batches = await service.batch_repo.get_all()
    return [InvoiceBatchResponse.model_validate(b) for b in batches]
