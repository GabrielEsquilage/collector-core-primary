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
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Retorna apenas os jobs que estão completos (completed) ou executando (running) 
    para fins de auditoria. Traz também os metadados (request info).
    """
    # Filtra apenas por jobs que nos interessam na auditoria
    total, items = list_jobs(db, status=["running", "completed"], limit=limit, offset=offset)
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
