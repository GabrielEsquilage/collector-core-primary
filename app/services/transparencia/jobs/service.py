import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import TransparenciaCargaJob
from app.services.transparencia.beneficios import validate_beneficio_mes_ano
from app.services.transparencia.jobs.definitions import (
    JOB_GRANULARITY_ESTADO_MES,
    JOB_GRANULARITY_MUNICIPIO_MES,
    JOB_STATUS_COMPLETED_WITH_ERRORS,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    TIPO_CARGA_BENEFICIO_MUNICIPIO,
    build_municipio_monthly_job_plans,
    build_monthly_job_plans,
    get_resource_config,
    iter_mes_ano,
)
from app.services.transparencia.jobs.repository import (
    count_retryable_failed_items,
    create_job_items,
    delete_job as repository_delete_job,
    fail_running_job_items,
    get_estado_municipios,
    get_job as repository_get_job,
    get_job_by_code,
    get_latest_running_item_started_at,
    list_jobs as repository_list_jobs,
    refresh_job_counts,
    reset_failed_job_items_to_pending,
    utcnow,
)
from app.services.transparencia.jobs.runner import run_job as runner_run_job

MAX_JOB_ITEM_ATTEMPTS = int(os.getenv("TRANSPARENCIA_JOB_MAX_ATTEMPTS", "3"))
STALE_JOB_AFTER_MINUTES = int(os.getenv("TRANSPARENCIA_JOB_STALE_AFTER_MINUTES", "15"))


class TransparenciaCargaJobNotFoundError(ValueError):
    pass


class TransparenciaCargaJobConflictError(ValueError):
    pass


def _stale_threshold() -> datetime:
    return utcnow() - timedelta(minutes=STALE_JOB_AFTER_MINUTES)


def _recover_stale_job_execution(
    db: Session,
    job: TransparenciaCargaJob,
) -> TransparenciaCargaJob | None:
    if job.status not in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        return None

    reference_time = get_latest_running_item_started_at(db, job_id=job.id)
    if reference_time is None:
        reference_time = job.started_at or job.created_at

    if reference_time is None or reference_time > _stale_threshold():
        return None

    fail_running_job_items(
        db,
        job_id=job.id,
        error_message="Execucao anterior interrompida e marcada para retentativa manual.",
    )
    job.status = JOB_STATUS_FAILED
    job.finished_at = utcnow()
    db.commit()
    db.refresh(job)
    return refresh_job_counts(db, job)


def _normalize_estado_sigla(estado_sigla: str) -> str:
    normalized = estado_sigla.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("estadoSigla must contain exactly 2 letters")
    return normalized


def _normalize_codigo_ibge(codigo_ibge: str) -> str:
    normalized = codigo_ibge.strip()
    if not normalized or not normalized.isdigit():
        raise ValueError("codigoIbge must contain only digits")
    return normalized


def _validate_mes_ano_value(label: str, value: str) -> None:
    if len(value) != 6 or not value.isdigit():
        raise ValueError(f"{label} must be in AAAAMM format")

    month = int(value[4:])
    if month < 1 or month > 12:
        raise ValueError(f"{label} must contain a valid month between 01 and 12")


def _resolve_seed_period(
    *,
    ano: int | None,
    mes_ano_inicio: str | None,
    mes_ano_fim: str | None,
) -> tuple[str, str]:
    if ano is not None and (mes_ano_inicio is not None or mes_ano_fim is not None):
        raise ValueError("Informe ano ou mesAnoInicio + mesAnoFim, mas nao ambos")

    if ano is not None:
        return f"{ano}01", f"{ano}12"

    if mes_ano_inicio is None or mes_ano_fim is None:
        raise ValueError("Informe ano ou mesAnoInicio + mesAnoFim para o seed")

    _validate_mes_ano_value("mesAnoInicio", mes_ano_inicio)
    _validate_mes_ano_value("mesAnoFim", mes_ano_fim)

    if mes_ano_inicio > mes_ano_fim:
        raise ValueError("mesAnoInicio must be less than or equal to mesAnoFim")

    return mes_ano_inicio, mes_ano_fim


def _resolve_target_municipios(
    db: Session,
    *,
    estado_sigla: str,
    municipio_codigos_ibge: list[str] | None,
) -> tuple[dict[str, str], ...]:
    all_municipios = tuple(get_estado_municipios(db, estado_sigla))
    if not all_municipios:
        raise ValueError(
            f"Nao ha municipios do estado {estado_sigla} carregados na base do IBGE."
        )

    if municipio_codigos_ibge is None:
        return all_municipios

    municipios_by_code = {item["codigo_ibge"]: item for item in all_municipios}
    selected: list[dict[str, str]] = []
    invalid_codes: list[str] = []

    for codigo_ibge in municipio_codigos_ibge:
        municipio = municipios_by_code.get(str(codigo_ibge))
        if municipio is None:
            invalid_codes.append(str(codigo_ibge))
            continue
        selected.append(municipio)

    if invalid_codes:
        invalid_values = ", ".join(sorted(invalid_codes))
        raise ValueError(
            "Os seguintes municipios nao pertencem ao estado "
            f"{estado_sigla}: {invalid_values}"
        )

    if not selected:
        raise ValueError("Nenhum municipio valido foi informado para o seed")

    return tuple(selected)


