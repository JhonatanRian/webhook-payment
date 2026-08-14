import logging

import starkbank
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import run_in_thread
from app.core.config import settings
from app.core.exceptions.domain_exceptions import BusinessRuleViolationError
from app.core.exceptions.starkbank_mapper import handle_starkbank_exception
from app.modules.transfer.model import TransferRecord
from app.modules.transfer.repository import TransferRepository

logger = logging.getLogger(__name__)


class TransferService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TransferRepository(session=session)

    @run_in_thread
    def _execute_stark_transfer(self, transfer_obj: starkbank.Transfer) -> list[starkbank.Transfer]:
        return starkbank.transfer.create([transfer_obj])

    async def transfer_credited_invoice(
        self,
        gross_amount: int,
        fee: int,
        stark_invoice_id: str | None = None,
        event_id: str | None = None,
        autocommit: bool = True,
    ) -> TransferRecord:
        net_amount = gross_amount - fee
        if net_amount <= 0:
            raise BusinessRuleViolationError(
                f"Net amount ({net_amount} cents) must be positive to perform transfer."
            )

        logger.info(
            "Executing payout transfer for credited invoice: gross_amount=%d, fee=%d, "
            "net_amount=%d [stark_invoice_id=%s, event_id=%s]",
            gross_amount,
            fee,
            net_amount,
            stark_invoice_id,
            event_id,
        )

        stark_transfer_obj = starkbank.Transfer(
            amount=net_amount,
            name=settings.TARGET_NAME,
            tax_id=settings.TARGET_TAX_ID,
            bank_code=settings.TARGET_BANK_CODE,
            branch_code=settings.TARGET_BRANCH,
            account_number=settings.TARGET_ACCOUNT,
            account_type=settings.TARGET_ACCOUNT_TYPE,
        )

        record = TransferRecord(
            stark_invoice_id=stark_invoice_id,
            event_id=event_id,
            amount=gross_amount,
            fee=fee,
            net_amount=net_amount,
            target_bank_code=settings.TARGET_BANK_CODE,
            target_branch=settings.TARGET_BRANCH,
            target_account=settings.TARGET_ACCOUNT,
            target_name=settings.TARGET_NAME,
            target_tax_id=settings.TARGET_TAX_ID,
            target_account_type=settings.TARGET_ACCOUNT_TYPE,
            status="pending",
        )
        await self.repo.create(record, autocommit=False)

        try:
            created_transfers = await self._execute_stark_transfer(stark_transfer_obj)
            if created_transfers and len(created_transfers) > 0:
                record.stark_transfer_id = created_transfers[0].id
                record.status = getattr(created_transfers[0], "status", "success")
            else:
                record.status = "success"
        except Exception as err:
            logger.error(
                "Transfer execution failed [transfer_record_id=%s, stark_invoice_id=%s]: %s",
                record.id,
                stark_invoice_id,
                err,
            )
            record.status = "failed"
            if autocommit:
                await self.session.commit()
            raise handle_starkbank_exception(err) from err

        if autocommit:
            await self.session.commit()
            await self.session.refresh(record)

        logger.info(
            "Transfer completed successfully [transfer_record_id=%s, "
            "stark_transfer_id=%s, net_amount=%d]",
            record.id,
            record.stark_transfer_id,
            net_amount,
        )
        return record
