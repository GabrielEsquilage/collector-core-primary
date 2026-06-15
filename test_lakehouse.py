import asyncio
import os
import pandas as pd
import duckdb
from app.services.siconfi.siconfi_service import SiconfiService

# Configurações do diretório do Lakehouse
DATA_LAKE_PATH = "data_lake/silver/siconfi_rreo"

async def extract_and_load_to_lakehouse():
    print("1. Iniciando Extração SICONFI na Camada Bronze (JSON -> Memória)...")
    service = SiconfiService()
    
    # Vamos simular a carga de 2 bimestres de 2023 para SP e RJ
    # Cod IBGE: SP = 3550308, RJ = 3304557
    entes = ["3550308", "3304557"]
    periodos = [1, 2]
    ano = 2023
    
    all_data = []
    
    for ente in entes:
        for periodo in periodos:
            print(f"   Coletando Ente: {ente} | Ano: {ano} | Bimestre: {periodo}...")
            rreo_data = await service.get_rreo(
                an_exercicio=ano, 
                nr_periodo=periodo, 
                co_tipo_demonstrativo='RREO', 
                id_ente=ente
            )
            all_data.extend(rreo_data)
            
    print(f"\n2. Extração Concluída! Total de registros brutos: {len(all_data)}")
    
    # ---------------------------------------------------------
    # Camada Prata (Transformação Pandas e Salvamento Parquet)
    # ---------------------------------------------------------
    print("3. Convertendo com Pandas e salvando particionado por Ano...")
    df = pd.DataFrame(all_data)
    
    # Limpa colunas desnecessárias, tipa os dados e prepara a coluna de partição (ano)
    df_clean = df[['exercicio', 'periodo', 'cod_ibge', 'uf', 'instituicao', 'anexo', 'coluna', 'conta', 'valor']].copy()
    df_clean.rename(columns={'exercicio': 'ano'}, inplace=True)
    df_clean['cod_ibge'] = df_clean['cod_ibge'].astype(str)
    df_clean['valor'] = pd.to_numeric(df_clean['valor'], errors='coerce')
    
    os.makedirs(DATA_LAKE_PATH, exist_ok=True)
    
    # Salva usando pyarrow com suporte a particionamento
    df_clean.to_parquet(
        DATA_LAKE_PATH,
        engine='pyarrow',
        partition_cols=['ano'],
        index=False
    )
    
    print(f"4. Arquivos Parquet gerados fisicamente no disco em: '{DATA_LAKE_PATH}/ano={ano}/'\n")

def query_with_duckdb():
    print("5. Consultando o Data Lake direto do disco com DuckDB...")
    
    con = duckdb.connect()
    
    print("\n=> CONSULTA 1: Top 5 maiores Receitas Realizadas (Bimestre 1 e 2)")
    query1 = f"""
        SELECT 
            uf,
            periodo,
            SUM(valor) / 1000000000 AS receitas_bilhoes
        FROM read_parquet('{DATA_LAKE_PATH}/**/*.parquet', hive_partitioning=1)
        WHERE coluna LIKE '%RECEITAS REALIZADAS%'
          AND conta LIKE 'RECEITAS (EXCETO%'
        GROUP BY uf, periodo
        ORDER BY uf, periodo;
    """
    res1 = con.execute(query1).df()
    print(res1)
    
    print("\n=> CONSULTA 2: Despesas Liquidadas por UF")
    query2 = f"""
        SELECT 
            uf,
            SUM(valor) / 1000000000 AS despesas_liquidadas_bilhoes
        FROM read_parquet('{DATA_LAKE_PATH}/**/*.parquet', hive_partitioning=1)
        WHERE coluna LIKE '%DESPESAS LIQUIDADAS%'
        GROUP BY uf
        ORDER BY despesas_liquidadas_bilhoes DESC;
    """
    res2 = con.execute(query2).df()
    print(res2)

async def main():
    await extract_and_load_to_lakehouse()
    query_with_duckdb()

if __name__ == "__main__":
    asyncio.run(main())
