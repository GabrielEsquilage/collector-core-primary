from app.database import SessionLocal
from app.models import FatoRepasseMunicipio, TransparenciaCargaJob, TransparenciaCargaJobItem

db = SessionLocal()
try:
    print("Deleting FatoRepasseMunicipio...")
    db.query(FatoRepasseMunicipio).delete()
    print("Deleting TransparenciaCargaJobItem...")
    db.query(TransparenciaCargaJobItem).delete()
    print("Deleting TransparenciaCargaJob...")
    db.query(TransparenciaCargaJob).delete()
    db.commit()
    print("All transparency jobs and benefit data wiped successfully.")
except Exception as e:
    db.rollback()
    print("Error:", e)
finally:
    db.close()
