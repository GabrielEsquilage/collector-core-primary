from datetime import datetime, timezone
import pytest
from app.models import TransparenciaCargaJob, TransparenciaCargaJobItem
from app.services.transparencia.jobs.definitions import (
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    ITEM_STATUS_PENDING,
)
from app.services.transparencia.jobs.repository import (
    get_job_by_code,
    list_jobs,
    get_job,
)

def utcnow():
    return datetime.now(timezone.utc)

def test_create_job_and_get(db):
    job = TransparenciaCargaJob(
        job_code="bf-202301",
        descricao="Bolsa Familia 202301",
        tipo_carga="bolsa_familia",
        metadata_json={
            "resource": "bolsa-familia-por-municipio",
            "mes_ano_inicio": "202301",
            "mes_ano_fim": "202301",
            "job_granularity": "estado_mes",
            "municipios": 100
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    assert job.id is not None
    assert job.status == JOB_STATUS_PENDING
    
    # Retrieve
    retrieved = get_job(db, job.id)
    assert retrieved is not None
    assert retrieved.job_code == "bf-202301"
    
    retrieved_by_code = get_job_by_code(db, "bf-202301")
    assert retrieved_by_code is not None
    assert retrieved_by_code.id == job.id

def test_list_jobs(db):
    # Cria dois jobs com status diferentes
    job1 = TransparenciaCargaJob(
        job_code="job-1",
        descricao="Desc 1",
        tipo_carga="bf",
        metadata_json={"resource": "res"},
        status=JOB_STATUS_PENDING
    )
    
    job2 = TransparenciaCargaJob(
        job_code="job-2",
        descricao="Desc 2",
        tipo_carga="bf",
        metadata_json={"resource": "res"},
        status=JOB_STATUS_RUNNING
    )
    db.add_all([job1, job2])
    db.commit()
    db.refresh(job1)
    
    total, jobs = list_jobs(db)
    assert total >= 2
    
    total_pending, jobs_pending = list_jobs(db, status=JOB_STATUS_PENDING)
    assert total_pending >= 1
    assert any(j.id == job1.id for j in jobs_pending)
