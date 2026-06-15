import os
import duckdb
from fastapi import APIRouter, HTTPException, Path
from typing import List

from app.schemas.siconfi import SiconfiKpiMacroResponse, SiconfiKpiMacroBase

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
