import asyncio
import logging
import os
from fastapi import FastAPI

from etl_beneficios import run_etl

logger = logging.getLogger(__name__)

ETL_INTERVAL_SECONDS = int(os.getenv("TRANSPARENCIA_ETL_INTERVAL_SECONDS", "300"))


def _is_enabled(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def run_etl_loop():
    logger.info("Starting Transparencia ETL worker (Parquet -> Postgres)...")
    while True:
        try:
            # We run it in a thread so polars/psycopg2 don't block the async loop
            await asyncio.to_thread(run_etl)
        except Exception as exc:
            logger.exception(f"Unexpected error in ETL worker loop: {exc}")

        await asyncio.sleep(ETL_INTERVAL_SECONDS)


async def start_etl_worker(app: FastAPI):
    if _is_enabled("TRANSPARENCIA_ETL_WORKER_ENABLED", "true"):
        app.state.etl_worker_task = asyncio.create_task(run_etl_loop())
        logger.info("Transparencia ETL worker task created successfully.")
    else:
        logger.info("Transparencia ETL worker is disabled via configuration.")


async def stop_etl_worker(app: FastAPI):
    task = getattr(app.state, "etl_worker_task", None)
    if task is not None and not task.done():
        logger.info("Stopping Transparencia ETL worker...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Transparencia ETL worker stopped.")
