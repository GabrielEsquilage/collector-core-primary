import os
import duckdb
from fastapi import APIRouter, HTTPException, Path
from typing import List

from app.schemas.siconfi import SiconfiKpiMacroResponse, SiconfiKpiMacroBase, SiconfiRankingResponse, SiconfiRankingItem
from fastapi import Query
from app.services.siconfi.siconfi_catalog import IndicadorMacro

router = APIRouter(prefix="/siconfi", tags=["SICONFI"])

DATA_LAKE_ROOT = os.getenv("DATA_LAKE_ROOT", "data_lake")
GOLD_PATH = os.path.join(DATA_LAKE_ROOT, "gold", "siconfi_macro")

@router.get("/municipio/{cod_ibge}/kpis/{ano}", response_model=SiconfiKpiMacroResponse)
def get_kpis_municipio(
    cod_ibge: str = Path(..., description="Código IBGE do Município (7 dígitos)"),
    ano: int = Path(..., description="Ano do exercício financeiro")
):
    """
    Retorna os KPIs consolidados da camada Gold para um município específico em um determinado ano.
    Os dados são agregados por bimestre (periodo).
    """
    gold_file = os.path.join(GOLD_PATH, f"kpis_macro_{ano}.parquet")
    
    if not os.path.exists(gold_file):
        raise HTTPException(status_code=404, detail=f"Dados consolidados não encontrados para o ano {ano}")
    
    try:
        # Usamos duckdb para consultar o parquet de forma rápida e eficiente
        query = f"""
            SELECT *
            FROM read_parquet('{gold_file}')
            WHERE cod_ibge = '{cod_ibge}'
            ORDER BY periodo ASC
        """
        
        with duckdb.connect() as con:
            df = con.execute(query).df()
            
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Nenhum dado encontrado para o município {cod_ibge} no ano {ano}")
            
        # Converte NaN para None (null em JSON)
        df = df.where(df.notnull(), None)
        
        records = df.to_dict(orient='records')
        
        return SiconfiKpiMacroResponse(
            ano=ano,
            data=[SiconfiKpiMacroBase(**row) for row in records]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")

@router.get("/ranking/{indicador}/ano/{ano}", response_model=SiconfiRankingResponse)
def get_ranking_siconfi(
    indicador: IndicadorMacro = Path(..., description="O indicador para o ranking"),
    ano: int = Path(..., description="Ano do exercício financeiro"),
    uf: str = Query(None, description="Filtrar por UF (Opcional)"),
    limit: int = Query(10, description="Quantidade máxima de resultados"),
    ordem: str = Query("desc", description="Ordem do ranking ('asc' ou 'desc')")
):
    """
    Retorna o ranking dos municípios para um determinado indicador (Ex: despesa_saude),
    utilizando o último período reportado por cada município naquele ano.
    """
    gold_file = os.path.join(GOLD_PATH, f"kpis_macro_{ano}.parquet")
    
    if not os.path.exists(gold_file):
        raise HTTPException(status_code=404, detail=f"Dados consolidados não encontrados para o ano {ano}")
        
    try:
        ordem_sql = "ASC" if ordem.lower() == "asc" else "DESC"
        uf_filter = f"AND t.uf = '{uf.upper()}'" if uf else ""
        
        query = f"""
            WITH latest_period AS (
                SELECT cod_ibge, MAX(periodo) as max_periodo
                FROM read_parquet('{gold_file}')
                GROUP BY cod_ibge
            )
            SELECT t.cod_ibge, t.uf, t.periodo, t.{indicador.value} as valor
            FROM read_parquet('{gold_file}') t
            JOIN latest_period lp ON t.cod_ibge = lp.cod_ibge AND t.periodo = lp.max_periodo
            WHERE t.{indicador.value} IS NOT NULL {uf_filter}
            ORDER BY valor {ordem_sql}
            LIMIT {limit}
        """
        
        with duckdb.connect() as con:
            df = con.execute(query).df()
            
        # Converte NaN para None
        df = df.where(df.notnull(), None)
        
        records = df.to_dict(orient='records')
        
        # Opcional: tratar valor nulo se houver no topo do ranking asc
        for r in records:
            if r['valor'] is None:
                r['valor'] = 0.0
                
        return SiconfiRankingResponse(
            ano=ano,
            indicador=indicador.value,
            data=[SiconfiRankingItem(**row) for row in records]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")
