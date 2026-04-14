from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import TransparenciaAuxilioBrasilMunicipio
from app.services.transparencia.client import TransparenciaClient


def _parse_mes_ano(mes_ano: str) -> date:
    if len(mes_ano) != 6 or not mes_ano.isdigit():
        raise ValueError("mesAno must be in AAAAMM format")

    year = int(mes_ano[:4])
    month = int(mes_ano[4:])
    return date(year, month, 1)


def _normalize_auxilio_brasil_record(item: dict) -> dict:
    return {
        "id_externo": int(item["id"]),
        "tipo_beneficio": "auxilio_brasil",
        "data_referencia": date.fromisoformat(item["dataReferencia"]),
        "municipio_codigo_ibge": str(item["municipio"]["codigoIBGE"]),
        "valor": Decimal(str(item["valor"])),
        "quantidade_beneficiados": int(item["quantidadeBeneficiados"]),
        "payload_json": item,
    }


async def collect_auxilio_brasil_municipio(
    db: Session,
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

    query = (
        db.query(TransparenciaAuxilioBrasilMunicipio)
        .filter(
            TransparenciaAuxilioBrasilMunicipio.tipo_beneficio == "auxilio_brasil",
            TransparenciaAuxilioBrasilMunicipio.data_referencia == data_referencia,
            TransparenciaAuxilioBrasilMunicipio.municipio_codigo_ibge == str(codigo_ibge),
        )
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
                    resource="auxilio-brasil-por-municipio",
                    pagina=pagina,
                    mesAno=mes_ano,
                    codigoIbge=str(codigo_ibge),
                )

                if not records:
                    break

                pages_collected += 1
                records_received += len(records)

                for item in records:
                    row = _normalize_auxilio_brasil_record(item)
                    key = (
                        row["id_externo"],
                        row["tipo_beneficio"],
                        row["data_referencia"],
                        row["municipio_codigo_ibge"],
                    )
                    current = existing.get(key)

                    if current is None:
                        current = TransparenciaAuxilioBrasilMunicipio(
                            **row,
                            collected_at=datetime.utcnow(),
                        )
                        db.add(current)
                        existing[key] = current
                        inserted += 1
                        continue

                    changed = False
                    for field in (
                        "valor",
                        "quantidade_beneficiados",
                        "payload_json",
                    ):
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
        "tipo_beneficio": "auxilio_brasil",
        "mes_ano": mes_ano,
        "pages_collected": pages_collected,
        "records_received": records_received,
        "inserted": inserted,
        "updated": updated,
    }


async def collect_auxilio_brasil_municipio_ano(
    db: Session,
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
        result = await collect_auxilio_brasil_municipio(
            db,
            mes_ano=mes_ano,
            codigo_ibge=codigo_ibge,
            pagina_inicial=pagina_inicial,
        )
        items.append(result)
        pages_collected += result["pages_collected"]
        records_received += result["records_received"]
        inserted += result["inserted"]
        updated += result["updated"]

    return {
        "tipo_beneficio": "auxilio_brasil",
        "codigo_ibge": str(codigo_ibge),
        "ano": ano,
        "months_processed": len(items),
        "pages_collected": pages_collected,
        "records_received": records_received,
        "inserted": inserted,
        "updated": updated,
        "items": items,
    }


def list_auxilio_brasil_municipio(
    db: Session,
    mes_ano: str | None = None,
    codigo_ibge: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    query = db.query(TransparenciaAuxilioBrasilMunicipio).filter(
        TransparenciaAuxilioBrasilMunicipio.tipo_beneficio == "auxilio_brasil"
    )

    if mes_ano is not None:
        query = query.filter(
            TransparenciaAuxilioBrasilMunicipio.data_referencia == _parse_mes_ano(mes_ano)
        )

    if codigo_ibge is not None:
        query = query.filter(
            TransparenciaAuxilioBrasilMunicipio.municipio_codigo_ibge == str(codigo_ibge)
        )

    total = query.count()
    items = (
        query.order_by(
            TransparenciaAuxilioBrasilMunicipio.data_referencia.desc(),
            TransparenciaAuxilioBrasilMunicipio.id_externo.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return total, items
