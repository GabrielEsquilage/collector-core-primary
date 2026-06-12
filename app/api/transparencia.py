from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db, get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.transparencia import (
    AuxilioBrasilCollectRequest,
    AuxilioBrasilCollectPeriodoRequest,
    AuxilioBrasilCollectPeriodoResponse,
    AuxilioBrasilCollectResponse,
    AuxilioBrasilMunicipioListResponse,
    BolsaFamiliaCollectPeriodoRequest,
    BolsaFamiliaCollectPeriodoResponse,
    BolsaFamiliaCollectRequest,
    BolsaFamiliaCollectResponse,
    BolsaFamiliaMunicipioListResponse,
    NovoBolsaFamiliaCollectRequest,
    NovoBolsaFamiliaCollectPeriodoRequest,
    NovoBolsaFamiliaCollectPeriodoResponse,
    NovoBolsaFamiliaCollectResponse,
    NovoBolsaFamiliaMunicipioListResponse,
    TransparenciaCargaJobListResponse,
    TransparenciaCargaJobResponse,
    TransparenciaCargaJobSeedRequest,
    TransparenciaCargaJobSeedResponse,
    TransparenciaCollectRequest,
    TransparenciaCollectResponse,
    TransparenciaOrgaoListResponse,
    TransparenciaOrgaoResponse,
)
from app.services.transparencia.beneficios import (
    BeneficioPeriodoInvalidoError,
    collect_auxilio_brasil_municipio,
    collect_auxilio_brasil_municipio_ano,
    collect_bolsa_familia_municipio,
    collect_bolsa_familia_municipio_ano,
    collect_novo_bolsa_familia_municipio,
    collect_novo_bolsa_familia_municipio_ano,
    list_auxilio_brasil_municipio,
    list_bolsa_familia_municipio,
    list_novo_bolsa_familia_municipio,
)
from app.services.transparencia.collector import (
    collect_orgaos_siafi,
    collect_orgaos_siape,
    get_orgao_siafi,
    get_orgao_siape,
    list_orgaos_siafi,
    list_orgaos_siape,
)
from app.services.transparencia.jobs import (
    TransparenciaCargaJobConflictError,
    TransparenciaCargaJobNotFoundError,
    delete_job,
    get_job,
    list_jobs,
    queue_job_run,
    reset_job_to_pending,
    run_job,
    seed_beneficio_jobs,
    seed_parana_beneficio_jobs,
)

router = APIRouter(prefix="/transparencia", tags=["Transparencia"])


