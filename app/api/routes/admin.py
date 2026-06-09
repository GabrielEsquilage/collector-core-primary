from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.admin import JobItemListResponse
from app.schemas.transparencia import TransparenciaCargaJobListResponse
from app.services.transparencia.jobs.repository import list_job_items
from app.services.transparencia.jobs.service import get_job, list_jobs

router = APIRouter(tags=["Admin - Auditoria"])


@router.get("/audit/jobs", response_model=TransparenciaCargaJobListResponse)
def get_audit_jobs(
    status: str | None = None,
    codigo_ibge: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Retorna apenas os jobs que estão completos (completed) ou executando (running) 
    para fins de auditoria. Traz também os metadados (request info).
    """
    audit_statuses = ["running", "completed"]
    if status:
        query_status = status if status in audit_statuses else audit_statuses
    else:
        query_status = audit_statuses

    total, items = list_jobs(db, status=query_status, codigo_ibge=codigo_ibge, limit=limit, offset=offset)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/audit/jobs/{job_id}/items", response_model=JobItemListResponse)
def get_audit_job_items(
    job_id: int,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lista os itens de um job específico para visualizar os detalhes (como logs de erro).
    """
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    total, items = list_job_items(db, job_id=job_id, status=status, limit=limit, offset=offset)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/audit/items/{item_id}/payloads")
def get_audit_job_item_payloads(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Busca os payloads originais que foram salvos no banco referentes a este item executado.
    """
    from app.services.transparencia.jobs.repository import get_job_item
    from app.services.transparencia.beneficios import _get_beneficio_spec, _parse_mes_ano

    item = get_job_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")

    if item.status != "success":
        return []

    try:
        spec = _get_beneficio_spec(item.tipo_beneficio)
        data_ref = _parse_mes_ano(item.mes_ano)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao resolver especificação: {e}")

    # Buscar na tabela de domínio
    records = (
        db.query(spec.model)
        .filter(
            spec.model.tipo_beneficio == spec.tipo_beneficio,
            spec.model.data_referencia == data_ref,
            spec.model.municipio_codigo_ibge == item.codigo_ibge,
        )
        .all()
    )

    return [record.payload_json for record in records]

