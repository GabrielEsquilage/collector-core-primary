from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import String, cast
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import (
    Estado,
    Municipio,
    TransparenciaAuxilioBrasilMunicipio,
    TransparenciaBolsaFamiliaMunicipio,
    TransparenciaNovoBolsaFamiliaMunicipio,
)
from app.services.transparencia.client import TransparenciaClient


class BeneficioPeriodoInvalidoError(ValueError):
    pass


BOLSA_FAMILIA_START = date(2013, 1, 1)
BOLSA_FAMILIA_END = date(2021, 10, 1)
AUXILIO_BRASIL_START = date(2021, 11, 1)
AUXILIO_BRASIL_END = date(2023, 2, 1)
NOVO_BOLSA_FAMILIA_START = date(2023, 3, 1)
BENEFICIO_MUTABLE_FIELDS = ("valor", "quantidade_beneficiados", "payload_json")


@dataclass(frozen=True)
class PeriodoMensalSpec:
    start: date
    end: date | None
    transition_years: frozenset[int]
    accepted_message: str


@dataclass(frozen=True)
class PeriodoAnualSpec:
    validator: Callable[[int], bool]
    transition_years: frozenset[int]
    accepted_message: str


@dataclass(frozen=True)
class BeneficioSpec:
    tipo_beneficio: str
    display_name: str
    resource: str
    model: Any
    periodo_mensal: PeriodoMensalSpec
    periodo_anual: PeriodoAnualSpec


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


def _normalize_estado_sigla(estado_sigla: str) -> str:
    normalized = estado_sigla.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("estadoSigla must contain exactly 2 letters")
    return normalized


def _is_bolsa_familia_annual_year(ano: int) -> bool:
    return 2013 <= ano <= 2020


def _is_auxilio_brasil_annual_year(ano: int) -> bool:
    return ano == 2022


def _is_novo_bolsa_familia_annual_year(ano: int) -> bool:
    return ano >= 2024


BENEFICIO_SPECS = {
    "auxilio_brasil": BeneficioSpec(
        tipo_beneficio="auxilio_brasil",
        display_name="Auxilio Brasil",
        resource="auxilio-brasil-por-municipio",
        model=TransparenciaAuxilioBrasilMunicipio,
        periodo_mensal=PeriodoMensalSpec(
            start=AUXILIO_BRASIL_START,
            end=AUXILIO_BRASIL_END,
            transition_years=frozenset({2021, 2023}),
            accepted_message="competencias entre 202111 e 202302",
        ),
        periodo_anual=PeriodoAnualSpec(
            validator=_is_auxilio_brasil_annual_year,
            transition_years=frozenset({2021, 2023}),
            accepted_message="o ano de 2022",
        ),
    ),
    "bolsa_familia": BeneficioSpec(
        tipo_beneficio="bolsa_familia",
        display_name="Bolsa Familia",
        resource="bolsa-familia-por-municipio",
        model=TransparenciaBolsaFamiliaMunicipio,
        periodo_mensal=PeriodoMensalSpec(
            start=BOLSA_FAMILIA_START,
            end=BOLSA_FAMILIA_END,
            transition_years=frozenset({2021}),
            accepted_message="competencias entre 201301 e 202110",
        ),
        periodo_anual=PeriodoAnualSpec(
            validator=_is_bolsa_familia_annual_year,
            transition_years=frozenset({2021}),
            accepted_message="anos de 2013 ate 2020",
        ),
    ),
    "novo_bolsa_familia": BeneficioSpec(
        tipo_beneficio="novo_bolsa_familia",
        display_name="Novo Bolsa Familia",
        resource="novo-bolsa-familia-por-municipio",
        model=TransparenciaNovoBolsaFamiliaMunicipio,
        periodo_mensal=PeriodoMensalSpec(
            start=NOVO_BOLSA_FAMILIA_START,
            end=None,
            transition_years=frozenset({2023}),
            accepted_message="competencias a partir de 202303",
        ),
        periodo_anual=PeriodoAnualSpec(
            validator=_is_novo_bolsa_familia_annual_year,
            transition_years=frozenset({2023}),
            accepted_message="anos de 2024 em diante",
        ),
    ),
}


def _get_beneficio_spec(tipo_beneficio: str) -> BeneficioSpec:
    spec = BENEFICIO_SPECS.get(tipo_beneficio)
    if spec is None:
        raise ValueError(f"Tipo de beneficio nao suportado: {tipo_beneficio}")
    return spec


def _is_date_in_range(value: date, start: date, end: date | None) -> bool:
    return value >= start and (end is None or value <= end)