def seed_beneficio_jobs(
    db: Session,
    *,
    resource: str,
    estado_sigla: str = "PR",
    job_granularity: str = JOB_GRANULARITY_MUNICIPIO_MES,
    ano: int | None = None,
    mes_ano_inicio: str | None = None,
    mes_ano_fim: str | None = None,
    municipio_codigos_ibge: list[str] | None = None,
    tipo_beneficio: str | None = None,
    job_code_prefix: str | None = None,
    descricao_prefix: str | None = None,
) -> tuple[int, int, list[TransparenciaCargaJob]]:
    normalized_estado_sigla = _normalize_estado_sigla(estado_sigla)
    resource_config = get_resource_config(resource)
    resolved_tipo_beneficio = tipo_beneficio or resource_config["tipo_beneficio"]

    if resolved_tipo_beneficio != resource_config["tipo_beneficio"]:
        raise ValueError(
            "tipoBeneficio nao corresponde ao resource informado para o seed"
        )

    start, end = _resolve_seed_period(
        ano=ano,
        mes_ano_inicio=mes_ano_inicio,
        mes_ano_fim=mes_ano_fim,
    )
    mes_anos = iter_mes_ano(start, end)

    for mes_ano in mes_anos:
        validate_beneficio_mes_ano(resolved_tipo_beneficio, mes_ano)

    target_municipios = _resolve_target_municipios(
        db,
        estado_sigla=normalized_estado_sigla,
        municipio_codigos_ibge=municipio_codigos_ibge,
    )

    if job_granularity == JOB_GRANULARITY_ESTADO_MES:
        if municipio_codigos_ibge is not None and len(target_municipios) != len(
            get_estado_municipios(db, normalized_estado_sigla)
        ):
            raise ValueError(
                "Selecao parcial de municipios exige jobGranularity=municipio_mes"
            )
        plans = build_monthly_job_plans(
            estado_sigla=normalized_estado_sigla,
            resource=resource,
            start=start,
            end=end,
            tipo_beneficio=resolved_tipo_beneficio,
            job_code_prefix=job_code_prefix,
            descricao_prefix=descricao_prefix,
            municipios=len(target_municipios),
        )
    elif job_granularity == JOB_GRANULARITY_MUNICIPIO_MES:
        plans = build_municipio_monthly_job_plans(
            estado_sigla=normalized_estado_sigla,
            resource=resource,
            start=start,
            end=end,
            municipios=target_municipios,
            tipo_beneficio=resolved_tipo_beneficio,
            job_code_prefix=job_code_prefix,
            descricao_prefix=descricao_prefix,
        )
    else:
        raise ValueError(f"jobGranularity nao suportado: {job_granularity}")

    created_count = 0
    existing_count = 0
    jobs: list[TransparenciaCargaJob] = []

    for plan in plans:
        existing_job: TransparenciaCargaJob | None = get_job_by_code(db, plan["job_code"])
        if existing_job is not None:
            existing_count += 1
            jobs.append(refresh_job_counts(db, existing_job))
            continue

        try:
            job = TransparenciaCargaJob(
                job_code=plan["job_code"],
                descricao=plan["descricao"],
                tipo_carga=TIPO_CARGA_BENEFICIO_MUNICIPIO,
                status=JOB_STATUS_PENDING,
                metadata_json={
                    "estado_sigla": normalized_estado_sigla,
                    "tipo_beneficio": plan["tipo_beneficio"],
                    "resource": plan["resource"],
                    "mes_ano_inicio": plan["mes_ano_inicio"],
                    "mes_ano_fim": plan["mes_ano_fim"],
                    "municipios": int(plan["municipios"]),
                    "job_granularity": plan["job_granularity"],
                    "municipio_codigo_ibge": plan["municipio_codigo_ibge"],
                    "municipio_nome": plan["municipio_nome"],
                },
            )
            db.add(job)
            db.flush()

            if plan["municipio_codigo_ibge"] is None:
                municipio_codigos = [item["codigo_ibge"] for item in target_municipios]
                mes_anos = iter_mes_ano(plan["mes_ano_inicio"], plan["mes_ano_fim"])
            else:
                municipio_codigos = [str(plan["municipio_codigo_ibge"])]
                mes_anos = [plan["mes_ano_inicio"]]

            create_job_items(
                db,
                job=job,
                tipo_beneficio=plan["tipo_beneficio"],
                resource=plan["resource"],
                municipio_codigos=municipio_codigos,
                mes_anos=mes_anos,
            )

            db.commit()
            db.refresh(job)
        except Exception:
            db.rollback()
            raise

        created_count += 1
        jobs.append(refresh_job_counts(db, job))

    jobs.sort(key=lambda item: str(item.job_code))
    return created_count, existing_count, jobs


