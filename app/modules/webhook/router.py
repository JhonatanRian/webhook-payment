from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.webhook.schema import WebhookResponse
from app.modules.webhook.service import WebhookService

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post(
    "/starkbank",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Stark Bank Webhook Endpoint",
)
async def handle_starkbank_webhook(
    request: Request,
    digital_signature: str | None = Header(None, alias="Digital-Signature"),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    body_bytes = await request.body()
    service = WebhookService(session=db)
    result = await service.process_webhook(body_bytes=body_bytes, signature=digital_signature)
    return WebhookResponse(**result)