@router.post(
    "/jobs/beneficios/seed",
    response_model=TransparenciaCargaJobSeedResponse,
)
@router.post(
    "/jobs/beneficios/parana/seed",
    response_model=TransparenciaCargaJobSeedResponse,
)
def seed_parana_jobs(
    payload: TransparenciaCargaJobSeedRequest | None = None,
    db: Session = Depends(get_db),
):
    filters = payload or TransparenciaCargaJobSeedRequest()
    try:
        if payload is None:
            created_count, existing_count, jobs = seed_parana_beneficio_jobs(db)
        else:
            created_count, existing_count, jobs = seed_beneficio_jobs(
                db,
                resource=filters.resource,
                estado_sigla=filters.estado_sigla,
                job_granularity=filters.job_granularity,
                ano=filters.ano,
                mes_ano_inicio=filters.mes_ano_inicio,
                mes_ano_fim=filters.mes_ano_fim,
                municipio_codigos_ibge=filters.municipio_codigos_ibge,
                tipo_beneficio=filters.tipo_beneficio,
                job_code_prefix=filters.job_code_prefix,
                descricao_prefix=filters.descricao_prefix,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TransparenciaCargaJobSeedResponse(
        created_count=created_count,
        existing_count=existing_count,
        jobs=jobs,
    )


@router.get("/jobs", response_model=TransparenciaCargaJobListResponse)
def get_jobs(
    status: str | None = Query(default=None, min_length=1),
    estado_sigla: str | None = Query(default=None, alias="estadoSigla", min_length=2, max_length=2),
    codigo_ibge: str | None = Query(default=None, alias="codigoIbge", min_length=1),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        total, items = list_jobs(
            db,
            status=status,
            estado_sigla=estado_sigla,
            codigo_ibge=codigo_ibge,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TransparenciaCargaJobListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/jobs/{job_id}", response_model=TransparenciaCargaJobResponse)
def get_job_by_id(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/run", response_model=TransparenciaCargaJobResponse, status_code=202)
def run_job_by_id(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        job = queue_job_run(db, job_id)
    except TransparenciaCargaJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TransparenciaCargaJobConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    background_tasks.add_task(run_job, job.id)
    return job


@router.post("/jobs/{job_id}/reset-pending", response_model=TransparenciaCargaJobResponse)
def reset_job_pending_by_id(
    job_id: int,
    db: Session = Depends(get_db),
):
    try:
        job = reset_job_to_pending(db, job_id)
    except TransparenciaCargaJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TransparenciaCargaJobConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return job


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job_by_id(
    job_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_job(db, job_id)
    except TransparenciaCargaJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TransparenciaCargaJobConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return Response(status_code=204)


@router.post(
    "/beneficios/bolsa-familia/collect",
    response_model=BolsaFamiliaCollectResponse,
)
async def collect_bolsa_familia(
    payload: BolsaFamiliaCollectRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await collect_bolsa_familia_municipio(
            db,
            mes_ano=payload.mes_ano,
            codigo_ibge=payload.codigo_ibge,
            pagina_inicial=payload.pagina_inicial,
        )
    except (BeneficioPeriodoInvalidoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/beneficios/bolsa-familia/collect-periodo",
    response_model=BolsaFamiliaCollectPeriodoResponse,
)
async def collect_bolsa_familia_periodo(
    payload: BolsaFamiliaCollectPeriodoRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await collect_bolsa_familia_municipio_ano(
            db,
            ano=payload.ano,
            codigo_ibge=payload.codigo_ibge,
            pagina_inicial=payload.pagina_inicial,
        )
    except (BeneficioPeriodoInvalidoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/beneficios/bolsa-familia",
    response_model=BolsaFamiliaMunicipioListResponse,
)
def get_bolsa_familia(
    ano: int | None = Query(default=None, ge=2000, le=2100),
    codigo_ibge: str | None = Query(default=None, alias="codigoIbge", min_length=1),
    estado_sigla: str | None = Query(default=None, alias="estadoSigla", min_length=2, max_length=2),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        total, items = list_bolsa_familia_municipio(
            db,
            ano=ano,
            codigo_ibge=codigo_ibge,
            estado_sigla=estado_sigla,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BolsaFamiliaMunicipioListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.post(
    "/beneficios/auxilio-brasil/collect",
    response_model=AuxilioBrasilCollectResponse,
)
async def collect_auxilio_brasil(
    payload: AuxilioBrasilCollectRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await collect_auxilio_brasil_municipio(
            db,
            mes_ano=payload.mes_ano,
            codigo_ibge=payload.codigo_ibge,
            pagina_inicial=payload.pagina_inicial,
        )
    except (BeneficioPeriodoInvalidoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/beneficios/auxilio-brasil/collect-periodo",
    response_model=AuxilioBrasilCollectPeriodoResponse,
)
async def collect_auxilio_brasil_periodo(
    payload: AuxilioBrasilCollectPeriodoRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await collect_auxilio_brasil_municipio_ano(
            db,
            ano=payload.ano,
            codigo_ibge=payload.codigo_ibge,
            pagina_inicial=payload.pagina_inicial,
        )
    except (BeneficioPeriodoInvalidoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/beneficios/auxilio-brasil",
    response_model=AuxilioBrasilMunicipioListResponse,
)
def get_auxilio_brasil(
    ano: int | None = Query(default=None, ge=2000, le=2100),
    codigo_ibge: str | None = Query(default=None, alias="codigoIbge", min_length=1),
    estado_sigla: str | None = Query(default=None, alias="estadoSigla", min_length=2, max_length=2),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        total, items = list_auxilio_brasil_municipio(
            db,
            ano=ano,
            codigo_ibge=codigo_ibge,
            estado_sigla=estado_sigla,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AuxilioBrasilMunicipioListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.post(
    "/beneficios/novo-bolsa-familia/collect",
    response_model=NovoBolsaFamiliaCollectResponse,
)
async def collect_novo_bolsa_familia(
    payload: NovoBolsaFamiliaCollectRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await collect_novo_bolsa_familia_municipio(
            db,
            mes_ano=payload.mes_ano,
            codigo_ibge=payload.codigo_ibge,
            pagina_inicial=payload.pagina_inicial,
        )
    except (BeneficioPeriodoInvalidoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/beneficios/novo-bolsa-familia/collect-periodo",
    response_model=NovoBolsaFamiliaCollectPeriodoResponse,
)
async def collect_novo_bolsa_familia_periodo(
    payload: NovoBolsaFamiliaCollectPeriodoRequest,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await collect_novo_bolsa_familia_municipio_ano(
            db,
            ano=payload.ano,
            codigo_ibge=payload.codigo_ibge,
            pagina_inicial=payload.pagina_inicial,
        )
    except (BeneficioPeriodoInvalidoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/beneficios/novo-bolsa-familia",
    response_model=NovoBolsaFamiliaMunicipioListResponse,
)
def get_novo_bolsa_familia(
    ano: int | None = Query(default=None, ge=2000, le=2100),
    codigo_ibge: str | None = Query(default=None, alias="codigoIbge", min_length=1),
    estado_sigla: str | None = Query(default=None, alias="estadoSigla", min_length=2, max_length=2),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        total, items = list_novo_bolsa_familia_municipio(
            db,
            ano=ano,
            codigo_ibge=codigo_ibge,
            estado_sigla=estado_sigla,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return NovoBolsaFamiliaMunicipioListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.post("/orgaos/siafi/collect", response_model=TransparenciaCollectResponse)
async def collect_transparencia_siafi(
    payload: TransparenciaCollectRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
):
    filters = payload or TransparenciaCollectRequest()
    return await collect_orgaos_siafi(
        db,
        codigo=filters.codigo,
        descricao=filters.descricao,
    )


@router.post("/orgaos/siape/collect", response_model=TransparenciaCollectResponse)
async def collect_transparencia_siape(
    payload: TransparenciaCollectRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
):
    filters = payload or TransparenciaCollectRequest()
    return await collect_orgaos_siape(
        db,
        codigo=filters.codigo,
        descricao=filters.descricao,
    )


@router.get("/orgaos/siafi", response_model=TransparenciaOrgaoListResponse)
def get_orgaos_siafi(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    codigo: str | None = Query(default=None, min_length=1),
    descricao: str | None = Query(default=None, min_length=1),
    status_registro: str | None = Query(default=None, min_length=1),
    elegivel_dashboard: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    total, items = list_orgaos_siafi(
        db,
        limit=limit,
        offset=offset,
        codigo=codigo,
        descricao=descricao,
        status_registro=status_registro,
        elegivel_dashboard=elegivel_dashboard,
    )
    return TransparenciaOrgaoListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/orgaos/siafi/{id}", response_model=TransparenciaOrgaoResponse)
def get_orgao_siafi_by_id(
    id: int,
    db: Session = Depends(get_db),
):
    item = get_orgao_siafi(db, id=id)
    if item is None:
        raise HTTPException(status_code=404, detail="Orgao SIAFI not found")
    return item


@router.get("/orgaos/siape", response_model=TransparenciaOrgaoListResponse)
def get_orgaos_siape(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    codigo: str | None = Query(default=None, min_length=1),
    descricao: str | None = Query(default=None, min_length=1),
    status_registro: str | None = Query(default=None, min_length=1),
    elegivel_dashboard: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    total, items = list_orgaos_siape(
        db,
        limit=limit,
        offset=offset,
        codigo=codigo,
        descricao=descricao,
        status_registro=status_registro,
        elegivel_dashboard=elegivel_dashboard,
    )
    return TransparenciaOrgaoListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/orgaos/siape/{id}", response_model=TransparenciaOrgaoResponse)
def get_orgao_siape_by_id(
    id: int,
    db: Session = Depends(get_db),
):
    item = get_orgao_siape(db, id=id)
    if item is None:
        raise HTTPException(status_code=404, detail="Orgao SIAPE not found")
    return item
