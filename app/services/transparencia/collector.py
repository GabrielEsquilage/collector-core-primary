from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    TransparenciaOrgaoSiafi,
    TransparenciaOrgaoSiafiRaw,
    TransparenciaOrgaoSiape,
    TransparenciaOrgaoSiapeRaw,
)
from app.services.transparencia.client import TransparenciaClient
from app.services.transparencia.normalizer import normalize_clean_record, normalize_raw_record


@dataclass(frozen=True)
class OrgaoCollectionSpec:
    resource: str
    tipo_orgao: str
    raw_model: Any
    clean_model: Any


ORGAO_COLLECTION_SPECS = {
    "siafi": OrgaoCollectionSpec(
        resource="orgaos-siafi",
        tipo_orgao="siafi",
        raw_model=TransparenciaOrgaoSiafiRaw,
        clean_model=TransparenciaOrgaoSiafi,
    ),
    "siape": OrgaoCollectionSpec(
        resource="orgaos-siape",
        tipo_orgao="siape",
        raw_model=TransparenciaOrgaoSiapeRaw,
        clean_model=TransparenciaOrgaoSiape,
    ),
}


def _get_orgao(db: Session, model: Any, id: int):
    return db.query(model).filter(model.id == id).one_or_none()


def _load_latest_raw_by_codigo(db: Session, model: Any) -> dict[str, Any]:
    latest_by_codigo: dict[str, Any] = {}
    for item in db.query(model).order_by(model.id.desc()).all():
        latest_by_codigo.setdefault(item.codigo, item)
    return latest_by_codigo


def _load_clean_by_codigo(db: Session, model: Any) -> dict[str, Any]:
    return {item.codigo: item for item in db.query(model).all()}


def _raw_row_matches(current: Any, row: dict[str, Any]) -> bool:
    return (
        current.codigo == row["codigo"]
        and current.descricao == row["descricao"]
        and current.pagina_origem == row["pagina_origem"]
        and current.payload_original_json == row["payload_original_json"]
    )


def _insert_changed_raw_rows(
    db: Session,
    model: Any,
    rows: list[dict[str, Any]],
    *,
    latest_by_codigo: dict[str, Any],
) -> int:
    inserted = 0

    for row in rows:
        current = latest_by_codigo.get(row["codigo"])
        if current is not None and _raw_row_matches(current, row):
            continue

        new_row = model(**row)
        db.add(new_row)
        latest_by_codigo[row["codigo"]] = new_row
        inserted += 1

    db.flush()
    return inserted


def _apply_row_updates(current: Any, row: dict[str, Any]) -> bool:
    changed = False
    for field, value in row.items():
        if getattr(current, field) != value:
            setattr(current, field, value)
            changed = True
    return changed


def _upsert_clean_rows(
    db: Session,
    model: Any,
    rows: list[dict[str, Any]],
    *,
    existing_by_codigo: dict[str, Any],
) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for row in rows:
        current = existing_by_codigo.get(row["codigo"])
        if current is None:
            current = model(**row)
            db.add(current)
            existing_by_codigo[row["codigo"]] = current
            inserted += 1
            continue

        if _apply_row_updates(current, row):
            updated += 1

    db.flush()
    return inserted, updated


def _build_collection_summary(tipo_orgao: str) -> dict[str, int | str]:
    return {
        "tipo_orgao": tipo_orgao,
        "pages_collected": 0,
        "records_received": 0,
        "raw_inserted": 0,
        "clean_inserted": 0,
        "clean_updated": 0,
    }


