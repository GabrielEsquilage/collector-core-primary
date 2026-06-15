import pytest
from unittest.mock import MagicMock
from app.services.transparencia.jobs.service import (
    queue_job_run,
    TransparenciaCargaJobNotFoundError,
    TransparenciaCargaJobConflictError,
    JOB_STATUS_QUEUED,
    JOB_STATUS_PENDING,
)
from app.models import TransparenciaCargaJob

def test_queue_job_run_not_found(mocker):
    mocker.patch("app.services.transparencia.jobs.service.repository_get_job", return_value=None)
    db = MagicMock()
    with pytest.raises(TransparenciaCargaJobNotFoundError):
        queue_job_run(db, 1)

def test_queue_job_run_success(mocker):
    # Mocking repository methods
    mock_job = TransparenciaCargaJob(id=1, status=JOB_STATUS_PENDING, pending_items=1)
    mocker.patch("app.services.transparencia.jobs.service.repository_get_job", return_value=mock_job)
    mocker.patch("app.services.transparencia.jobs.service.refresh_job_counts", return_value=mock_job)
    mocker.patch("app.services.transparencia.jobs.service.count_retryable_failed_items", return_value=0)
    
    db = MagicMock()
    
    result = queue_job_run(db, 1)
    
    assert result.status == JOB_STATUS_QUEUED
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(mock_job)

def test_queue_job_run_no_pending_items(mocker):
    # Mocking a job with no pending items to execute
    mock_job = TransparenciaCargaJob(id=1, status=JOB_STATUS_PENDING, pending_items=0)
    mocker.patch("app.services.transparencia.jobs.service.repository_get_job", return_value=mock_job)
    mocker.patch("app.services.transparencia.jobs.service.refresh_job_counts", return_value=mock_job)
    mocker.patch("app.services.transparencia.jobs.service.count_retryable_failed_items", return_value=0)
    
    db = MagicMock()
    
    with pytest.raises(TransparenciaCargaJobConflictError, match="nao possui itens pendentes"):
        queue_job_run(db, 1)
