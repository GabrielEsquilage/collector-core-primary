from app.database import SessionLocal
from app.models import TransparenciaCargaJob

db = SessionLocal()
jobs = db.query(TransparenciaCargaJob).order_by(TransparenciaCargaJob.id.desc()).limit(20).all()
for j in jobs:
    print(j.job_code, j.metadata_json)
