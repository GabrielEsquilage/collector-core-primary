import os
import duckdb
from fastapi import APIRouter, HTTPException, Path
from typing import List

from app.schemas.siconfi import (
    SiconfiKpiMacroResponse, SiconfiKpiMacroBase, SiconfiRankingResponse, SiconfiRankingItem,
    SiconfiSerieHistoricaItem, SiconfiSerieHistoricaResponse,
    SiconfiAgregacaoItem, SiconfiAgregacaoResponse, SiconfiComparativoResponse
)
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


@router.get("/municipio/{cod_ibge}/serie-historica/{indicador}", response_model=SiconfiSerieHistoricaResponse)
def get_serie_historica_siconfi(
    cod_ibge: str = Path(..., description="Código IBGE do Município"),
    indicador: IndicadorMacro = Path(..., description="O indicador para visualizar a série histórica")
):
    """
    Retorna a evolução histórica de um determinado indicador para um município específico
    em todos os anos e bimestres disponíveis na camada Gold.
    """
    try:
        query = f"""
            SELECT CAST(regexp_extract(filename, 'kpis_macro_([0-9]+)\\.parquet', 1) AS INTEGER) AS ano,
                   periodo,
                   {indicador.value} AS valor
            FROM read_parquet('{GOLD_PATH}/*.parquet', filename=true)
            WHERE cod_ibge = '{cod_ibge}'
              AND {indicador.value} IS NOT NULL
            ORDER BY ano ASC, periodo ASC
        """
        
        with duckdb.connect() as con:
            df = con.execute(query).df()
            
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Nenhum dado encontrado para o município {cod_ibge} e indicador {indicador.value}")
            
        df = df.where(df.notnull(), None)
        records = df.to_dict(orient='records')
        
        for r in records:
            if r['valor'] is None:
                r['valor'] = 0.0
                
        return SiconfiSerieHistoricaResponse(
            cod_ibge=cod_ibge,
            indicador=indicador.value,
            data=[SiconfiSerieHistoricaItem(**row) for row in records]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")


@router.get("/agregacao/ano/{ano}", response_model=SiconfiAgregacaoResponse)
def get_agregacao_siconfi(
    ano: int = Path(..., description="Ano do exercício financeiro"),
    uf: str = Query(None, description="Filtrar por Estado (Opcional). Se não passado, agrega nacional.")
):
    """
    Retorna a soma de todos os KPIs agrupados por período (bimestre) para um estado específico ou nacionalmente.
    """
    gold_file = os.path.join(GOLD_PATH, f"kpis_macro_{ano}.parquet")
    
    if not os.path.exists(gold_file):
        raise HTTPException(status_code=404, detail=f"Dados consolidados não encontrados para o ano {ano}")
        
    try:
        uf_filter = f"WHERE uf = '{uf.upper()}'" if uf else ""
        
        # Cria as cláusulas de SUM para todos os indicadores dinamicamente baseados no SICONFI_CATALOG
        sum_clauses = ",\n".join([f"SUM({ind.value}) as {ind.value}" for ind in IndicadorMacro])
        
        query = f"""
            SELECT periodo,
                   {sum_clauses}
            FROM read_parquet('{gold_file}')
            {uf_filter}
            GROUP BY periodo
            ORDER BY periodo ASC
        """
        
        with duckdb.connect() as con:
            df = con.execute(query).df()
            
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Nenhum dado encontrado na agregação para o ano {ano}")
            
        df = df.where(df.notnull(), None)
        records = df.to_dict(orient='records')
        
        return SiconfiAgregacaoResponse(
            ano=ano,
            uf=uf.upper() if uf else None,
            data=[SiconfiAgregacaoItem(**row) for row in records]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")


@router.get("/comparativo/ano/{ano}", response_model=SiconfiComparativoResponse)
def get_comparativo_siconfi(
    ano: int = Path(..., description="Ano do exercício financeiro"),
    codigos_ibge: str = Query(..., description="Códigos IBGE separados por vírgula (ex: 111,222)")
):
    """
    Retorna os KPIs consolidados para múltiplos municípios lado a lado, facilitando comparativos.
    """
    gold_file = os.path.join(GOLD_PATH, f"kpis_macro_{ano}.parquet")
    
    if not os.path.exists(gold_file):
        raise HTTPException(status_code=404, detail=f"Dados consolidados não encontrados para o ano {ano}")
        
    try:
        ibge_list = [cod.strip() for cod in codigos_ibge.split(",") if cod.strip()]
        if not ibge_list:
            raise HTTPException(status_code=400, detail="Nenhum código IBGE válido fornecido")
            
        ibge_sql = ", ".join([f"'{cod}'" for cod in ibge_list])
        
        query = f"""
            SELECT *
            FROM read_parquet('{gold_file}')
            WHERE cod_ibge IN ({ibge_sql})
            ORDER BY cod_ibge ASC, periodo ASC
        """
        
        with duckdb.connect() as con:
            df = con.execute(query).df()
            
        df = df.where(df.notnull(), None)
        records = df.to_dict(orient='records')
        
        return SiconfiComparativoResponse(
            ano=ano,
            data=[SiconfiKpiMacroBase(**row) for row in records]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a requisição: {str(e)}")
