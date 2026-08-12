import random
from typing import Any

import starkbank
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import run_in_thread
from app.modules.invoice.model import InvoiceBatch, InvoiceRecord
from app.modules.invoice.repository import InvoiceBatchRepository, InvoiceRecordRepository

type StarkInvoiceItem = dict[str, Any]


class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.batch_repo = InvoiceBatchRepository(session=session)
        self.record_repo = InvoiceRecordRepository(session=session)
        self.faker = Faker("pt_BR")

    @run_in_thread
    def _create_stark_invoices(self, items: list[StarkInvoiceItem]) -> list[starkbank.Invoice]:
        stark_invoices = [
            starkbank.Invoice(
                amount=item["amount"],
                tax_id=item["tax_id"],
                name=item["name"],
            )
            for item in items
        ]
        return starkbank.invoice.create(stark_invoices)

    def generate_random_invoice_data(self, count: int) -> list[StarkInvoiceItem]:
        items: list[StarkInvoiceItem] = []
        for _ in range(count):
            tax_id = self.faker.cpf().replace(".", "").replace("-", "").strip()
            name = self.faker.name()
            amount = random.randint(1000, 50000)
            items.append({"amount": amount, "tax_id": tax_id, "name": name})
        return items

    async def issue_batch(self, cycle_index: int, count: int | None = None) -> InvoiceBatch:
        if count is None:
            count = random.randint(8, 12)

        items_data = self.generate_random_invoice_data(count)

        batch = InvoiceBatch(
            cycle_index=cycle_index,
            invoice_count=count,
            status="pending",
        )
        await self.batch_repo.create(batch, autocommit=False)

        created_stark_invoices: list[starkbank.Invoice] = []
        try:
            created_stark_invoices = await self._create_stark_invoices(items_data)
            batch.status = "completed"
        except Exception as err:
            batch.status = "failed"
            await self.session.commit()
            raise err

        for item, stark_inv in zip(items_data, created_stark_invoices):
            rec = InvoiceRecord(
                stark_invoice_id=stark_inv.id,
                batch_id=batch.id,
                amount=stark_inv.amount if hasattr(stark_inv, "amount") else item["amount"],
                tax_id=item["tax_id"],
                name=item["name"],
                status=getattr(stark_inv, "status", "created"),
            )
            self.session.add(rec)

        await self.session.commit()
        await self.session.refresh(batch)
        return batch
