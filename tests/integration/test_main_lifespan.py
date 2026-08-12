from unittest.mock import patch

from fastapi import FastAPI

from app.main import lifespan


async def test_app_lifespan_execution() -> None:
    app = FastAPI()
    with patch("app.main.setup_starkbank_user"):
        async with lifespan(app):
            pass
