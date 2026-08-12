from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.exceptions.handlers import register_exception_handlers
from app.core.starkbank import setup_starkbank_user
from app.infra.db.session import init_db
from app.modules.invoice.router import router as invoice_router
from app.modules.scheduler.router import router as scheduler_router
from app.modules.scheduler.service import start_scheduler, stop_scheduler
from app.modules.transfer.router import router as transfer_router
from app.modules.webhook.router import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup actions
    setup_starkbank_user()
    await init_db()
    start_scheduler()
    yield
    # Shutdown actions
    stop_scheduler()


app = FastAPI(
    title="Stark Bank Webhook & Payment Integration",
    description="Automated invoice generation, webhook listener, and payout transfer system.",
    version="0.1.0",
    lifespan=lifespan,
)

# Register global exception handlers
register_exception_handlers(app)

# Include domain module routers
app.include_router(webhook_router)
app.include_router(invoice_router)
app.include_router(transfer_router)
app.include_router(scheduler_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "webhook-payment"}
