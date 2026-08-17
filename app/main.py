import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions.handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.starkbank import setup_starkbank_user
from app.infra.db.session import init_db
from app.modules.dashboard.router import router as dashboard_router
from app.modules.invoice.router import router as invoice_router
from app.modules.scheduler.router import router as scheduler_router
from app.modules.scheduler.service import start_scheduler, stop_scheduler
from app.modules.transfer.router import router as transfer_router
from app.modules.webhook.router import router as webhook_router

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_starkbank_user()
    await init_db()
    await start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Stark Bank Webhook & Payment Integration",
    description="Automated invoice generation, webhook listener, and payout transfer system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)

app.include_router(webhook_router)
app.include_router(invoice_router)
app.include_router(transfer_router)
app.include_router(scheduler_router)
app.include_router(dashboard_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    logger.info("Health check endpoint accessed")
    return {"status": "ok", "service": "webhook-payment"}
