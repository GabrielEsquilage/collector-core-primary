import re

with open('app/services/transparencia/jobs/runner.py', 'r') as f:
    content = f.read()

content = content.replace('from app.database import SessionLocal', 'from app.database import AsyncSessionLocal')

# Replace sync repository imports with async ones
content = content.replace(
    'from app.services.transparencia.jobs.repository import (',
    '''from app.services.transparencia.jobs.repository import (
    utcnow,
)
from app.services.transparencia.jobs.repository_async import (
    async_claim_next_job_item,
    async_get_job,
    async_mark_job_item_failed,
    async_mark_job_item_success,
    async_refresh_job_counts,'''
)

content = content.replace('from sqlalchemy.orm import Session', 'from sqlalchemy.ext.asyncio import AsyncSession')

# _mark_job_running
content = re.sub(
    r'def _mark_job_running\(job_id: int\) -> TransparenciaCargaJob \| None:\n\s+with SessionLocal\(\) as db:\n\s+job = get_job\(db, job_id\)',
    'async def _mark_job_running(job_id: int) -> TransparenciaCargaJob | None:\n    async with AsyncSessionLocal() as db:\n        job = await async_get_job(db, job_id)',
    content
)
content = content.replace('        db.commit()\n        db.refresh(job)\n        return refresh_job_counts(db, job)', '        await db.commit()\n        await db.refresh(job)\n        return await async_refresh_job_counts(db, job)')

# _claim_next_job_item_context
content = re.sub(
    r'def _claim_next_job_item_context\(\n\s+job_id: int,\n\s+\*,\n\s+max_attempts: int,\n\) -> JobItemContext \| None:\n\s+with SessionLocal\(\) as db:\n\s+item = claim_next_job_item\(db, job_id=job_id, max_attempts=max_attempts\)',
    'async def _claim_next_job_item_context(\n    job_id: int,\n    *,\n    max_attempts: int,\n) -> JobItemContext | None:\n    async with AsyncSessionLocal() as db:\n        item = await async_claim_next_job_item(db, job_id=job_id, max_attempts=max_attempts)',
    content
)

# _refresh_job_counts
content = re.sub(
    r'def _refresh_job_counts\(job_id: int\) -> TransparenciaCargaJob \| None:\n\s+with SessionLocal\(\) as db:\n\s+job = get_job\(db, job_id\)',
    'async def _refresh_job_counts(job_id: int) -> TransparenciaCargaJob | None:\n    async with AsyncSessionLocal() as db:\n        job = await async_get_job(db, job_id)',
    content
)
content = content.replace('        return refresh_job_counts(db, job)', '        return await async_refresh_job_counts(db, job)')

# _mark_job_item_success_and_refresh
content = re.sub(
    r'def _mark_job_item_success_and_refresh\(\n\s+job_id: int,\n\s+item_id: int,\n\s+metrics: JobItemExecutionMetrics,\n\) -> TransparenciaCargaJob \| None:\n\s+with SessionLocal\(\) as db:\n\s+mark_job_item_success\(db, item_id, metrics\)\n\s+job = get_job\(db, job_id\)',
    'async def _mark_job_item_success_and_refresh(\n    job_id: int,\n    item_id: int,\n    metrics: JobItemExecutionMetrics,\n) -> TransparenciaCargaJob | None:\n    async with AsyncSessionLocal() as db:\n        await async_mark_job_item_success(db, item_id, metrics)\n        job = await async_get_job(db, job_id)',
    content
)

# _mark_job_item_failed_and_refresh
content = re.sub(
    r'def _mark_job_item_failed_and_refresh\(\n\s+job_id: int,\n\s+item_id: int,\n\s+error_message: str,\n\) -> TransparenciaCargaJob \| None:\n\s+with SessionLocal\(\) as db:\n\s+mark_job_item_failed\(db, item_id, error_message\)\n\s+job = get_job\(db, job_id\)',
    'async def _mark_job_item_failed_and_refresh(\n    job_id: int,\n    item_id: int,\n    error_message: str,\n) -> TransparenciaCargaJob | None:\n    async with AsyncSessionLocal() as db:\n        await async_mark_job_item_failed(db, item_id, error_message)\n        job = await async_get_job(db, job_id)',
    content
)

# _finalize_job and finalize_job
content = re.sub(
    r'def finalize_job\(db: Session, job: TransparenciaCargaJob\) -> TransparenciaCargaJob:\n\s+job = refresh_job_counts\(db, job\)',
    'async def async_finalize_job(db: AsyncSession, job: TransparenciaCargaJob) -> TransparenciaCargaJob:\n    job = await async_refresh_job_counts(db, job)',
    content
)
content = content.replace('    db.commit()\n    db.refresh(job)\n    return refresh_job_counts(db, job)', '    await db.commit()\n    await db.refresh(job)\n    return await async_refresh_job_counts(db, job)')

content = re.sub(
    r'def _finalize_job\(job_id: int\) -> TransparenciaCargaJob \| None:\n\s+with SessionLocal\(\) as db:\n\s+job = get_job\(db, job_id\)',
    'async def _finalize_job(job_id: int) -> TransparenciaCargaJob | None:\n    async with AsyncSessionLocal() as db:\n        job = await async_get_job(db, job_id)',
    content
)
content = content.replace('        return finalize_job(db, job)', '        return await async_finalize_job(db, job)')

# _mark_job_failed
content = re.sub(
    r'def _mark_job_failed\(job_id: int\) -> None:\n\s+with SessionLocal\(\) as db:\n\s+job = get_job\(db, job_id\)',
    'async def _mark_job_failed(job_id: int) -> None:\n    async with AsyncSessionLocal() as db:\n        job = await async_get_job(db, job_id)',
    content
)
content = content.replace('        job.finished_at = utcnow()\n        db.commit()', '        job.finished_at = utcnow()\n        await db.commit()')

# execute_job_item parameter
content = content.replace('execute_job_item(\n    db: Session,', 'execute_job_item(\n    db: AsyncSession,')

# run_job updates
content = content.replace('job = _mark_job_running(job_id)', 'job = await _mark_job_running(job_id)')
content = content.replace('item_context = _claim_next_job_item_context(job.id, max_attempts=max_attempts)', 'item_context = await _claim_next_job_item_context(job.id, max_attempts=max_attempts)')
content = content.replace('with SessionLocal() as db:', 'async with AsyncSessionLocal() as db:')
content = content.replace('job = _mark_job_item_failed_and_refresh(', 'job = await _mark_job_item_failed_and_refresh(')
content = content.replace('job = _mark_job_item_success_and_refresh(', 'job = await _mark_job_item_success_and_refresh(')
content = content.replace('_finalize_job(job.id)', 'await _finalize_job(job.id)')
content = content.replace('_mark_job_failed(job_id)', 'await _mark_job_failed(job_id)')

with open('app/services/transparencia/jobs/runner.py', 'w') as f:
    f.write(content)

