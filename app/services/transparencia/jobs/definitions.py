from typing import TypedDict


class JobPlan(TypedDict):
    job_code: str
    descricao: str
    tipo_beneficio: str
    resource: str
    mes_ano_inicio: str
    mes_ano_fim: str


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

RESTRICTED_RESOURCE = "bolsa-familia-por-municipio"

JOB_PLANS_PR: tuple[JobPlan, ...] = (
    {
        "job_code": "bf-pr-2018",
        "descricao": "Bolsa Familia PR 2018",
        "tipo_beneficio": "bolsa_familia",
        "resource": "bolsa-familia-por-municipio",
        "mes_ano_inicio": "201801",
        "mes_ano_fim": "201812",
    },
    {
        "job_code": "bf-pr-2019",
        "descricao": "Bolsa Familia PR 2019",
        "tipo_beneficio": "bolsa_familia",
        "resource": "bolsa-familia-por-municipio",
        "mes_ano_inicio": "201901",
        "mes_ano_fim": "201912",
    },
    {
        "job_code": "bf-pr-2020",
        "descricao": "Bolsa Familia PR 2020",
        "tipo_beneficio": "bolsa_familia",
        "resource": "bolsa-familia-por-municipio",
        "mes_ano_inicio": "202001",
        "mes_ano_fim": "202012",
    },
    {
        "job_code": "ab-pr-202111-202302",
        "descricao": "Auxilio Brasil PR 202111-202302",
        "tipo_beneficio": "auxilio_brasil",
        "resource": "auxilio-brasil-por-municipio",
        "mes_ano_inicio": "202111",
        "mes_ano_fim": "202302",
    },
    {
        "job_code": "nbf-pr-202303-202601",
        "descricao": "Novo Bolsa Familia PR 202303-202601",
        "tipo_beneficio": "novo_bolsa_familia",
        "resource": "novo-bolsa-familia-por-municipio",
        "mes_ano_inicio": "202303",
        "mes_ano_fim": "202601",
    },
)


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
