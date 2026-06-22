from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, distinct
from app.database import SQLALCHEMY_DATABASE_URL
from app.models import FatoDemografia

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

vars = db.query(distinct(FatoDemografia.variavel_codigo)).all()
print("Variables:", vars)
