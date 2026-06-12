import asyncio
import httpx
import logging
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import SessionLocal
from app.models import DimPesquisaIBGE, DimPesquisaPeriodo

logger = logging.getLogger(__name__)

async def sync_periodos_pesquisa(db: Session, codigo_pesquisa: str, client: httpx.AsyncClient):
    url = f"https://servicodados.ibge.gov.br/api/v2/metadados/pesquisas/{codigo_pesquisa}/periodos"
    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch periods for research {codigo_pesquisa}: {e}")
        return 0

    if not data or not isinstance(data, list):
        return 0
        
    inserted_or_updated = 0
    
    # We will use bulk upsert
    stmt = insert(DimPesquisaPeriodo).values([
        {
            "codigo_pesquisa": codigo_pesquisa,
            "ano": item.get("ano", 0),
            "mes": item.get("mes", 0),
            "nome_ocorrencia": item.get("nome_ocorrencia")
        }
        for item in data
    ])
    
    # ON CONFLICT DO NOTHING (or UPDATE if we care about nome_ocorrencia changing)
    # We only care about new periods (insert).
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["codigo_pesquisa", "ano", "mes"]
    )
    
    result = db.execute(stmt)
    db.commit()
    
    if result.rowcount > 0:
        logger.info(f"Added {result.rowcount} new periods for research {codigo_pesquisa}.")
        
    return result.rowcount

async def sync_all_periodos(db: Session):
    stmt = select(DimPesquisaIBGE.codigo).where(DimPesquisaIBGE.situacao == "Ativa")
    pesquisas = db.execute(stmt).scalars().all()
    
    logger.info(f"Found {len(pesquisas)} active researches. Starting periods sync...")
    
    total_new = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Avoid hammering the API, use a small concurrency or sequential
        for codigo in pesquisas:
            new_count = await sync_periodos_pesquisa(db, codigo, client)
            total_new += new_count
            await asyncio.sleep(0.5) # rate limit prevention

    logger.info(f"Period sync finished. Total new periods added: {total_new}")
    return total_new

async def sync_all_periodos_with_new_session():
    db = SessionLocal()
    try:
        return await sync_all_periodos(db)
    except Exception as e:
        logger.exception("Failed to sync IBGE researches periods")
        db.rollback()
        raise e
    finally:
        db.close()
