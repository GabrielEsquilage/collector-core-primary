from datetime import datetime
from collections.abc import Mapping
from typing import cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Estado, Municipio, TransparenciaCargaJob, TransparenciaCargaJobItem
from app.services.transparencia.jobs.definitions import (
    ITEM_STATUS_FAILED,
    ITEM_STATUS_PENDING,
    ITEM_STATUS_RUNNING,
    ITEM_STATUS_SUCCESS,
)


def utcnow() -> datetime:
    return datetime.utcnow()


def get_job(db: Session, job_id: int) -> TransparenciaCargaJob | None:
    return cast(
        TransparenciaCargaJob | None,
        db.query(TransparenciaCargaJob)
        .filter(TransparenciaCargaJob.id == job_id)
        .first(),
    )


def get_job_by_code(db: Session, job_code: str) -> TransparenciaCargaJob | None:
    return cast(
        TransparenciaCargaJob | None,
        db.query(TransparenciaCargaJob)
        .filter(TransparenciaCargaJob.job_code == job_code)
        .first(),
    )


def get_parana_municipio_codigos(db: Session) -> list[str]:
    rows = cast(
        list[tuple[int]],
        db.query(Municipio.id_municipio)
        .join(Estado, Estado.id_estado == Municipio.id_estado)
        .filter(Estado.sigla == "PR")
        .order_by(Municipio.id_municipio.asc())
        .all(),
    )
    return [str(municipio_id) for (municipio_id,) in rows]


def refresh_job_counts(db: Session, job: TransparenciaCargaJob) -> TransparenciaCargaJob:
    rows = cast(
        list[tuple[str, int]],
        db.query(
            TransparenciaCargaJobItem.status,
            func.count(TransparenciaCargaJobItem.id),
        )
        .filter(TransparenciaCargaJobItem.job_id == job.id)
        .group_by(TransparenciaCargaJobItem.status)
        .all(),
    )
    counts = {status: int(count) for status, count in rows}

    job.total_items = int(sum(counts.values()))
    job.pending_items = counts.get(ITEM_STATUS_PENDING, 0)
    job.running_items = counts.get(ITEM_STATUS_RUNNING, 0)
    job.success_items = counts.get(ITEM_STATUS_SUCCESS, 0)
    job.failed_items = counts.get(ITEM_STATUS_FAILED, 0)
    db.commit()
    db.refresh(job)
    return job


def create_job_items(
    db: Session,
    *,
    job: TransparenciaCargaJob,
    tipo_beneficio: str,
    resource: str,
    municipio_codigos: list[str],
    mes_anos: list[str],
) -> None:
    items: list[TransparenciaCargaJobItem] = []
    for codigo_ibge in municipio_codigos:
        for mes_ano in mes_anos:
            items.append(
                TransparenciaCargaJobItem(
                    job_id=job.id,
                    tipo_beneficio=tipo_beneficio,
                    resource=resource,
                    codigo_ibge=codigo_ibge,
                    mes_ano=mes_ano,
                    status=ITEM_STATUS_PENDING,
                )
            )

    db.add_all(items)


def list_jobs(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[TransparenciaCargaJob]]:
    query = db.query(TransparenciaCargaJob)

    if status is not None:
        query = query.filter(TransparenciaCargaJob.status == status)

    total = int(query.count())
    items = cast(
        list[TransparenciaCargaJob],
        query.order_by(TransparenciaCargaJob.created_at.desc(), TransparenciaCargaJob.id.desc())
        .offset(offset)
        .limit(limit)
        .all(),
    )
    return total, items


def count_retryable_failed_items(
    db: Session,
    *,
    job_id: int,
    max_attempts: int,
) -> int:
    return int(
        db.query(func.count(TransparenciaCargaJobItem.id))
        .filter(
            TransparenciaCargaJobItem.job_id == job_id,
            TransparenciaCargaJobItem.status == ITEM_STATUS_FAILED,
            TransparenciaCargaJobItem.attempts < max_attempts,
        )
        .scalar()
        or 0
    )


def claim_next_job_item(
    db: Session,
    *,
    job_id: int,
    max_attempts: int,
) -> TransparenciaCargaJobItem | None:
    item = cast(
        TransparenciaCargaJobItem | None,
        db.query(TransparenciaCargaJobItem)
        .filter(
            TransparenciaCargaJobItem.job_id == job_id,
            TransparenciaCargaJobItem.status == ITEM_STATUS_PENDING,
        )
        .order_by(
            TransparenciaCargaJobItem.mes_ano.asc(),
            TransparenciaCargaJobItem.codigo_ibge.asc(),
            TransparenciaCargaJobItem.id.asc(),
        )
        .first(),
    )

    if item is None:
        item = cast(
            TransparenciaCargaJobItem | None,
            db.query(TransparenciaCargaJobItem)
            .filter(
                TransparenciaCargaJobItem.job_id == job_id,
                TransparenciaCargaJobItem.status == ITEM_STATUS_FAILED,
                TransparenciaCargaJobItem.attempts < max_attempts,
            )
            .order_by(
                TransparenciaCargaJobItem.mes_ano.asc(),
                TransparenciaCargaJobItem.codigo_ibge.asc(),
                TransparenciaCargaJobItem.id.asc(),
            )
            .first(),
        )

    if item is None:
        return None

    item.status = ITEM_STATUS_RUNNING
    item.attempts = int(item.attempts) + 1
    item.started_at = utcnow()
    item.finished_at = None
    db.commit()
    db.refresh(item)
    return item


def mark_job_item_success(db: Session, item_id: int, result: Mapping[str, int]) -> None:
    item = cast(
        TransparenciaCargaJobItem | None,
        db.query(TransparenciaCargaJobItem)
        .filter(TransparenciaCargaJobItem.id == item_id)
        .first(),
    )
    if item is None:
        return

    item.status = ITEM_STATUS_SUCCESS
    item.last_error = None
    item.pages_collected = int(result["pages_collected"])
    item.records_received = int(result["records_received"])
    item.inserted = int(result["inserted"])
    item.updated = int(result["updated"])
    item.finished_at = utcnow()
    db.commit()


def mark_job_item_failed(db: Session, item_id: int, error_message: str) -> None:
    item = cast(
        TransparenciaCargaJobItem | None,
        db.query(TransparenciaCargaJobItem)
        .filter(TransparenciaCargaJobItem.id == item_id)
        .first(),
    )
    if item is None:
        return

    item.status = ITEM_STATUS_FAILED
    item.last_error = error_message[:2000]
    item.finished_at = utcnow()
    db.commit()


def get_latest_running_item_started_at(
    db: Session,
    *,
    job_id: int,
) -> datetime | None:
    return cast(
        datetime | None,
        db.query(func.max(TransparenciaCargaJobItem.started_at))
        .filter(
            TransparenciaCargaJobItem.job_id == job_id,
            TransparenciaCargaJobItem.status == ITEM_STATUS_RUNNING,
        )
        .scalar(),
    )


def fail_running_job_items(
    db: Session,
    *,
    job_id: int,
    error_message: str,
) -> int:
    items = cast(
        list[TransparenciaCargaJobItem],
        db.query(TransparenciaCargaJobItem)
        .filter(
            TransparenciaCargaJobItem.job_id == job_id,
            TransparenciaCargaJobItem.status == ITEM_STATUS_RUNNING,
        )
        .all(),
    )
    finished_at = utcnow()

    for item in items:
        item.status = ITEM_STATUS_FAILED
        item.last_error = error_message[:2000]
        item.finished_at = finished_at

    return len(items)
