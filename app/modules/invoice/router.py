from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.invoice.schema import InvoiceBatchResponse
from app.modules.invoice.service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.post(
    "/batch",
    response_model=InvoiceBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger invoice batch issuance",
    description="Manually triggers issuance of a batch of 8 to 12 randomized invoices.",
)
async def trigger_invoice_batch(
    count: int | None = Query(
        default=None, ge=1, le=50, description="Optional invoice count (defaults to random 8-12)"
    ),
    db: AsyncSession = Depends(get_db),
) -> InvoiceBatchResponse:
    service = InvoiceService(session=db)
    batch = await service.issue_batch(count=count, trigger_type="manual")
    return InvoiceBatchResponse.model_validate(batch)


@router.get(
    "/batches",
    response_model=list[InvoiceBatchResponse],
    summary="List invoice batches",
    description="Returns all issued invoice batches with their associated invoice items.",
)
async def list_invoice_batches(
    db: AsyncSession = Depends(get_db),
) -> Sequence[InvoiceBatchResponse]:
    service = InvoiceService(session=db)
    batches = await service.batch_repo.get_all()
    return [InvoiceBatchResponse.model_validate(b) for b in batches]
