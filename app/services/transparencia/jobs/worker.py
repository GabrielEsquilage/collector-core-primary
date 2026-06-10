import asyncio
import logging
import os
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import TransparenciaCargaJob
from app.services.transparencia.jobs.definitions import JOB_STATUS_PENDING
from app.services.transparencia.jobs.service import queue_job_run, run_job

logger = logging.getLogger(__name__)

WORKER_BATCH_SIZE = int(os.getenv("TRANSPARENCIA_WORKER_BATCH_SIZE", "8"))
WORKER_INTERVAL_SECONDS = int(os.getenv("TRANSPARENCIA_WORKER_INTERVAL_SECONDS", "90"))
WORKER_IDLE_INTERVAL_SECONDS = int(os.getenv("TRANSPARENCIA_WORKER_IDLE_INTERVAL_SECONDS", "5"))


def _is_enabled(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def run_worker_loop():
    logger.info("Starting Transparencia background jobs worker...")
    while True:
        executed_any = False
        try:
            job_ids = []
            def _fetch_and_queue():
                local_ids = []
                with SessionLocal() as db:
                    pending_jobs = (
                        db.query(TransparenciaCargaJob)
                        .filter(TransparenciaCargaJob.status == JOB_STATUS_PENDING)
                        .order_by(TransparenciaCargaJob.id.asc())
                        .limit(WORKER_BATCH_SIZE)
                        .all()
                    )

                    for job in pending_jobs:
                        try:
                            queue_job_run(db, job.id)
                            local_ids.append(job.id)
                        except Exception as exc:
                            logger.error(f"Failed to queue job {job.id}: {exc}")
                return local_ids

            job_ids = await asyncio.to_thread(_fetch_and_queue)

            if job_ids:
                executed_any = True
                logger.info(f"Executing {len(job_ids)} jobs concurrently: {job_ids}")

                async def safe_run_job(job_id: int):
                    try:
                        await run_job(job_id)
                        logger.info(f"Job {job_id} completed execution successfully.")
                    except Exception as exc:
                        logger.exception(f"Error executing job {job_id}: {exc}")

                await asyncio.gather(*(safe_run_job(jid) for jid in job_ids))
                logger.info(f"Finished execution of batch. Waiting {WORKER_INTERVAL_SECONDS} seconds...")
            else:
                logger.debug("No pending jobs found.")

        except Exception as exc:
            logger.exception(f"Unexpected error in background worker loop: {exc}")

        # If we executed jobs, we wait for 2 minutes as requested.
        # If there were no jobs, we check again after a short idle interval to stay responsive.
        sleep_time = WORKER_INTERVAL_SECONDS if executed_any else WORKER_IDLE_INTERVAL_SECONDS
        await asyncio.sleep(sleep_time)


async def start_jobs_worker(app: FastAPI):
    if _is_enabled("TRANSPARENCIA_BACKGROUND_WORKER_ENABLED", "true"):
        app.state.jobs_worker_task = asyncio.create_task(run_worker_loop())
        logger.info("Transparencia background worker task created successfully.")
    else:
        logger.info("Transparencia background worker is disabled via environment configuration.")


async def stop_jobs_worker(app: FastAPI):
    task = getattr(app.state, "jobs_worker_task", None)
    if task is not None and not task.done():
        logger.info("Stopping Transparencia background jobs worker...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Transparencia background jobs worker stopped.")
