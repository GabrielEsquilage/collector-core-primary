import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import TransparenciaCargaJob
from app.services.transparencia.jobs.definitions import (
    JOB_PLANS_PR,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    TIPO_CARGA_BENEFICIO_MUNICIPIO,
    iter_mes_ano,
)
from app.services.transparencia.jobs.repository import (
    count_retryable_failed_items,
    create_job_items,
    fail_running_job_items,
    get_job as repository_get_job,
    get_job_by_code,
    get_latest_running_item_started_at,
    get_parana_municipio_codigos,
    list_jobs as repository_list_jobs,
    refresh_job_counts,
    utcnow,
)
from app.services.transparencia.jobs.runner import run_job as runner_run_job

MAX_JOB_ITEM_ATTEMPTS = int(os.getenv("TRANSPARENCIA_JOB_MAX_ATTEMPTS", "3"))
STALE_JOB_AFTER_MINUTES = int(os.getenv("TRANSPARENCIA_JOB_STALE_AFTER_MINUTES", "15"))


class TransparenciaCargaJobNotFoundError(ValueError):
    pass


class TransparenciaCargaJobConflictError(ValueError):
    pass


def _stale_threshold() -> datetime:
    return utcnow() - timedelta(minutes=STALE_JOB_AFTER_MINUTES)


def _recover_stale_job_execution(
    db: Session,
    job: TransparenciaCargaJob,
) -> TransparenciaCargaJob | None:
    if job.status not in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        return None

    reference_time = get_latest_running_item_started_at(db, job_id=job.id)
    if reference_time is None:
        reference_time = job.started_at or job.created_at

    if reference_time is None or reference_time > _stale_threshold():
        return None

    fail_running_job_items(
        db,
        job_id=job.id,
        error_message="Execucao anterior interrompida e marcada para retentativa manual.",
    )
    job.status = JOB_STATUS_FAILED
    job.finished_at = utcnow()
    db.commit()
    db.refresh(job)
    return refresh_job_counts(db, job)


def seed_parana_beneficio_jobs(
    db: Session,
) -> tuple[int, int, list[TransparenciaCargaJob]]:
    municipio_codigos: list[str] = get_parana_municipio_codigos(db)
    if not municipio_codigos:
        raise ValueError("Nao ha municipios do estado do Parana carregados na base do IBGE.")

    created_count = 0
    existing_count = 0
    jobs: list[TransparenciaCargaJob] = []

    for plan in JOB_PLANS_PR:
        existing_job: TransparenciaCargaJob | None = get_job_by_code(db, plan["job_code"])
        if existing_job is not None:
            existing_count += 1
            jobs.append(refresh_job_counts(db, existing_job))
            continue

        try:
            job: TransparenciaCargaJob = TransparenciaCargaJob(
                job_code=plan["job_code"],
                descricao=plan["descricao"],
                tipo_carga=TIPO_CARGA_BENEFICIO_MUNICIPIO,
                status=JOB_STATUS_PENDING,
                metadata_json={
                    "estado_sigla": "PR",
                    "tipo_beneficio": plan["tipo_beneficio"],
                    "resource": plan["resource"],
                    "mes_ano_inicio": plan["mes_ano_inicio"],
                    "mes_ano_fim": plan["mes_ano_fim"],
                    "municipios": len(municipio_codigos),
                },
            )
            db.add(job)
            db.flush()

            create_job_items(
                db,
                job=job,
                tipo_beneficio=plan["tipo_beneficio"],
                resource=plan["resource"],
                municipio_codigos=municipio_codigos,
                mes_anos=iter_mes_ano(plan["mes_ano_inicio"], plan["mes_ano_fim"]),
            )

            db.commit()
            db.refresh(job)
        except Exception:
            db.rollback()
            raise

        created_count += 1
        jobs.append(refresh_job_counts(db, job))

    jobs.sort(key=lambda item: str(item.job_code))
    return created_count, existing_count, jobs


def list_jobs(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[TransparenciaCargaJob]]:
    return repository_list_jobs(db, status=status, limit=limit, offset=offset)


def get_job(db: Session, job_id: int) -> TransparenciaCargaJob | None:
    job: TransparenciaCargaJob | None = repository_get_job(db, job_id)
    if job is None:
        return None
    return refresh_job_counts(db, job)


def queue_job_run(db: Session, job_id: int) -> TransparenciaCargaJob:
    job: TransparenciaCargaJob | None = repository_get_job(db, job_id)
    if job is None:
        raise TransparenciaCargaJobNotFoundError(f"Job {job_id} not found")

    job = refresh_job_counts(db, job)

    if job.status in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        recovered_job = _recover_stale_job_execution(db, job)
        if recovered_job is None:
            raise TransparenciaCargaJobConflictError(
                f"Job {job_id} ja esta em execucao."
            )
        job = recovered_job

    retryable_failed_items = count_retryable_failed_items(
        db,
        job_id=job.id,
        max_attempts=MAX_JOB_ITEM_ATTEMPTS,
    )

    if job.pending_items == 0 and retryable_failed_items == 0:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} nao possui itens pendentes para execucao."
        )

    job.status = JOB_STATUS_QUEUED
    job.started_at = job.started_at or utcnow()
    job.finished_at = None
    db.commit()
    db.refresh(job)
    return refresh_job_counts(db, job)


async def run_job(job_id: int) -> None:
    await runner_run_job(job_id, max_attempts=MAX_JOB_ITEM_ATTEMPTS)