async def _collect_orgaos(
    db: Session,
    spec: OrgaoCollectionSpec,
    *,
    codigo: str | None = None,
    descricao: str | None = None,
):
    summary = _build_collection_summary(spec.tipo_orgao)
    latest_raw_by_codigo = _load_latest_raw_by_codigo(db, spec.raw_model)
    clean_by_codigo = _load_clean_by_codigo(db, spec.clean_model)

    try:
        async with TransparenciaClient() as client:
            async for pagina, records in client.iter_pages(
                spec.resource,
                codigo=codigo,
                descricao=descricao,
            ):
                summary["pages_collected"] += 1
                summary["records_received"] += len(records)

                raw_rows = [normalize_raw_record(item, pagina) for item in records]
                summary["raw_inserted"] += _insert_changed_raw_rows(
                    db,
                    spec.raw_model,
                    raw_rows,
                    latest_by_codigo=latest_raw_by_codigo,
                )

                clean_rows = [normalize_clean_record(item) for item in records]
                inserted, updated = _upsert_clean_rows(
                    db,
                    spec.clean_model,
                    clean_rows,
                    existing_by_codigo=clean_by_codigo,
                )
                summary["clean_inserted"] += inserted
                summary["clean_updated"] += updated

        db.commit()
    except Exception:
        db.rollback()
        raise

    return summary


async def collect_orgaos_siafi(
    db: Session,
    codigo: str | None = None,
    descricao: str | None = None,
):
    return await _collect_orgaos(
        db,
        ORGAO_COLLECTION_SPECS["siafi"],
        codigo=codigo,
        descricao=descricao,
    )


async def collect_orgaos_siafi_with_new_session(
    codigo: str | None = None,
    descricao: str | None = None,
):
    db = SessionLocal()
    try:
        return await collect_orgaos_siafi(db, codigo=codigo, descricao=descricao)
    finally:
        db.close()


async def collect_orgaos_siape(
    db: Session,
    codigo: str | None = None,
    descricao: str | None = None,
):
    return await _collect_orgaos(
        db,
        ORGAO_COLLECTION_SPECS["siape"],
        codigo=codigo,
        descricao=descricao,
    )


async def collect_orgaos_siape_with_new_session(
    codigo: str | None = None,
    descricao: str | None = None,
):
    db = SessionLocal()
    try:
        return await collect_orgaos_siape(db, codigo=codigo, descricao=descricao)
    finally:
        db.close()


def _list_orgaos(
    db: Session,
    model: Any,
    *,
    limit: int = 100,
    offset: int = 0,
    codigo: str | None = None,
    descricao: str | None = None,
    status_registro: str | None = None,
    elegivel_dashboard: bool | None = None,
):
    query = db.query(model)

    if codigo is not None:
        query = query.filter(model.codigo == codigo)

    if descricao is not None:
        query = query.filter(model.descricao.ilike(f"%{descricao}%"))

    if status_registro is not None:
        query = query.filter(model.status_registro == status_registro)

    if elegivel_dashboard is not None:
        query = query.filter(model.elegivel_dashboard == elegivel_dashboard)

    total = query.count()
    items = query.order_by(model.codigo).offset(offset).limit(limit).all()

    return total, items


def list_orgaos_siafi(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    codigo: str | None = None,
    descricao: str | None = None,
    status_registro: str | None = None,
    elegivel_dashboard: bool | None = None,
):
    return _list_orgaos(
        db,
        model=TransparenciaOrgaoSiafi,
        limit=limit,
        offset=offset,
        codigo=codigo,
        descricao=descricao,
        status_registro=status_registro,
        elegivel_dashboard=elegivel_dashboard,
    )


def get_orgao_siafi(db: Session, id: int):
    return _get_orgao(db, TransparenciaOrgaoSiafi, id=id)


def list_orgaos_siape(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    codigo: str | None = None,
    descricao: str | None = None,
    status_registro: str | None = None,
    elegivel_dashboard: bool | None = None,
):
    return _list_orgaos(
        db,
        model=TransparenciaOrgaoSiape,
        limit=limit,
        offset=offset,
        codigo=codigo,
        descricao=descricao,
        status_registro=status_registro,
        elegivel_dashboard=elegivel_dashboard,
    )


def get_orgao_siape(db: Session, id: int):
    return _get_orgao(db, TransparenciaOrgaoSiape, id=id)
