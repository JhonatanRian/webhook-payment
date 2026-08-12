import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_transfers_api(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/transfers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
