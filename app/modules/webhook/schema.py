from enum import StrEnum

from pydantic import BaseModel


class WebhookSubscription(StrEnum):
    INVOICE = "invoice"
    TRANSFER = "transfer"


class WebhookLogType(StrEnum):
    CREDITED = "credited"
    CREATED = "created"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class WebhookResponse(BaseModel):
    status: str
    message: str
    event_id: str | None = None
    transfer_id: str | None = None
