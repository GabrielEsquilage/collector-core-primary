import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from sqlalchemy import text

from app import models
from app.api.transparencia import router as transparencia_router
from app.api.routes.ibge import router as ibge_router
from app.database import Base, engine
from app.services.startup_sync import start_startup_sync

logging.basicConfig(level=logging.INFO)


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS datacrypt"))
        conn.commit()

    Base.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await start_startup_sync(app)
    yield
    task = getattr(app.state, "startup_sync_task", None)
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="DataCrypt Collector", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/startup-sync")
def health_startup_sync():
    task = getattr(app.state, "startup_sync_task", None)
    return {
        "finished": getattr(app.state, "startup_sync_finished", False),
        "running": task is not None and not task.done(),
        "results": getattr(app.state, "startup_sync_results", {}),
        "errors": getattr(app.state, "startup_sync_errors", {}),
    }


app.include_router(ibge_router, prefix="/api/v1")
app.include_router(transparencia_router, prefix="/api/v1")
