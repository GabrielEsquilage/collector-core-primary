from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.database import SQLALCHEMY_DATABASE_URL
from app.models import FatoDemografia, DimSiconfiEnte

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("FatoDemografia:")
results = db.query(FatoDemografia).limit(5).all()
for r in results:
    print(f"IBGE: {r.codigo_ibge_municipio}, Ano: {r.ano}, Variavel: {r.variavel_codigo}, Valor: {r.valor_estatistico}")

print("DimSiconfiEnte:")
results = db.query(DimSiconfiEnte).filter(DimSiconfiEnte.populacao != None).limit(5).all()
for r in results:
    print(f"IBGE: {r.cod_ibge}, Exercicio: {r.exercicio}, Pop: {r.populacao}")
