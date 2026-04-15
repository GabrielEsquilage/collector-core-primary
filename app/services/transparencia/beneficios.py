from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    TransparenciaAuxilioBrasilMunicipio,
    TransparenciaNovoBolsaFamiliaMunicipio,
)
from app.services.transparencia.client import TransparenciaClient


def _parse_mes_ano(mes_ano: str) -> date:
    if len(mes_ano) != 6 or not mes_ano.isdigit():
        raise ValueError("mesAno must be in AAAAMM format")

    year = int(mes_ano[:4])
    month = int(mes_ano[4:])
    return date(year, month, 1)


def _parse_data_referencia(value: str | date) -> date:
    if isinstance(value, date):
        return value

    raw_value = str(value).strip()
    if len(raw_value) == 6 and raw_value.isdigit():
        return _parse_mes_ano(raw_value)

    return date.fromisoformat(raw_value.split("T", 1)[0])


def _normalize_beneficio_record(item: dict, *, tipo_beneficio: str) -> dict:
    return {
        "id_externo": int(item["id"]),
        "tipo_beneficio": tipo_beneficio,
        "data_referencia": _parse_data_referencia(item["dataReferencia"]),
        "municipio_codigo_ibge": str(item["municipio"]["codigoIBGE"]),
        "valor": Decimal(str(item["valor"])),
        "quantidade_beneficiados": int(item["quantidadeBeneficiados"]),
        "payload_json": item,
    }


def _logical_key(row: dict) -> tuple[int, str, date, str]:
    return (
        row["id_externo"],
        row["tipo_beneficio"],
        row["data_referencia"],
        row["municipio_codigo_ibge"],
    )


async def _collect_beneficio_municipio(
    db: Session,
    *,
    model,
    resource: str,
    tipo_beneficio: str,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
):
    data_referencia = _parse_mes_ano(mes_ano)
    pagina = pagina_inicial
    pages_collected = 0
    records_received = 0
    inserted = 0
    updated = 0

    query = db.query(model).filter(
        model.tipo_beneficio == tipo_beneficio,
        model.data_referencia == data_referencia,
        model.municipio_codigo_ibge == str(codigo_ibge),
    )
    existing = {
        (
            item.id_externo,
            item.tipo_beneficio,
            item.data_referencia,
            item.municipio_codigo_ibge,
        ): item
        for item in query.all()
    }

    try:
        async with TransparenciaClient() as client:
            while True:
                records = await client.fetch_page(
                    resource=resource,
                    pagina=pagina,
                    mesAno=mes_ano,
                    codigoIbge=str(codigo_ibge),
                )

                if not records:
                    break

                pages_collected += 1
                records_received += len(records)

                for item in records:
                    row = _normalize_beneficio_record(
                        item,
                        tipo_beneficio=tipo_beneficio,
                    )
                    key = _logical_key(row)
                    current = existing.get(key)

                    if current is None:
                        current = model(
                            **row,
                            collected_at=datetime.utcnow(),
                        )
                        db.add(current)
                        existing[key] = current
                        inserted += 1
                        continue

                    changed = False
                    for field in ("valor", "quantidade_beneficiados", "payload_json"):
                        value = row[field]
                        if getattr(current, field) != value:
                            setattr(current, field, value)
                            changed = True

                    if changed:
                        current.collected_at = datetime.utcnow()
                        updated += 1

                pagina += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "tipo_beneficio": tipo_beneficio,
        "mes_ano": mes_ano,
        "codigo_ibge": str(codigo_ibge),
        "pages_collected": pages_collected,
        "records_received": records_received,
        "inserted": inserted,
        "updated": updated,
    }


async def _collect_beneficio_municipio_ano(
    db: Session,
    *,
    model,
    resource: str,
    tipo_beneficio: str,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
):
    items = []
    pages_collected = 0
    records_received = 0
    inserted = 0
    updated = 0

    for mes in range(1, 13):
        mes_ano = f"{ano}{mes:02d}"
        result = await _collect_beneficio_municipio(
            db,
            model=model,
            resource=resource,
            tipo_beneficio=tipo_beneficio,
            mes_ano=mes_ano,
            codigo_ibge=codigo_ibge,
            pagina_inicial=pagina_inicial,
        )
        items.append(
            {
                "mes_ano": result["mes_ano"],
                "pages_collected": result["pages_collected"],
                "records_received": result["records_received"],
                "inserted": result["inserted"],
                "updated": result["updated"],
            }
        )
        pages_collected += result["pages_collected"]
        records_received += result["records_received"]
        inserted += result["inserted"]
        updated += result["updated"]

    return {
        "tipo_beneficio": tipo_beneficio,
        "codigo_ibge": str(codigo_ibge),
        "ano": ano,
        "months_processed": len(items),
        "pages_collected": pages_collected,
        "records_received": records_received,
        "inserted": inserted,
        "updated": updated,
        "items": items,
    }


def _list_beneficio_municipio(
    db: Session,
    *,
    model,
    tipo_beneficio: str,
    mes_ano: str | None = None,
    codigo_ibge: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    query = db.query(model).filter(model.tipo_beneficio == tipo_beneficio)

    if mes_ano is not None:
        query = query.filter(model.data_referencia == _parse_mes_ano(mes_ano))

    if codigo_ibge is not None:
        query = query.filter(model.municipio_codigo_ibge == str(codigo_ibge))

    total = query.count()
    items = (
        query.order_by(model.data_referencia.desc(), model.id_externo.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return total, items


async def collect_auxilio_brasil_municipio(
    db: Session,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
):
    return await _collect_beneficio_municipio(
        db,
        model=TransparenciaAuxilioBrasilMunicipio,
        resource="auxilio-brasil-por-municipio",
        tipo_beneficio="auxilio_brasil",
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
    )


async def collect_auxilio_brasil_municipio_ano(
    db: Session,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
):
    return await _collect_beneficio_municipio_ano(
        db,
        model=TransparenciaAuxilioBrasilMunicipio,
        resource="auxilio-brasil-por-municipio",
        tipo_beneficio="auxilio_brasil",
        ano=ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
    )


def list_auxilio_brasil_municipio(
    db: Session,
    mes_ano: str | None = None,
    codigo_ibge: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return _list_beneficio_municipio(
        db,
        model=TransparenciaAuxilioBrasilMunicipio,
        tipo_beneficio="auxilio_brasil",
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        limit=limit,
        offset=offset,
    )


async def collect_novo_bolsa_familia_municipio(
    db: Session,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
):
    return await _collect_beneficio_municipio(
        db,
        model=TransparenciaNovoBolsaFamiliaMunicipio,
        resource="novo-bolsa-familia-por-municipio",
        tipo_beneficio="novo_bolsa_familia",
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
    )


async def collect_novo_bolsa_familia_municipio_ano(
    db: Session,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
):
    return await _collect_beneficio_municipio_ano(
        db,
        model=TransparenciaNovoBolsaFamiliaMunicipio,
        resource="novo-bolsa-familia-por-municipio",
        tipo_beneficio="novo_bolsa_familia",
        ano=ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
    )


def list_novo_bolsa_familia_municipio(
    db: Session,
    mes_ano: str | None = None,
    codigo_ibge: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return _list_beneficio_municipio(
        db,
        model=TransparenciaNovoBolsaFamiliaMunicipio,
        tipo_beneficio="novo_bolsa_familia",
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        limit=limit,
        offset=offset,
    )
