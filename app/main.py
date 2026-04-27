import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from starlette.responses import RedirectResponse
from sqlalchemy import text

from app import models
from app.api.transparencia import router as transparencia_router
from app.api.routes.ibge import router as ibge_router
from app.database import Base, engine
from app.services.startup_sync import start_startup_sync

logging.basicConfig(level=logging.INFO)
ADMIN_DIST_DIR = Path(__file__).resolve().parents[1] / "frontend-admin" / "dist"
ADMIN_INDEX_FILE = ADMIN_DIST_DIR / "index.html"


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


def _get_admin_index() -> Path | None:
    if ADMIN_INDEX_FILE.exists():
        return ADMIN_INDEX_FILE
    return None


@app.get("/admin", include_in_schema=False)
def redirect_admin_root():
    return RedirectResponse(url="/admin/")


@app.get("/admin/", include_in_schema=False)
@app.get("/admin/{full_path:path}", include_in_schema=False)
def serve_admin(full_path: str = ""):
    requested_path = (ADMIN_DIST_DIR / full_path).resolve()

    try:
        requested_path.relative_to(ADMIN_DIST_DIR.resolve())
    except ValueError:
        return HTMLResponse("Caminho invalido.", status_code=400)

    if full_path and requested_path.is_file():
        return FileResponse(requested_path)

    admin_index = _get_admin_index()
    if admin_index is None:
        return HTMLResponse(
            (
                "<h1>Admin frontend nao encontrado</h1>"
                "<p>Execute <code>npm run build</code> em <code>frontend-admin</code> "
                "antes de abrir <code>/admin</code>.</p>"
            ),
            status_code=503,
        )

    return FileResponse(admin_index)