def _validate_mes_ano(spec: BeneficioSpec, mes_ano: str) -> None:
    data_referencia = _parse_mes_ano(mes_ano)
    if _is_date_in_range(
        data_referencia,
        spec.periodo_mensal.start,
        spec.periodo_mensal.end,
    ):
        return

    if data_referencia.year in spec.periodo_mensal.transition_years:
        raise BeneficioPeriodoInvalidoError(
            f"mesAno {mes_ano} pertence a um periodo de transicao do {spec.display_name}. "
            f"Este endpoint aceita apenas {spec.periodo_mensal.accepted_message}."
        )

    raise BeneficioPeriodoInvalidoError(
        f"mesAno {mes_ano} nao pertence ao periodo do {spec.display_name}. "
        f"Este endpoint aceita apenas {spec.periodo_mensal.accepted_message}."
    )


def _validate_ano(spec: BeneficioSpec, ano: int) -> None:
    if spec.periodo_anual.validator(ano):
        return

    if ano in spec.periodo_anual.transition_years:
        raise BeneficioPeriodoInvalidoError(
            f"ano {ano} e um ano de transicao para o {spec.display_name}. "
            "Este endpoint anual aceita apenas anos totalmente cobertos pelo beneficio. "
            "Use a coleta mensal para esse ano."
        )

    raise BeneficioPeriodoInvalidoError(
        f"ano {ano} nao pertence ao periodo do {spec.display_name}. "
        f"Este endpoint anual aceita apenas {spec.periodo_anual.accepted_message}."
    )


def validate_beneficio_mes_ano(tipo_beneficio: str, mes_ano: str) -> None:
    _validate_mes_ano(_get_beneficio_spec(tipo_beneficio), mes_ano)


def validate_beneficio_ano(tipo_beneficio: str, ano: int) -> None:
    _validate_ano(_get_beneficio_spec(tipo_beneficio), ano)


def _normalize_beneficio_record(
    item: dict[str, Any],
    *,
    spec: BeneficioSpec,
) -> dict[str, Any]:
    return {
        "id_externo": int(item["id"]),
        "tipo_beneficio": spec.tipo_beneficio,
        "data_referencia": _parse_data_referencia(item["dataReferencia"]),
        "municipio_codigo_ibge": str(item["municipio"]["codigoIBGE"]),
        "valor": Decimal(str(item["valor"])),
        "quantidade_beneficiados": int(item["quantidadeBeneficiados"]),
        "payload_json": item,
    }


def _logical_key(row: dict[str, Any]) -> tuple[int, str, date, str]:
    return (
        row["id_externo"],
        row["tipo_beneficio"],
        row["data_referencia"],
        row["municipio_codigo_ibge"],
    )











import json
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

async def _save_beneficio_to_parquet(
    spec: BeneficioSpec,
    records: list[dict[str, Any]],
    mes_ano: str,
    codigo_ibge: str,
) -> int:
    if not records:
        return 0

    ano = mes_ano[:4]
    mes = mes_ano[4:]
    
    DATA_LAKE_PATH = Path("app/data/parquet")
    partition_dir = DATA_LAKE_PATH / spec.tipo_beneficio / f"ano={ano}" / f"mes={mes}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = partition_dir / f"{codigo_ibge}.parquet"
    
    normalized_records = []
    for item in records:
        row = _normalize_beneficio_record(item, spec=spec)
        row["data_referencia"] = row["data_referencia"].isoformat()
        row["valor"] = float(row["valor"])
        row["payload_json"] = json.dumps(row["payload_json"])
        normalized_records.append(row)
    
    table = pa.Table.from_pylist(normalized_records)
    pq.write_table(table, file_path)
    return len(normalized_records)

def _build_mensal_summary(
    spec: BeneficioSpec,
    *,
    mes_ano: str,
    codigo_ibge: str,
) -> dict[str, int | str]:
    return {
        "tipo_beneficio": spec.tipo_beneficio,
        "mes_ano": mes_ano,
        "codigo_ibge": str(codigo_ibge),
        "pages_collected": 0,
        "records_received": 0,
        "inserted": 0,
        "updated": 0,
    }


