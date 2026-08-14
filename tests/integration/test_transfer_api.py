from httpx import AsyncClient


async def test_list_transfers_api(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/transfers?page=1&size=20")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert data["page"] == 1
    assert data["size"] == 20
    assert isinstance(data["items"], list)
