from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transparencia import (
    AuxilioBrasilCollectRequest,
    AuxilioBrasilCollectPeriodoRequest,
    AuxilioBrasilCollectPeriodoResponse,
    AuxilioBrasilCollectResponse,
    AuxilioBrasilMunicipioListResponse,
    TransparenciaCollectRequest,
    TransparenciaCollectResponse,
    TransparenciaOrgaoListResponse,
    TransparenciaOrgaoResponse,
)
from app.services.transparencia.beneficios import (
    collect_auxilio_brasil_municipio,
    collect_auxilio_brasil_municipio_ano,
    list_auxilio_brasil_municipio,
)
from app.services.transparencia.collector import (
    collect_orgaos_siafi,
    collect_orgaos_siape,
    get_orgao_siafi,
    get_orgao_siape,
    list_orgaos_siafi,
    list_orgaos_siape,
)

router = APIRouter(prefix="/transparencia", tags=["Transparencia"])


@router.post(
    "/beneficios/auxilio-brasil/collect",
    response_model=AuxilioBrasilCollectResponse,
)
async def collect_auxilio_brasil(
    payload: AuxilioBrasilCollectRequest,
    db: Session = Depends(get_db),
):
    return await collect_auxilio_brasil_municipio(
        db,
        mes_ano=payload.mes_ano,
        codigo_ibge=payload.codigo_ibge,
        pagina_inicial=payload.pagina_inicial,
    )


@router.post(
    "/beneficios/auxilio-brasil/collect-periodo",
    response_model=AuxilioBrasilCollectPeriodoResponse,
)
async def collect_auxilio_brasil_periodo(
    payload: AuxilioBrasilCollectPeriodoRequest,
    db: Session = Depends(get_db),
):
    return await collect_auxilio_brasil_municipio_ano(
        db,
        ano=payload.ano,
        codigo_ibge=payload.codigo_ibge,
        pagina_inicial=payload.pagina_inicial,
    )


@router.get(
    "/beneficios/auxilio-brasil",
    response_model=AuxilioBrasilMunicipioListResponse,
)
def get_auxilio_brasil(
    mes_ano: str | None = Query(default=None, alias="mesAno", min_length=6, max_length=6),
    codigo_ibge: str | None = Query(default=None, alias="codigoIbge", min_length=1),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total, items = list_auxilio_brasil_municipio(
        db,
        mes_ano=mes_ano,
        codigo_ibge=codigo_ibge,
        limit=limit,
        offset=offset,
    )
    return AuxilioBrasilMunicipioListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.post("/orgaos/siafi/collect", response_model=TransparenciaCollectResponse)
async def collect_transparencia_siafi(
    payload: TransparenciaCollectRequest | None = None,
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