async def _collect_beneficio_municipio(
    db: AsyncSession,
    *,
    spec: BeneficioSpec,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    summary = _build_mensal_summary(spec, mes_ano=mes_ano, codigo_ibge=codigo_ibge)
    
    all_records = []
    async with TransparenciaClient(before_request=before_request) as client:
        async for _, records in client.iter_pages(
            spec.resource,
            start_page=pagina_inicial,
            mesAno=mes_ano,
            codigoIbge=str(codigo_ibge),
        ):
            summary["pages_collected"] += 1
            summary["records_received"] += len(records)
            all_records.extend(records)

    if all_records:
        inserted = await _save_beneficio_to_parquet(spec, all_records, mes_ano, codigo_ibge)
        summary["inserted"] = inserted

    return summary


def _iter_mes_ano_for_year(ano: int):
    for mes in range(1, 13):
        yield f"{ano}{mes:02d}"


async def _collect_beneficio_municipio_ano(
    db: AsyncSession,
    *,
    spec: BeneficioSpec,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    items = []
    pages_collected = 0
    records_received = 0
    inserted = 0
    updated = 0

    for mes_ano in _iter_mes_ano_for_year(ano):
        result = await _collect_beneficio_municipio(
            db,
            spec=spec,
            mes_ano=mes_ano,
            codigo_ibge=codigo_ibge,
            pagina_inicial=pagina_inicial,
            before_request=before_request,
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
        "tipo_beneficio": spec.tipo_beneficio,
        "codigo_ibge": str(codigo_ibge),
        "ano": ano,
        "months_processed": len(items),
        "pages_collected": pages_collected,
        "records_received": records_received,
        "inserted": inserted,
        "updated": updated,
        "items": items,
    }


def _apply_estado_sigla_filter(query, model: Any, estado_sigla: str):
    return (
        query.join(
            Municipio,
            cast(Municipio.id_municipio, String) == model.municipio_codigo_ibge,
        )
        .join(Estado, Estado.id_estado == Municipio.id_estado)
        .filter(Estado.sigla == _normalize_estado_sigla(estado_sigla))
    )


def _list_beneficio_municipio(
    db: Session,
    *,
    spec: BeneficioSpec,
    ano: int | None = None,
    codigo_ibge: str | None = None,
    estado_sigla: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    model = spec.model
    query = db.query(model).filter(model.tipo_beneficio == spec.tipo_beneficio)

    if ano is not None:
        from sqlalchemy import extract
        query = query.filter(extract('year', model.data_referencia) == ano)

    if codigo_ibge is not None:
        query = query.filter(model.municipio_codigo_ibge == str(codigo_ibge))

    if estado_sigla is not None:
        query = _apply_estado_sigla_filter(query, model, estado_sigla)

    total = query.count()
    items = (
        query.order_by(model.data_referencia.desc(), model.id_externo.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return total, items


async def collect_auxilio_brasil_municipio(
    db: AsyncSession,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    spec = _get_beneficio_spec("auxilio_brasil")
    _validate_mes_ano(spec, mes_ano)
    return await _collect_beneficio_municipio(
        db,
        spec=spec,
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
        before_request=before_request,
    )


async def collect_bolsa_familia_municipio(
    db: AsyncSession,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    spec = _get_beneficio_spec("bolsa_familia")
    _validate_mes_ano(spec, mes_ano)
    return await _collect_beneficio_municipio(
        db,
        spec=spec,
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
        before_request=before_request,
    )


async def collect_auxilio_brasil_municipio_ano(
    db: AsyncSession,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    spec = _get_beneficio_spec("auxilio_brasil")
    _validate_ano(spec, ano)
    return await _collect_beneficio_municipio_ano(
        db,
        spec=spec,
        ano=ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
        before_request=before_request,
    )


async def collect_bolsa_familia_municipio_ano(
    db: AsyncSession,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    spec = _get_beneficio_spec("bolsa_familia")
    _validate_ano(spec, ano)
    return await _collect_beneficio_municipio_ano(
        db,
        spec=spec,
        ano=ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
        before_request=before_request,
    )


def list_auxilio_brasil_municipio(
    db: Session,
    ano: int | None = None,
    codigo_ibge: str | None = None,
    estado_sigla: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return _list_beneficio_municipio(
        db,
        spec=_get_beneficio_spec("auxilio_brasil"),
        ano=ano,
        codigo_ibge=codigo_ibge,
        estado_sigla=estado_sigla,
        limit=limit,
        offset=offset,
    )


def list_bolsa_familia_municipio(
    db: Session,
    ano: int | None = None,
    codigo_ibge: str | None = None,
    estado_sigla: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return _list_beneficio_municipio(
        db,
        spec=_get_beneficio_spec("bolsa_familia"),
        ano=ano,
        codigo_ibge=codigo_ibge,
        estado_sigla=estado_sigla,
        limit=limit,
        offset=offset,
    )


async def collect_novo_bolsa_familia_municipio(
    db: AsyncSession,
    mes_ano: str,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    spec = _get_beneficio_spec("novo_bolsa_familia")
    _validate_mes_ano(spec, mes_ano)
    return await _collect_beneficio_municipio(
        db,
        spec=spec,
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
        before_request=before_request,
    )


async def collect_novo_bolsa_familia_municipio_ano(
    db: AsyncSession,
    ano: int,
    codigo_ibge: str,
    pagina_inicial: int = 1,
    before_request=None,
):
    spec = _get_beneficio_spec("novo_bolsa_familia")
    _validate_ano(spec, ano)
    return await _collect_beneficio_municipio_ano(
        db,
        spec=spec,
        ano=ano,
        codigo_ibge=codigo_ibge,
        pagina_inicial=pagina_inicial,
        before_request=before_request,
    )


def list_novo_bolsa_familia_municipio(
    db: Session,
    ano: int | None = None,
    codigo_ibge: str | None = None,
    estado_sigla: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return _list_beneficio_municipio(
        db,
        spec=_get_beneficio_spec("novo_bolsa_familia"),
        ano=ano,
        codigo_ibge=codigo_ibge,
        estado_sigla=estado_sigla,
        limit=limit,
        offset=offset,
    )
