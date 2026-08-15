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
from app.modules.transfer.repository import TransferRepository
from app.modules.transfer.service import TransferService
from app.modules.webhook.model import WebhookEventRecord
from app.modules.webhook.repository import WebhookEventRepository
from app.modules.webhook.schema import WebhookLogType, WebhookSubscription

logger = logging.getLogger(__name__)

type WebhookProcessResult = dict[str, str | None]

_webhook_lock = asyncio.Lock()


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.event_repo = WebhookEventRepository(session=session)
        self.invoice_repo = InvoiceRecordRepository(session=session)
        self.transfer_repo = TransferRepository(session=session)
        self.transfer_service = TransferService(session=session)

    @run_in_thread
    def _parse_event(self, body_bytes: bytes, signature: str) -> starkbank.Event:
        try:
            content_str = body_bytes.decode("utf-8")
            return starkbank.event.parse(content=content_str, signature=signature)
        except UnicodeDecodeError as err:
            raise WebhookSignatureError(f"Invalid payload encoding: {err}") from err
        except starkbank.error.InvalidSignatureError as err:
            raise WebhookSignatureError(f"Digital signature validation failed: {err}") from err
        except Exception as err:
            raise WebhookSignatureError(f"Failed to parse webhook event: {err}") from err

    async def _dispatch_credited_invoice(self, item_obj: Any, event_id: str) -> str | None:
        stark_item_id = getattr(item_obj, "id", None)
        amount = getattr(item_obj, "amount", 0)
        fee = getattr(item_obj, "fee", 0) or 0

        inv_record = (
            await self.invoice_repo.get_by_stark_id(stark_item_id) if stark_item_id else None
        )

        if not inv_record:
            logger.warning(
                "Received credited webhook for unknown invoice '%s'. Skipping payout transfer.",
                stark_item_id,
            )
            return None

        inv_record.status = WebhookLogType.CREDITED
        self.session.add(inv_record)

        transfer_rec = await self.transfer_service.transfer_credited_invoice(
            gross_amount=amount,
            fee=fee,
            stark_invoice_id=stark_item_id,
            event_id=event_id,
            autocommit=False,
        )
        return str(transfer_rec.id)

    async def _handle_invoice_event(self, log_obj: Any, event_id: str) -> str | None:
        """Handles 'invoice' subscription events. Only acts on 'credited' log type."""
        if getattr(log_obj, "type", None) != WebhookLogType.CREDITED:
            return None
        invoice_obj = getattr(log_obj, "invoice", None)
        if not invoice_obj:
            return None
        return await self._dispatch_credited_invoice(invoice_obj, event_id)

    async def _handle_transfer_event(self, log_obj: Any, event_id: str) -> str | None:  # noqa: ARG002
        """Handles 'transfer' subscription events. Updates local TransferRecord status."""
        transfer_obj = getattr(log_obj, "transfer", None)
        if not transfer_obj:
            return None
        stark_transfer_id = getattr(transfer_obj, "id", None)
        new_status = getattr(transfer_obj, "status", None)
        if not (stark_transfer_id and new_status):
            return None
        transfer_rec = await self.transfer_repo.get_by_stark_id(stark_transfer_id)
        if not transfer_rec:
            return None
        transfer_rec.status = new_status
        self.session.add(transfer_rec)
        logger.info(
            "Transfer status updated via webhook [stark_transfer_id=%s, status=%s]",
            stark_transfer_id,
            new_status,
        )
        return str(transfer_rec.id)

    async def _persist_and_dispatch(self, event: starkbank.Event, body_bytes: bytes) -> str | None:
        existing = await self.event_repo.get_by_event_id(event.id)
        if existing:
            raise DuplicateEventError(event_id=event.id)

        log_obj = getattr(event, "log", None)
        subscription = getattr(event, "subscription", None)

        record = WebhookEventRecord(
            event_id=event.id,
            subscription=subscription,
            log_type=getattr(log_obj, "type", None) if log_obj else None,
            payload=body_bytes.decode("utf-8", errors="replace"),
        )
        await self.event_repo.create(record, autocommit=False)

        _handlers = {
            WebhookSubscription.INVOICE: self._handle_invoice_event,
            WebhookSubscription.TRANSFER: self._handle_transfer_event,
        }

        handler = _handlers.get(subscription)
        transfer_record_id = await handler(log_obj, event.id) if handler else None

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
