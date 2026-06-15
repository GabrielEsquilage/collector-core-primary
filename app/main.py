import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from sqlalchemy import text

import os
from fastapi.middleware.cors import CORSMiddleware
from app import models
from app.api.transparencia import router as transparencia_router
from app.api.routes.ibge import router as ibge_router
from app.database import Base, engine
from app.services.startup_sync import start_startup_sync
from app.services.transparencia.jobs.worker import start_jobs_worker, stop_jobs_worker
from app.services.transparencia.jobs.etl_worker import start_etl_worker, stop_etl_worker

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
    await start_jobs_worker(app)
    await start_etl_worker(app)
    yield
    await stop_etl_worker(app)
    await stop_jobs_worker(app)


app = FastAPI(title="DataCrypt Collector", lifespan=lifespan)

cors_origins_str = os.getenv("CORS_ORIGINS", "")
if cors_origins_str:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
else:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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


from app.api.routes.admin import router as admin_router
from app.api.routes.siconfi import router as siconfi_router

app.include_router(ibge_router, prefix="/api/v1")
app.include_router(transparencia_router, prefix="/api/v1")
app.include_router(siconfi_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1/admin")
