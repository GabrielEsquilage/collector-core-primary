from typing import TypedDict


class MunicipioJobTarget(TypedDict):
    codigo_ibge: str
    nome: str


class JobPlan(TypedDict):
    job_code: str
    descricao: str
    tipo_beneficio: str
    resource: str
    mes_ano_inicio: str
    mes_ano_fim: str
    job_granularity: str
    municipios: int
    municipio_codigo_ibge: str | None
    municipio_nome: str | None


class BeneficioResourceConfig(TypedDict):
    tipo_beneficio: str
    job_code_prefix: str
    descricao_prefix: str


JOB_STATUS_PENDING = "pending"
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_COMPLETED_WITH_ERRORS = "completed_with_errors"
JOB_STATUS_FAILED = "failed"

ITEM_STATUS_PENDING = "pending"
ITEM_STATUS_RUNNING = "running"
ITEM_STATUS_SUCCESS = "success"
ITEM_STATUS_FAILED = "failed"

TIPO_CARGA_BENEFICIO_MUNICIPIO = "beneficio_municipio"
JOB_GRANULARITY_ESTADO_MES = "estado_mes"
JOB_GRANULARITY_MUNICIPIO_MES = "municipio_mes"

RESTRICTED_RESOURCE = "bolsa-familia-por-municipio"

RESOURCE_CONFIGS: dict[str, BeneficioResourceConfig] = {
    "bolsa-familia-por-municipio": {
        "tipo_beneficio": "bolsa_familia",
        "job_code_prefix": "bf",
        "descricao_prefix": "Bolsa Familia",
    },
    "auxilio-brasil-por-municipio": {
        "tipo_beneficio": "auxilio_brasil",
        "job_code_prefix": "ab",
        "descricao_prefix": "Auxilio Brasil",
    },
    "novo-bolsa-familia-por-municipio": {
        "tipo_beneficio": "novo_bolsa_familia",
        "job_code_prefix": "nbf",
        "descricao_prefix": "Novo Bolsa Familia",
    },
}


def get_resource_config(resource: str) -> BeneficioResourceConfig:
    config = RESOURCE_CONFIGS.get(resource)
    if config is None:
        raise ValueError(f"Resource nao suportado para seed: {resource}")
    return config

def iter_mes_ano(start: str, end: str) -> list[str]:
    current_year = int(start[:4])
    current_month = int(start[4:])
    end_year = int(end[:4])
    end_month = int(end[4:])
    result = []

    while current_year < end_year or (current_year == end_year and current_month <= end_month):
        result.append(f"{current_year}{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return result


def _build_monthly_job_plans(
    *,
    prefix: str,
    descricao_prefix: str,
    tipo_beneficio: str,
    resource: str,
    start: str,
    end: str,
    municipios: int,
) -> tuple[JobPlan, ...]:
    return tuple(
        {
            "job_code": f"{prefix}-{mes_ano}",
            "descricao": f"{descricao_prefix} {mes_ano}",
            "tipo_beneficio": tipo_beneficio,
            "resource": resource,
            "mes_ano_inicio": mes_ano,
            "mes_ano_fim": mes_ano,
            "job_granularity": JOB_GRANULARITY_ESTADO_MES,
            "municipios": municipios,
            "municipio_codigo_ibge": None,
            "municipio_nome": None,
        }
        for mes_ano in iter_mes_ano(start, end)
    )


def build_monthly_job_plans(
    *,
    estado_sigla: str | None,
    resource: str,
    start: str,
    end: str,
    tipo_beneficio: str | None = None,
    job_code_prefix: str | None = None,
    descricao_prefix: str | None = None,
    municipios: int = 0,
) -> tuple[JobPlan, ...]:
    config = get_resource_config(resource)
    resolved_tipo_beneficio = tipo_beneficio or config["tipo_beneficio"]
    resolved_job_code_prefix = job_code_prefix or (f"{config['job_code_prefix']}-{estado_sigla.lower()}" if estado_sigla else config['job_code_prefix'])
    resolved_descricao_prefix = descricao_prefix or (f"{config['descricao_prefix']} {estado_sigla.upper()}" if estado_sigla else config['descricao_prefix'])

    return _build_monthly_job_plans(
        prefix=resolved_job_code_prefix,
        descricao_prefix=resolved_descricao_prefix,
        tipo_beneficio=resolved_tipo_beneficio,
        resource=resource,
        start=start,
        end=end,
        municipios=municipios,
    )


def build_municipio_monthly_job_plans(
    *,
    estado_sigla: str | None,
    resource: str,
    start: str,
    end: str,
    municipios: tuple[MunicipioJobTarget, ...],
    tipo_beneficio: str | None = None,
    job_code_prefix: str | None = None,
    descricao_prefix: str | None = None,
) -> tuple[JobPlan, ...]:
    config = get_resource_config(resource)
    resolved_tipo_beneficio = tipo_beneficio or config["tipo_beneficio"]
    resolved_job_code_prefix = job_code_prefix or (f"{config['job_code_prefix']}-{estado_sigla.lower()}" if estado_sigla else config['job_code_prefix'])
    resolved_descricao_prefix = descricao_prefix or (f"{config['descricao_prefix']} {estado_sigla.upper()}" if estado_sigla else config['descricao_prefix'])

    plans: list[JobPlan] = []
    for mes_ano in iter_mes_ano(start, end):
        for municipio in municipios:
            plans.append(
                {
                    "job_code": f"{resolved_job_code_prefix}-{mes_ano}-{municipio['codigo_ibge']}",
                    "descricao": (
                        f"{resolved_descricao_prefix} {mes_ano} "
                        f"{municipio['nome']} ({municipio['codigo_ibge']})"
                    ),
                    "tipo_beneficio": resolved_tipo_beneficio,
                    "resource": resource,
                    "mes_ano_inicio": mes_ano,
                    "mes_ano_fim": mes_ano,
                    "job_granularity": JOB_GRANULARITY_MUNICIPIO_MES,
                    "municipios": 1,
                    "municipio_codigo_ibge": municipio["codigo_ibge"],
                    "municipio_nome": municipio["nome"],
                }
            )

    return tuple(plans)


JOB_PLANS_PR: tuple[JobPlan, ...] = (
    *build_monthly_job_plans(
        estado_sigla="PR",
        resource="bolsa-familia-por-municipio",
        start="201801",
        end="201812",
        municipios=399,
    ),
)
