from app.database import SessionLocal
from app.services.transparencia.jobs.service import seed_beneficio_jobs

db = SessionLocal()
try:
    c, e, jobs = seed_beneficio_jobs(
        db,
        resource="novo-bolsa-familia-por-municipio",
        estado_sigla=None,
        mes_ano_inicio="202303",
        mes_ano_fim="202304"
    )
    print(f"Created {c}, Existing {e}")
    states = set(j.metadata_json["estado_sigla"] for j in jobs)
    print(f"States generated: {states}")
finally:
    db.rollback()
    db.close()
