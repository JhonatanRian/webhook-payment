import starkbank
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import run_in_thread
from app.core.exceptions.domain_exceptions import (
    DuplicateEventError,
    WebhookSignatureError,
)
from app.modules.invoice.repository import InvoiceRecordRepository
from app.modules.transfer.service import TransferService
from app.modules.webhook.model import WebhookEventRecord
from app.modules.webhook.repository import WebhookEventRepository

type WebhookProcessResult = dict[str, str | None]


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.event_repo = WebhookEventRepository(session=session)
        self.invoice_repo = InvoiceRecordRepository(session=session)
        self.transfer_service = TransferService(session=session)

    @run_in_thread
    def _parse_event(self, body_bytes: bytes, signature: str) -> starkbank.Event:
        content_str = body_bytes.decode("utf-8")
        try:
            return starkbank.event.parse(content=content_str, signature=signature)
        except starkbank.error.InvalidSignatureError as err:
            raise WebhookSignatureError(f"Digital signature validation failed: {err}") from err
        except Exception as err:
            raise WebhookSignatureError(f"Failed to parse webhook event: {err}") from err

    async def process_webhook(
        self, body_bytes: bytes, signature: str | None
    ) -> WebhookProcessResult:
        if not signature:
            raise WebhookSignatureError("Missing 'Digital-Signature' header.")

        event = await self._parse_event(body_bytes, signature)

        # Check idempotency
        existing = await self.event_repo.get_by_event_id(event.id)
        if existing:
            raise DuplicateEventError(event_id=event.id)

        log_obj = getattr(event, "log", None)
        log_type = getattr(log_obj, "type", None) if log_obj else None
        subscription = getattr(event, "subscription", None)

        record = WebhookEventRecord(
            event_id=event.id,
            subscription=subscription,
            log_type=log_type,
            payload=body_bytes.decode("utf-8", errors="replace"),
        )
        await self.event_repo.create(record, autocommit=True)

        transfer_record_id: str | None = None
        if subscription == "invoice" and log_type == "credited":
            invoice_obj = getattr(log_obj, "invoice", None)
            if invoice_obj:
                stark_invoice_id = getattr(invoice_obj, "id", None)
                amount = getattr(invoice_obj, "amount", 0)
                fee = getattr(invoice_obj, "fee", 0) or 0

                if stark_invoice_id:
                    inv_record = await self.invoice_repo.get_by_stark_id(stark_invoice_id)
                    if inv_record:
                        inv_record.status = "credited"
                        self.session.add(inv_record)

                transfer_rec = await self.transfer_service.transfer_credited_invoice(
                    gross_amount=amount,
                    fee=fee,
                    stark_invoice_id=stark_invoice_id,
                    event_id=event.id,
                )
                transfer_record_id = str(transfer_rec.id)

        return {
            "status": "success",
            "message": "Webhook processed successfully.",
            "event_id": event.id,
            "transfer_id": transfer_record_id,
        }
