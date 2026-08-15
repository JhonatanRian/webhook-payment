import logging
import random
from typing import Any

import starkbank
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import run_in_thread
from app.core.exceptions.starkbank_mapper import handle_starkbank_exception
from app.modules.invoice.model import InvoiceBatch, InvoiceRecord
from app.modules.invoice.repository import InvoiceBatchRepository, InvoiceRecordRepository
from app.modules.invoice.schema import BatchStatus, InvoiceStatus
from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository
from app.modules.scheduler.schema import CycleStatus

logger = logging.getLogger(__name__)

type StarkItem = dict[str, Any]


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.batch_repo = InvoiceBatchRepository(session=session)
        self.record_repo = InvoiceRecordRepository(session=session)
        self.faker = Faker("pt_BR")

    @run_in_thread
    def _create_stark_invoices(self, items: list[StarkItem]) -> list[starkbank.Invoice]:
        stark_invoices = [
            starkbank.Invoice(
                amount=item["amount"],
                tax_id=item["tax_id"],
                name=item["name"],
            )
            for item in items
        ]
        return starkbank.invoice.create(stark_invoices)

    def generate_random_invoice_data(self, count: int) -> list[StarkItem]:
        items: list[StarkItem] = []
        for _ in range(count):
            tax_id = self.faker.cpf().replace(".", "").replace("-", "").strip()
            name = self.faker.name()
            amount = random.randint(1000, 50000)
            items.append({"amount": amount, "tax_id": tax_id, "name": name})
        return items

    async def issue_batch(
        self,
        cycle_index: int = 0,
        count: int | None = None,
        trigger_type: str | None = None,
    ) -> InvoiceBatch:
        if count is None:
            count = random.randint(8, 12)

        logger.info(
            "Issuing batch of %d invoices to Stark Bank API (cycle_index=%d)...",
            count,
            cycle_index,
        )

        items_data = self.generate_random_invoice_data(count)

        batch = InvoiceBatch(
            cycle_index=cycle_index,
            invoice_count=count,
            status=BatchStatus.COMPLETED,
        )
        await self.batch_repo.create(batch, autocommit=False)

        created_stark_items: list[Any] = []
        try:
            created_stark_items = await self._create_stark_invoices(items_data)
            batch.status = BatchStatus.COMPLETED
        except Exception as err:
            logger.error(
                "Invoice batch failed [batch_id=%s, count=%d]: %s",
                batch.id,
                count,
                err,
            )
            batch.status = BatchStatus.FAILED

            if trigger_type is not None:
                cycle_repo = ScheduleCycleRepository(session=self.session)
                manual_count = await cycle_repo.get_manual_trigger_count()
                cycle_rec = ScheduleCycleRecord(
                    cycle_index=cycle_index or (manual_count + 1),
                    status=CycleStatus.FAILED,
                    trigger_type=trigger_type,
                    invoice_count=0,
                    batch_id=batch.id,
                )
                self.session.add(cycle_rec)

            await self.session.commit()
            raise handle_starkbank_exception(err) from err

        for item, stark_item in zip(items_data, created_stark_items):
            rec = InvoiceRecord(
                stark_invoice_id=stark_item.id,
                batch_id=batch.id,
                amount=stark_item.amount if hasattr(stark_item, "amount") else item["amount"],
                tax_id=item["tax_id"],
                name=item["name"],
                status=getattr(stark_item, "status", InvoiceStatus.CREATED),
            )
            self.session.add(rec)

        if trigger_type is not None:
            cycle_repo = ScheduleCycleRepository(session=self.session)
            manual_count = await cycle_repo.get_manual_trigger_count()
            cycle_rec = ScheduleCycleRecord(
                cycle_index=cycle_index or (manual_count + 1),
                status=CycleStatus.COMPLETED,
                trigger_type=trigger_type,
                invoice_count=batch.invoice_count,
                batch_id=batch.id,
            )
            self.session.add(cycle_rec)

        await self.session.commit()
        await self.session.refresh(batch)
        logger.info(
            "Invoice batch completed successfully [batch_id=%s, count=%d]",
            batch.id,
            len(created_stark_items),
        )
        return batch
