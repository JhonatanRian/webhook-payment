from pydantic import BaseModel


class WebhookResponse(BaseModel):
    status: str
    message: str
    event_id: str | None = None
    transfer_id: str | None = None
