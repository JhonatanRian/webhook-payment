from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transfer.model import TransferRecord
from app.shared.repository import BaseRepository


class TransferUpdateSchema(BaseModel):
    status: str
    fee: int


async def test_base_repository_crud_operations(db_session: AsyncSession) -> None:
    repo = BaseRepository(model=TransferRecord, session=db_session)

    record = TransferRecord(
        amount=1000,
        fee=10,
        net_amount=990,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="created",
    )
    created_rec = await repo.create(record, autocommit=False)
    assert created_rec.id is not None

    retrieved = await repo.get(created_rec.id)
    assert retrieved is not None
    assert retrieved.id == created_rec.id

    updated_dict = await repo.update_partial(
        db_obj=retrieved,
        obj_in={"status": "processing"},
        autocommit=False,
    )
    assert updated_dict.status == "processing"

    schema = TransferUpdateSchema(status="success", fee=15)
    updated_schema = await repo.update_partial(
        db_obj=retrieved,
        obj_in=schema,
        autocommit=True,
    )
    assert updated_schema.status == "success"
    assert updated_schema.fee == 15

    await repo.delete(updated_schema, autocommit=False)
    after_delete = await repo.get(created_rec.id)
    assert after_delete is None

    rec2 = TransferRecord(
        amount=2000,
        fee=20,
        net_amount=1980,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="created",
    )
    c2 = await repo.create(rec2, autocommit=True)
    all_recs = await repo.get_all()
    assert len(all_recs) >= 1
    await repo.delete(c2, autocommit=True)
    assert await repo.get(c2.id) is None
