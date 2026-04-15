from collections.abc import Awaitable, Callable, Mapping
from typing import TypedDict

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import TransparenciaCargaJob, TransparenciaCargaJobItem
from app.services.transparencia.beneficios import (
    collect_auxilio_brasil_municipio,
    collect_bolsa_familia_municipio,
    collect_novo_bolsa_familia_municipio,
)
from app.services.transparencia.jobs.definitions import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_COMPLETED_WITH_ERRORS,
    JOB_STATUS_FAILED,
    JOB_STATUS_RUNNING,
)
from app.services.transparencia.jobs.rate_limit import PortalRequestRateLimiter
from app.services.transparencia.jobs.repository import (
    claim_next_job_item,
    get_job,
    mark_job_item_failed,
    mark_job_item_success,
    refresh_job_counts,
    utcnow,
)



class JobItemExecutionMetrics(TypedDict):
    pages_collected: int
    records_received: int
    inserted: int
    updated: int


CollectorResult = Mapping[str, str | int]
BeneficioCollector = Callable[..., Awaitable[CollectorResult]]


def get_item_executor(tipo_beneficio: str) -> BeneficioCollector:
    executors: dict[str, BeneficioCollector] = {
        "bolsa_familia": collect_bolsa_familia_municipio,
        "auxilio_brasil": collect_auxilio_brasil_municipio,
        "novo_bolsa_familia": collect_novo_bolsa_familia_municipio,
    }
    executor = executors.get(tipo_beneficio)
    if executor is None:
        raise ValueError(f"Tipo de beneficio nao suportado no job runner: {tipo_beneficio}")
    return executor


async def execute_job_item(
    db: Session,
    item: TransparenciaCargaJobItem,
    limiter: PortalRequestRateLimiter,
) -> JobItemExecutionMetrics:
    executor = get_item_executor(item.tipo_beneficio)
    result = await executor(
        db,
        mes_ano=item.mes_ano,
        codigo_ibge=item.codigo_ibge,
        pagina_inicial=1,
        before_request=limiter.acquire,
    )
    return {
        "pages_collected": int(result["pages_collected"]),
        "records_received": int(result["records_received"]),
        "inserted": int(result["inserted"]),
        "updated": int(result["updated"]),
    }


def finalize_job(db: Session, job: TransparenciaCargaJob) -> TransparenciaCargaJob:
    job = refresh_job_counts(db, job)

    if job.pending_items > 0 or job.running_items > 0:
        job.status = JOB_STATUS_FAILED
    elif job.failed_items > 0:
        if job.success_items > 0:
            job.status = JOB_STATUS_COMPLETED_WITH_ERRORS
        else:
            job.status = JOB_STATUS_FAILED
    else:
        job.status = JOB_STATUS_COMPLETED

    job.finished_at = utcnow()
    db.commit()
    db.refresh(job)
    return refresh_job_counts(db, job)


async def run_job(job_id: int, *, max_attempts: int) -> None:
    db: Session = SessionLocal()
    try:
        job = get_job(db, job_id)
        if job is None:
            return

        job.status = JOB_STATUS_RUNNING
        job.started_at = job.started_at or utcnow()
        job.finished_at = None
        db.commit()
        db.refresh(job)
        job = refresh_job_counts(db, job)

        limiter = PortalRequestRateLimiter()

        while True:
            item = claim_next_job_item(db, job_id=job.id, max_attempts=max_attempts)
            if item is None:
                break

            try:
                metrics = await execute_job_item(db, item, limiter)
            except Exception as exc:
                mark_job_item_failed(db, item.id, str(exc))
            else:
                mark_job_item_success(db, item.id, metrics)

            job = refresh_job_counts(db, job)

        finalize_job(db, job)
    except Exception:
        job = get_job(db, job_id)
        if job is not None:
            job.status = JOB_STATUS_FAILED
            job.finished_at = utcnow()
            db.commit()
        raise
    finally:
        db.close()
