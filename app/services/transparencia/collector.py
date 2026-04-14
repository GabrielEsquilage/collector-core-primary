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


def _get_orgao(db: Session, model, id: int):
    return db.query(model).filter(model.id == id).one_or_none()


def _insert_changed_raw_rows(db: Session, model, rows: list[dict]):
    latest_by_codigo = {}
    for item in db.query(model).order_by(model.id.desc()).all():
        if item.codigo not in latest_by_codigo:
            latest_by_codigo[item.codigo] = item

    inserted = 0

    for row in rows:
        current = latest_by_codigo.get(row["codigo"])
        if current is not None:
            if (
                current.codigo == row["codigo"]
                and current.descricao == row["descricao"]
                and current.pagina_origem == row["pagina_origem"]
                and current.payload_original_json == row["payload_original_json"]
            ):
                continue

        new_row = model(**row)
        db.add(new_row)
        latest_by_codigo[row["codigo"]] = new_row
        inserted += 1

    db.flush()
    return inserted


def _upsert_clean_rows(db: Session, model, rows: list[dict]):
    existing = {item.codigo: item for item in db.query(model).all()}
    inserted = 0
    updated = 0

    for row in rows:
        current = existing.get(row["codigo"])
        if current is None:
            current = model(**row)
            db.add(current)
            existing[row["codigo"]] = current
            inserted += 1
            continue

        changed = False
        for field, value in row.items():
            if getattr(current, field) != value:
                setattr(current, field, value)
                changed = True

        if changed:
            updated += 1

    db.flush()
    return inserted, updated


async def _collect_orgaos(
    db: Session,
    resource: str,
    tipo_orgao: str,
    raw_model,
    clean_model,
    codigo: str | None = None,
    descricao: str | None = None,
):
    pagina = 1
    pages_collected = 0
    records_received = 0
    raw_inserted = 0
    clean_inserted = 0
    clean_updated = 0

    try:
        async with TransparenciaClient() as client:
            while True:
                records = await client.fetch_page(
                    resource=resource,
                    pagina=pagina,
                    codigo=codigo,
                    descricao=descricao,
                )

                if not records:
                    break

                pages_collected += 1
                records_received += len(records)

                raw_rows = [
                    normalize_raw_record(item, pagina)
                    for item in records
                ]
                raw_inserted += _insert_changed_raw_rows(db, raw_model, raw_rows)

                clean_rows = [normalize_clean_record(item) for item in records]
                inserted, updated = _upsert_clean_rows(db, clean_model, clean_rows)
                clean_inserted += inserted
                clean_updated += updated

                pagina += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "tipo_orgao": tipo_orgao,
        "pages_collected": pages_collected,
        "records_received": records_received,
        "raw_inserted": raw_inserted,
        "clean_inserted": clean_inserted,
        "clean_updated": clean_updated,
    }


async def collect_orgaos_siafi(
    db: Session,
    codigo: str | None = None,
    descricao: str | None = None,
):
    return await _collect_orgaos(
        db,
        resource="orgaos-siafi",
        tipo_orgao="siafi",
        raw_model=TransparenciaOrgaoSiafiRaw,
        clean_model=TransparenciaOrgaoSiafi,
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
        resource="orgaos-siape",
        tipo_orgao="siape",
        raw_model=TransparenciaOrgaoSiapeRaw,
        clean_model=TransparenciaOrgaoSiape,
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
    model,
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
