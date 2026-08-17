from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.dashboard.schema import DashboardSummaryResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated financial dashboard summary",
    description=(
        "Returns consolidated database-wide financial KPIs and statistics (total invoiced, "
        "total credited, total liquidated payouts, and conversion rate)."
    ),
)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    service = DashboardService(session=db)
    return await service.get_summary()
