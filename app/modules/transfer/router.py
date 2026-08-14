from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.transfer.schema import TransferResponse
from app.modules.transfer.service import TransferService
from app.shared.pagination import Page, PaginationParams

router = APIRouter(prefix="/api/v1/transfers", tags=["Transfers"])


@router.get(
    "",
    response_model=Page[TransferResponse],
    summary="List transfer records (paginated)",
    description=(
        "Returns a paginated list of all recorded payout transfers executed by the application."
    ),
)
async def list_transfers(
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Page[TransferResponse]:
    service = TransferService(session=db)
    result = await service.repo.paginate_transfers(params=params)
    items = [TransferResponse.model_validate(r) for r in result.items]
    return Page.create(items=items, total=result.total, params=params)