def seed_parana_beneficio_jobs(
    db: Session,
) -> tuple[int, int, list[TransparenciaCargaJob]]:
    return seed_beneficio_jobs(
        db,
        resource="bolsa-familia-por-municipio",
        estado_sigla="PR",
        job_granularity=JOB_GRANULARITY_ESTADO_MES,
        ano=2018,
    )


def list_jobs(
    db: Session,
    *,
    status: str | list[str] | None = None,
    estado_sigla: str | None = None,
    codigo_ibge: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[TransparenciaCargaJob]]:
    normalized_estado_sigla = None
    if estado_sigla is not None:
        normalized_estado_sigla = _normalize_estado_sigla(estado_sigla)

    normalized_codigo_ibge = None
    if codigo_ibge is not None:
        normalized_codigo_ibge = _normalize_codigo_ibge(codigo_ibge)

    return repository_list_jobs(
        db,
        status=status,
        estado_sigla=normalized_estado_sigla,
        codigo_ibge=normalized_codigo_ibge,
        limit=limit,
        offset=offset,
    )


def get_job(db: Session, job_id: int) -> TransparenciaCargaJob | None:
    job: TransparenciaCargaJob | None = repository_get_job(db, job_id)
    if job is None:
        return None
    return refresh_job_counts(db, job)


def queue_job_run(db: Session, job_id: int) -> TransparenciaCargaJob:
    job: TransparenciaCargaJob | None = repository_get_job(db, job_id)
    if job is None:
        raise TransparenciaCargaJobNotFoundError(f"Job {job_id} not found")

    job = refresh_job_counts(db, job)

    if job.status in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        recovered_job = _recover_stale_job_execution(db, job)
        if recovered_job is None:
            raise TransparenciaCargaJobConflictError(
                f"Job {job_id} ja esta em execucao."
            )
        job = recovered_job

    retryable_failed_items = count_retryable_failed_items(
        db,
        job_id=job.id,
        max_attempts=MAX_JOB_ITEM_ATTEMPTS,
    )

    if job.pending_items == 0 and retryable_failed_items == 0:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} nao possui itens pendentes para execucao."
        )

    job.status = JOB_STATUS_QUEUED
    job.started_at = job.started_at or utcnow()
    job.finished_at = None
    db.commit()
    db.refresh(job)
    return refresh_job_counts(db, job)


async def run_job(job_id: int) -> None:
    await runner_run_job(job_id, max_attempts=MAX_JOB_ITEM_ATTEMPTS)


def reset_job_to_pending(db: Session, job_id: int) -> TransparenciaCargaJob:
    job: TransparenciaCargaJob | None = repository_get_job(db, job_id)
    if job is None:
        raise TransparenciaCargaJobNotFoundError(f"Job {job_id} not found")

    job = refresh_job_counts(db, job)

    if job.status in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} ainda esta em execucao."
        )

    if job.status not in {JOB_STATUS_FAILED, JOB_STATUS_COMPLETED_WITH_ERRORS}:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} nao terminou com erro e nao pode voltar para pending."
        )

    reset_count = reset_failed_job_items_to_pending(db, job_id=job.id)
    if reset_count == 0 and job.pending_items == 0:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} nao possui itens com erro para reabrir."
        )

    job.status = JOB_STATUS_PENDING
    job.finished_at = None
    db.commit()
    db.refresh(job)
    return refresh_job_counts(db, job)


def delete_job(db: Session, job_id: int) -> None:
    job: TransparenciaCargaJob | None = repository_get_job(db, job_id)
    if job is None:
        raise TransparenciaCargaJobNotFoundError(f"Job {job_id} not found")

    job = refresh_job_counts(db, job)

    if job.status != JOB_STATUS_PENDING:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} nao esta pending e nao pode ser excluido."
        )

    if job.started_at is not None or job.finished_at is not None:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} ja possui historico de execucao e nao pode ser excluido."
        )

    if job.running_items > 0 or job.success_items > 0 or job.failed_items > 0:
        raise TransparenciaCargaJobConflictError(
            f"Job {job_id} ja possui itens processados e nao pode ser excluido."
        )

    repository_delete_job(db, job)
