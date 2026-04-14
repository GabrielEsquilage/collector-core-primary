import json

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Estado, Municipio, Regiao
from app.services.ibge.ibge_service import fetch_municipios
from app.services.ibge.localidades_parser import parse_localidades


def _upsert_rows(db: Session, model, key_field: str, rows):
    existing = {
        getattr(item, key_field): item
        for item in db.query(model).all()
    }
    inserted = 0
    updated = 0

    for row in rows:
        key = row[key_field]
        current = existing.get(key)

        if current is None:
            db.add(model(**row))
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
    return {"inserted": inserted, "updated": updated}


def sync_localidades(db: Session):
    municipios = fetch_municipios()
    localidades = parse_localidades(municipios)

    try:
        summary = {
            "regioes": _upsert_rows(
                db, Regiao, "id_regiao", localidades["regioes"]
            ),
            "estados": _upsert_rows(
                db, Estado, "id_estado", localidades["estados"]
            ),
            "municipios": _upsert_rows(
                db, Municipio, "id_municipio", localidades["municipios"]
            ),
        }
        db.commit()
        return summary
    except Exception:
        db.rollback()
        raise


def sync_localidades_with_new_session():
    db = SessionLocal()
    try:
        return sync_localidades(db)
    finally:
        db.close()


if __name__ == "__main__":
    from app.main import init_db

    init_db()
    result = sync_localidades_with_new_session()
    print(json.dumps(result, ensure_ascii=False, indent=2))
