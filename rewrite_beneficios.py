import re

with open('app/services/transparencia/beneficios.py', 'r') as f:
    content = f.read()

# Replace imports
content = content.replace(
    'from sqlalchemy.orm import Session',
    'from sqlalchemy.orm import Session\nfrom sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy.future import select'
)

# _load_existing_beneficio_rows
load_old = """def _load_existing_beneficio_rows(
    db: Session,
    spec: BeneficioSpec,
    *,
    data_referencia: date,
    codigo_ibge: str,
) -> dict[tuple[int, str, date, str], Any]:
    query = db.query(spec.model).filter(
        spec.model.tipo_beneficio == spec.tipo_beneficio,
        spec.model.data_referencia == data_referencia,
        spec.model.municipio_codigo_ibge == str(codigo_ibge),
    )
    return {_logical_key(_row_to_logical_dict(item)): item for item in query.all()}"""

load_new = """async def _load_existing_beneficio_rows(
    db: AsyncSession,
    spec: BeneficioSpec,
    *,
    data_referencia: date,
    codigo_ibge: str,
) -> dict[tuple[int, str, date, str], Any]:
    query = select(spec.model).filter(
        spec.model.tipo_beneficio == spec.tipo_beneficio,
        spec.model.data_referencia == data_referencia,
        spec.model.municipio_codigo_ibge == str(codigo_ibge),
    )
    result = await db.execute(query)
    return {_logical_key(_row_to_logical_dict(item)): item for item in result.scalars().all()}"""
content = content.replace(load_old, load_new)

# _upsert_beneficio_rows
upsert_old = """def _upsert_beneficio_rows(
    db: Session,
    spec: BeneficioSpec,
    *,
    records: list[dict[str, Any]],
    existing_by_key: dict[tuple[int, str, date, str], Any],
) -> tuple[int, int]:"""

upsert_new = """async def _upsert_beneficio_rows(
    db: AsyncSession,
    spec: BeneficioSpec,
    *,
    records: list[dict[str, Any]],
    existing_by_key: dict[tuple[int, str, date, str], Any],
) -> tuple[int, int]:"""
content = content.replace(upsert_old, upsert_new)
content = content.replace('    db.flush()\n    return inserted, updated', '    await db.flush()\n    return inserted, updated')

# _collect_beneficio_municipio
collect_old = """async def _collect_beneficio_municipio(
    db: Session,"""
collect_new = """async def _collect_beneficio_municipio(
    db: AsyncSession,"""
content = content.replace(collect_old, collect_new)

content = content.replace(
    'existing_by_key = _load_existing_beneficio_rows(',
    'existing_by_key = await _load_existing_beneficio_rows('
)

content = content.replace(
    'inserted, updated = _upsert_beneficio_rows(',
    'inserted, updated = await _upsert_beneficio_rows('
)

content = content.replace('        db.commit()\n    except Exception:\n        db.rollback()', '        await db.commit()\n    except Exception:\n        await db.rollback()')

# db: Session -> db: AsyncSession in collect_* methods
content = re.sub(
    r'(async def collect_[a-z_]+\(\n\s+)db: Session,',
    r'\1db: AsyncSession,',
    content
)
content = re.sub(
    r'(async def _collect_beneficio_municipio_ano\(\n\s+)db: Session,',
    r'\1db: AsyncSession,',
    content
)


with open('app/services/transparencia/beneficios.py', 'w') as f:
    f.write(content)

