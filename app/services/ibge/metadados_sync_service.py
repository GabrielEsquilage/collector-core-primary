import httpx
import logging
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import DimPesquisaIBGE

logger = logging.getLogger(__name__)

async def sync_metadados_pesquisas(db: Session) -> dict:
    url = "https://servicodados.ibge.gov.br/api/v2/metadados/pesquisas"
    logger.info(f"Fetching IBGE researches metadata from {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
    ativas = [item for item in data if item.get("situacao") == "Ativa"]
    logger.info(f"Found {len(data)} researches, {len(ativas)} are active.")
    
    if not ativas:
        return {"inserted": 0, "updated": 0, "status": "success"}

    stmt = insert(DimPesquisaIBGE).values([
        {
            "codigo": str(item.get("codigo", "")),
            "nome": item.get("nome", ""),
            "situacao": item.get("situacao", "Ativa"),
            "categoria": item.get("categoria"),
            "periodicidade_divulgacao": item.get("periodicidade_divulgacao"),
            "tags_tematicas": item.get("classificacoes_tematicas", [])
        }
        for item in ativas
    ])
    
    from datetime import datetime
    
    stmt = stmt.on_conflict_do_update(
        index_elements=["codigo"],
        set_={
            "nome": stmt.excluded.nome,
            "situacao": stmt.excluded.situacao,
            "categoria": stmt.excluded.categoria,
            "periodicidade_divulgacao": stmt.excluded.periodicidade_divulgacao,
            "tags_tematicas": stmt.excluded.tags_tematicas,
            "atualizado_em": datetime.utcnow()
        }
    )
    
    db.execute(stmt)
    db.commit()
    
    logger.info("Successfully synced IBGE researches metadata.")
    return {"inserted_or_updated": len(ativas), "status": "success"}

async def sync_metadados_pesquisas_with_new_session() -> dict:
    db = SessionLocal()
    try:
        return await sync_metadados_pesquisas(db)
    except Exception as e:
        logger.exception("Failed to sync IBGE researches metadata")
        db.rollback()
        raise e
    finally:
        db.close()
