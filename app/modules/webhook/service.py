import asyncio
import logging
from typing import Any

import starkbank
from sqlalchemy.exc import DBAPIError, IntegrityError
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

logger = logging.getLogger(__name__)

type WebhookProcessResult = dict[str, str | None]

_webhook_lock = asyncio.Lock()


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.event_repo = WebhookEventRepository(session=session)
        self.invoice_repo = InvoiceRecordRepository(session=session)
        self.transfer_service = TransferService(session=session)

    @run_in_thread
    def _parse_event(self, body_bytes: bytes, signature: str) -> starkbank.Event:
        try:
            content_str = body_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise WebhookSignatureError(f"Invalid payload encoding: {err}") from err
        try:
            return starkbank.event.parse(content=content_str, signature=signature)
        except starkbank.error.InvalidSignatureError as err:
            raise WebhookSignatureError(f"Digital signature validation failed: {err}") from err
        except Exception as err:
            raise WebhookSignatureError(f"Failed to parse webhook event: {err}") from err

    async def _dispatch_credited_invoice(self, item_obj: Any, event_id: str) -> str | None:
        stark_item_id = getattr(item_obj, "id", None)
        amount = getattr(item_obj, "amount", 0)
        fee = getattr(item_obj, "fee", 0) or 0

        if stark_item_id:
            inv_record = await self.invoice_repo.get_by_stark_id(stark_item_id)
            if inv_record:
                inv_record.status = "credited"
                self.session.add(inv_record)

        transfer_rec = await self.transfer_service.transfer_credited_invoice(
            gross_amount=amount,
            fee=fee,
            stark_invoice_id=stark_item_id,
            event_id=event_id,
            autocommit=False,
        )
        return str(transfer_rec.id)

    async def _persist_and_dispatch(self, event: starkbank.Event, body_bytes: bytes) -> str | None:
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
        await self.event_repo.create(record, autocommit=False)

        transfer_record_id: str | None = None
        if subscription == "invoice" and log_type == "credited":
            invoice_obj = getattr(log_obj, "invoice", None)
            if invoice_obj:
                transfer_record_id = await self._dispatch_credited_invoice(invoice_obj, event.id)

        await self.session.commit()
        return transfer_record_id

    async def process_webhook(
        self, body_bytes: bytes, signature: str | None
    ) -> WebhookProcessResult:
        if not signature:
            raise WebhookSignatureError("Missing 'Digital-Signature' header.")

        event = await self._parse_event(body_bytes, signature)

        log_obj = getattr(event, "log", None)
        log_type = getattr(log_obj, "type", None) if log_obj else None
        subscription = getattr(event, "subscription", None)

        logger.info(
            "Received Stark Bank webhook event [event_id=%s, subscription=%s, log_type=%s]",
            event.id,
            subscription,
            log_type,
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Incoming Webhook Raw Payload [event_id=%s]: %s",
                event.id,
                body_bytes.decode("utf-8", errors="replace"),
            )

        async with _webhook_lock:
            try:
                transfer_record_id = await self._persist_and_dispatch(event, body_bytes)
                logger.info(
                    "Webhook processed successfully [event_id=%s, transfer_id=%s]",
                    event.id,
                    transfer_record_id,
                )
            except DuplicateEventError:
                raise
            except (IntegrityError, DBAPIError):
                if self.session.is_active:
                    await self.session.rollback()
                raise DuplicateEventError(event_id=event.id)
            except Exception:
                if self.session.is_active:
                    await self.session.rollback()
                raise

        return {
            "status": "success",
            "message": "Webhook processed successfully.",
            "event_id": event.id,
            "transfer_id": transfer_record_id,
        }
