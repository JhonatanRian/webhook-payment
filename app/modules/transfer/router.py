from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.transfer.schema import TransferResponse
from app.modules.transfer.service import TransferService

router = APIRouter(prefix="/api/v1/transfers", tags=["Transfers"])


@router.get("", response_model=list[TransferResponse])
async def list_transfers(
    db: AsyncSession = Depends(get_db),
) -> Sequence[TransferResponse]:
    service = TransferService(session=db)
    records = await service.repo.get_all()
    return [TransferResponse.model_validate(r) for r in records]
