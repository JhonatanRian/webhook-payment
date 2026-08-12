from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.webhook.model import WebhookEventRecord
from app.shared.repository import BaseRepository


class WebhookEventRepository(BaseRepository[WebhookEventRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=WebhookEventRecord, session=session)

    async def get_by_event_id(self, event_id: str) -> WebhookEventRecord | None:
        query = select(WebhookEventRecord).where(WebhookEventRecord.event_id == event_id)
        result = await self.session.execute(query)
        return result.scalars().first()
