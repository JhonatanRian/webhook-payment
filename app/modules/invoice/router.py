from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.invoice.schema import InvoiceBatchResponse, InvoiceResponse, InvoiceStatus
from app.modules.invoice.service import InvoiceService
from app.modules.scheduler.schema import TriggerType
from app.shared.pagination import Page, PaginationParams

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
    batch = await service.issue_batch(count=count, trigger_type=TriggerType.MANUAL)
    return InvoiceBatchResponse.model_validate(batch)


@router.get(
    "/batches",
    response_model=Page[InvoiceBatchResponse],
    summary="List invoice batches (paginated)",
    description=(
        "Returns a paginated list of issued invoice batches with their associated invoice items."
    ),
)
async def list_invoice_batches(
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Page[InvoiceBatchResponse]:
    service = InvoiceService(session=db)
    result = await service.batch_repo.paginate_batches(params=params)
    items = [InvoiceBatchResponse.model_validate(b) for b in result.items]
    return Page.create(items=items, total=result.total, params=params)


@router.get(
    "",
    response_model=Page[InvoiceResponse],
    summary="List individual invoices (paginated)",
    description=(
        "Returns a paginated list of all individual invoice records with optional status filtering."
    ),
)
async def list_invoices(
    status_filter: InvoiceStatus | None = Query(
        default=None,
        alias="status",
        description="Filter invoices by status (e.g. 'created', 'credited')",
    ),
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Page[InvoiceResponse]:
    service = InvoiceService(session=db)
    result = await service.record_repo.paginate_invoices(params=params, status=status_filter)
    items = [InvoiceResponse.model_validate(i) for i in result.items]
    return Page.create(items=items, total=result.total, params=params)
