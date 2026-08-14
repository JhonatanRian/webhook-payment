import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoice.model import InvoiceBatch, InvoiceRecord
from app.modules.invoice.repository import InvoiceBatchRepository, InvoiceRecordRepository
from app.modules.transfer.model import TransferRecord
from app.modules.transfer.repository import TransferRepository
from app.shared.pagination import Page, PaginationParams
from app.shared.repository import BaseRepository


def test_pagination_params_offset_and_limit() -> None:
    p1 = PaginationParams(page=1, size=20)
    assert p1.offset == 0
    assert p1.limit == 20

    p2 = PaginationParams(page=3, size=15)
    assert p2.offset == 30
    assert p2.limit == 15


def test_page_create_math_calculations() -> None:
    p1 = PaginationParams(page=1, size=20)
    page_obj = Page[str].create(items=["a", "b"], total=45, params=p1)
    assert page_obj.total == 45
    assert page_obj.pages == 3
    assert page_obj.page == 1
    assert page_obj.size == 20
    assert page_obj.has_next is True
    assert page_obj.has_previous is False

    p2 = PaginationParams(page=2, size=20)
    page_obj_2 = Page[str].create(items=["c", "d"], total=45, params=p2)
    assert page_obj_2.page == 2
    assert page_obj_2.has_next is True
    assert page_obj_2.has_previous is True

    p3 = PaginationParams(page=3, size=20)
    page_obj_3 = Page[str].create(items=["e"], total=45, params=p3)
    assert page_obj_3.page == 3
    assert page_obj_3.has_next is False
    assert page_obj_3.has_previous is True


def test_page_create_empty_dataset() -> None:
    p = PaginationParams(page=1, size=20)
    page_obj = Page[str].create(items=[], total=0, params=p)
    assert page_obj.total == 0
    assert page_obj.pages == 0
    assert page_obj.has_next is False
    assert page_obj.has_previous is False


@pytest.mark.asyncio
async def test_base_repository_paginate_empty_and_populated(db_session: AsyncSession) -> None:
    repo = BaseRepository(model=TransferRecord, session=db_session)

    res_empty = await repo.paginate(params=PaginationParams(page=1, size=10))
    assert res_empty.total == 0
    assert len(res_empty.items) == 0

    for i in range(1, 16):
        await repo.create(
            TransferRecord(
                amount=1000 * i,
                fee=10,
                net_amount=(1000 * i) - 10,
                target_bank_code="20018183",
                target_branch="0001",
                target_account="6341320293482496",
                target_name="Target",
                target_tax_id="20018183000180",
                target_account_type="payment",
                status="success",
            ),
            autocommit=False,
        )
    await db_session.commit()

    res_p1 = await repo.paginate(params=PaginationParams(page=1, size=10))
    assert res_p1.total == 15
    assert len(res_p1.items) == 10

    res_p2 = await repo.paginate(params=PaginationParams(page=2, size=10))
    assert res_p2.total == 15
    assert len(res_p2.items) == 5


@pytest.mark.asyncio
async def test_invoice_batch_repository_paginate(db_session: AsyncSession) -> None:
    batch_repo = InvoiceBatchRepository(session=db_session)

    for i in range(1, 4):
        batch = InvoiceBatch(cycle_index=i, invoice_count=2, status="completed")
        await batch_repo.create(batch, autocommit=False)
    await db_session.commit()

    all_batches = await batch_repo.get_all()
    assert len(all_batches) == 3

    res = await batch_repo.paginate_batches(params=PaginationParams(page=1, size=2))
    assert res.total == 3
    assert len(res.items) == 2


@pytest.mark.asyncio
async def test_invoice_record_repository_paginate_with_filter(db_session: AsyncSession) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)

    await inv_repo.create(
        InvoiceRecord(
            stark_invoice_id="inv_c1",
            amount=1000,
            tax_id="12345678909",
            name="Alice",
            status="created",
        ),
        autocommit=False,
    )
    await inv_repo.create(
        InvoiceRecord(
            stark_invoice_id="inv_c2",
            amount=2000,
            tax_id="12345678909",
            name="Bob",
            status="credited",
        ),
        autocommit=True,
    )

    all_res = await inv_repo.paginate_invoices(params=PaginationParams(page=1, size=10))
    assert all_res.total == 2

    credited_res = await inv_repo.paginate_invoices(
        params=PaginationParams(page=1, size=10), status="credited"
    )
    assert credited_res.total == 1
    assert credited_res.items[0].stark_invoice_id == "inv_c2"


@pytest.mark.asyncio
async def test_transfer_repository_paginate(db_session: AsyncSession) -> None:
    transfer_repo = TransferRepository(session=db_session)

    await transfer_repo.create(
        TransferRecord(
            amount=5000,
            fee=50,
            net_amount=4950,
            target_bank_code="20018183",
            target_branch="0001",
            target_account="6341320293482496",
            target_name="Target",
            target_tax_id="20018183000180",
            target_account_type="payment",
            status="success",
        ),
        autocommit=True,
    )

    res = await transfer_repo.paginate_transfers(params=PaginationParams(page=1, size=10))
    assert res.total == 1
    assert len(res.items) == 1
