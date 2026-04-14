from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ibge import (
    EstadoResponse,
    MunicipioListResponse,
    MunicipioResponse,
    RegiaoResponse,
)
from app.services.ibge.localidades_query_service import (
    get_estado,
    get_municipio,
    get_regiao,
    list_regiao_estados,
    list_estado_municipios,
    list_estados,
    list_municipios,
    list_regioes,
)

router = APIRouter(prefix="/ibge", tags=["IBGE"])


@router.get("/regioes", response_model=list[RegiaoResponse])
def get_regioes(
    id_regiao: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    return list_regioes(db, id_regiao=id_regiao)


@router.get("/regioes/{id_regiao}", response_model=RegiaoResponse)
def get_regiao_by_id(
    id_regiao: int,
    db: Session = Depends(get_db),
):
    regiao = get_regiao(db, id_regiao=id_regiao)
    if regiao is None:
        raise HTTPException(status_code=404, detail="Regiao not found")
    return regiao


@router.get("/regioes/{id_regiao}/estados", response_model=list[EstadoResponse])
def get_regiao_estados(
    id_regiao: int,
    db: Session = Depends(get_db),
):
    regiao, estados = list_regiao_estados(db, id_regiao=id_regiao)
    if regiao is None:
        raise HTTPException(status_code=404, detail="Regiao not found")
    return estados


@router.get("/estados", response_model=list[EstadoResponse])
def get_estados(
    id_estado: int | None = Query(default=None, ge=1),
    sigla: str | None = Query(default=None, min_length=2, max_length=2),
    db: Session = Depends(get_db),
):
    return list_estados(db, id_estado=id_estado, sigla=sigla)


@router.get("/estados/{id_estado}", response_model=EstadoResponse)
def get_estado_by_id(
    id_estado: int,
    db: Session = Depends(get_db),
):
    estado = get_estado(db, id_estado=id_estado)
    if estado is None:
        raise HTTPException(status_code=404, detail="Estado not found")
    return estado


@router.get("/estados/{id_estado}/municipios", response_model=MunicipioListResponse)
def get_estado_municipios(
    id_estado: int,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    nome: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
):
    estado, total, items = list_estado_municipios(
        db,
        id_estado=id_estado,
        limit=limit,
        offset=offset,
        nome=nome,
    )
    if estado is None:
        raise HTTPException(status_code=404, detail="Estado not found")
    return MunicipioListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/municipios", response_model=MunicipioListResponse)
def get_municipios(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    id_municipio: int | None = Query(default=None, ge=1),
    id_estado: int | None = Query(default=None, ge=1),
    nome: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
):
    total, items = list_municipios(
        db,
        limit=limit,
        offset=offset,
        id_municipio=id_municipio,
        id_estado=id_estado,
        nome=nome,
    )
    return MunicipioListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/municipios/{id_municipio}", response_model=MunicipioResponse)
def get_municipio_by_id(
    id_municipio: int,
    db: Session = Depends(get_db),
):
    municipio = get_municipio(db, id_municipio=id_municipio)
    if municipio is None:
        raise HTTPException(status_code=404, detail="Municipio not found")
    return municipio
