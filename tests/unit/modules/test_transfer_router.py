import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transfer.model import TransferRecord
from app.modules.transfer.router import list_transfers
from app.shared.pagination import PaginatedResult, PaginationParams


@pytest.mark.asyncio
async def test_list_transfers_direct(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    mock_transfer = TransferRecord(
        id=uuid.uuid4(),
        stark_transfer_id="tx_123",
        stark_invoice_id="inv_123",
        event_id="ev_123",
        amount=1000,
        fee=10,
        net_amount=990,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="success",
        created=now,
        updated=now,
    )
    mock_result = PaginatedResult(items=[mock_transfer], total=1, page=1, size=20)

    with patch(
        "app.modules.transfer.repository.TransferRepository.paginate_transfers",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        res = await list_transfers(
            params=PaginationParams(page=1, size=20),
            db=db_session,
        )
        assert res.total == 1
        assert len(res.items) == 1
        assert res.items[0].stark_transfer_id == "tx_123"
