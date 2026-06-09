from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transparencia import TransparenciaCargaJobListResponse
from app.services.transparencia.jobs.service import list_jobs

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
