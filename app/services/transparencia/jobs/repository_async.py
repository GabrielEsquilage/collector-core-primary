from collections.abc import Mapping
from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models import TransparenciaCargaJob, TransparenciaCargaJobItem
from app.services.transparencia.jobs.definitions import (
    ITEM_STATUS_FAILED,
    ITEM_STATUS_PENDING,
    ITEM_STATUS_RUNNING,
    ITEM_STATUS_SUCCESS,
)
from app.services.transparencia.jobs.repository import utcnow


async def async_get_job(db: AsyncSession, job_id: int) -> TransparenciaCargaJob | None:
    query = select(TransparenciaCargaJob).filter(TransparenciaCargaJob.id == job_id)
    result = await db.execute(query)
    return result.scalars().first()


async def async_refresh_job_counts(db: AsyncSession, job: TransparenciaCargaJob) -> TransparenciaCargaJob:
    query = select(
        TransparenciaCargaJobItem.status,
        func.count(TransparenciaCargaJobItem.id),
    ).filter(TransparenciaCargaJobItem.job_id == job.id).group_by(TransparenciaCargaJobItem.status)
    result = await db.execute(query)
    rows = result.all()
    counts = {status: int(count) for status, count in rows}

    job.total_items = int(sum(counts.values()))
    job.pending_items = counts.get(ITEM_STATUS_PENDING, 0)
    job.running_items = counts.get(ITEM_STATUS_RUNNING, 0)
    job.success_items = counts.get(ITEM_STATUS_SUCCESS, 0)
    job.failed_items = counts.get(ITEM_STATUS_FAILED, 0)
    await db.commit()
    await db.refresh(job)
    return job


async def async_claim_next_job_item(
    db: AsyncSession,
    *,
    job_id: int,
    max_attempts: int,
) -> TransparenciaCargaJobItem | None:
    query_pending = select(TransparenciaCargaJobItem).filter(
        TransparenciaCargaJobItem.job_id == job_id,
        TransparenciaCargaJobItem.status == ITEM_STATUS_PENDING,
    ).order_by(
        TransparenciaCargaJobItem.mes_ano.asc(),
        TransparenciaCargaJobItem.codigo_ibge.asc(),
        TransparenciaCargaJobItem.id.asc(),
    ).limit(1)
    
    result = await db.execute(query_pending)
    item = result.scalars().first()

    if item is None:
        query_failed = select(TransparenciaCargaJobItem).filter(
            TransparenciaCargaJobItem.job_id == job_id,
            TransparenciaCargaJobItem.status == ITEM_STATUS_FAILED,
            TransparenciaCargaJobItem.attempts < max_attempts,
        ).order_by(
            TransparenciaCargaJobItem.mes_ano.asc(),
            TransparenciaCargaJobItem.codigo_ibge.asc(),
            TransparenciaCargaJobItem.id.asc(),
        ).limit(1)
        result = await db.execute(query_failed)
        item = result.scalars().first()

    if item is None:
        return None

    item.status = ITEM_STATUS_RUNNING
    item.attempts = int(item.attempts) + 1
    item.started_at = utcnow()
    item.finished_at = None
    await db.commit()
    await db.refresh(item)
    return item


async def async_mark_job_item_success(db: AsyncSession, item_id: int, result: Mapping[str, int]) -> None:
    query = select(TransparenciaCargaJobItem).filter(TransparenciaCargaJobItem.id == item_id)
    res = await db.execute(query)
    item = res.scalars().first()
    if item is None:
        return

    item.status = ITEM_STATUS_SUCCESS
    item.last_error = None
    item.pages_collected = int(result["pages_collected"])
    item.records_received = int(result["records_received"])
    item.inserted = int(result["inserted"])
    item.updated = int(result["updated"])
    item.finished_at = utcnow()
    await db.commit()


async def async_mark_job_item_failed(db: AsyncSession, item_id: int, error_message: str) -> None:
    query = select(TransparenciaCargaJobItem).filter(TransparenciaCargaJobItem.id == item_id)
    res = await db.execute(query)
    item = res.scalars().first()
    if item is None:
        return

    item.status = ITEM_STATUS_FAILED
    item.last_error = error_message[:2000]
    item.finished_at = utcnow()
    await db.commit()


async def async_get_pending_jobs(db: AsyncSession, limit: int) -> list[TransparenciaCargaJob]:
    query = select(TransparenciaCargaJob).filter(
        TransparenciaCargaJob.status == "pending"
    ).order_by(TransparenciaCargaJob.id.asc()).limit(limit)
    res = await db.execute(query)
    return list(res.scalars().all())
