from collections.abc import Awaitable, Callable, Mapping
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
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
from app.services.transparencia.jobs.rate_limit import (
    PortalRequestRateLimiter,
    get_shared_portal_request_limiter,
)
from app.services.transparencia.jobs.repository import (
    utcnow,
)
from app.services.transparencia.jobs.repository_async import (
    async_claim_next_job_item,
    async_get_job,
    async_mark_job_item_failed,
    async_mark_job_item_success,
    async_refresh_job_counts,
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


class JobItemContext(TypedDict):
    item_id: int
    tipo_beneficio: str
    mes_ano: str
    codigo_ibge: str


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
    db: AsyncSession,
    item: JobItemContext,
    limiter: PortalRequestRateLimiter,
) -> JobItemExecutionMetrics:
    executor = get_item_executor(item["tipo_beneficio"])
    result = await executor(
        db,
        mes_ano=item["mes_ano"],
        codigo_ibge=item["codigo_ibge"],
        pagina_inicial=1,
        before_request=limiter.acquire,
    )
    return {
        "pages_collected": int(result["pages_collected"]),
        "records_received": int(result["records_received"]),
        "inserted": int(result["inserted"]),
        "updated": int(result["updated"]),
    }


def _item_context_from_model(item: TransparenciaCargaJobItem) -> JobItemContext:
    return {
        "item_id": int(item.id),
        "tipo_beneficio": str(item.tipo_beneficio),
        "mes_ano": str(item.mes_ano),
        "codigo_ibge": str(item.codigo_ibge),
    }


async def _mark_job_running(job_id: int) -> TransparenciaCargaJob | None:
    async with AsyncSessionLocal() as db:
        job = await async_get_job(db, job_id)
        if job is None:
            return None

        job.status = JOB_STATUS_RUNNING
        job.started_at = job.started_at or utcnow()
        job.finished_at = None
        await db.commit()
        await db.refresh(job)
        return await async_refresh_job_counts(db, job)


async def _claim_next_job_item_context(
    job_id: int,
    *,
    max_attempts: int,
) -> JobItemContext | None:
    async with AsyncSessionLocal() as db:
        item = await async_claim_next_job_item(db, job_id=job_id, max_attempts=max_attempts)
        if item is None:
            return None
        return _item_context_from_model(item)


async def _refresh_job_counts(job_id: int) -> TransparenciaCargaJob | None:
    async with AsyncSessionLocal() as db:
        job = await async_get_job(db, job_id)
        if job is None:
            return None
        return await async_refresh_job_counts(db, job)


async def _mark_job_item_success_and_refresh(
    job_id: int,
    item_id: int,
    metrics: JobItemExecutionMetrics,
) -> TransparenciaCargaJob | None:
    async with AsyncSessionLocal() as db:
        await async_mark_job_item_success(db, item_id, metrics)
        job = await async_get_job(db, job_id)
        if job is None:
            return None
        return await async_refresh_job_counts(db, job)


async def _mark_job_item_failed_and_refresh(
    job_id: int,
    item_id: int,
    error_message: str,
) -> TransparenciaCargaJob | None:
    async with AsyncSessionLocal() as db:
        await async_mark_job_item_failed(db, item_id, error_message)
        job = await async_get_job(db, job_id)
        if job is None:
            return None
        return await async_refresh_job_counts(db, job)


async def _finalize_job(job_id: int) -> TransparenciaCargaJob | None:
    async with AsyncSessionLocal() as db:
        job = await async_get_job(db, job_id)
        if job is None:
            return None
        return await async_finalize_job(db, job)


async def _mark_job_failed(job_id: int) -> None:
    async with AsyncSessionLocal() as db:
        job = await async_get_job(db, job_id)
        if job is None:
            return
        job.status = JOB_STATUS_FAILED
        job.finished_at = utcnow()
        await db.commit()


async def async_finalize_job(db: AsyncSession, job: TransparenciaCargaJob) -> TransparenciaCargaJob:
    job = await async_refresh_job_counts(db, job)

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
    await db.commit()
    await db.refresh(job)
    return await async_refresh_job_counts(db, job)


async def run_job(job_id: int, *, max_attempts: int) -> None:
    try:
        job = await _mark_job_running(job_id)
        if job is None:
            return

        limiter = get_shared_portal_request_limiter()

        while True:
            item_context = await _claim_next_job_item_context(job.id, max_attempts=max_attempts)
            if item_context is None:
                break

            try:
                async with AsyncSessionLocal() as db:
                    metrics = await execute_job_item(db, item_context, limiter)
            except Exception as exc:
                job = await _mark_job_item_failed_and_refresh(
                    job.id,
                    item_context["item_id"],
                    str(exc),
                )
            else:
                job = await _mark_job_item_success_and_refresh(
                    job.id,
                    item_context["item_id"],
                    metrics,
                )
            if job is None:
                return

        await _finalize_job(job.id)
    except Exception:
        await _mark_job_failed(job_id)
        raise
