import logging
import httpx
import polars as pl
from psycopg2.extras import execute_values
import os
import psycopg2

logger = logging.getLogger(__name__)

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    
    user = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASS", "postgres")
    db_name = os.getenv("DB_NAME", "datacrypt_db")
    port = os.getenv("DB_PORT", "5433")
    return psycopg2.connect(
        dbname=db_name,
        user=user,
        password=pwd,
        host="localhost",
        port=port
    )

async def extract_sidra_data(url: str):
    logger.info(f"Fetching SIDRA data from {url}")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
    if not data or len(data) <= 1:
        logger.warning("No data returned from SIDRA")
        return None

    # Task 3.1: Ignorar o cabeçalho descritivo no índice 0
    raw_df = pl.DataFrame(data[1:])
    return raw_df

def transform_sidra_data(df: pl.DataFrame):
    # Task 3.2: Limpeza e tipagem (Polars)
    # Selecionar e renomear colunas essenciais
    df_clean = df.select([
        pl.col("D1C").alias("codigo_ibge_municipio"),
        pl.col("D3C").alias("ano"),
        pl.col("D2C").alias("variavel_codigo"),
        pl.col("V").alias("valor_estatistico")
    ])
    
    from datetime import datetime
    
    # Cast dos tipos
    df_clean = df_clean.with_columns([
        pl.col("codigo_ibge_municipio").cast(pl.Utf8),
        pl.col("ano").cast(pl.Int32),
        pl.col("variavel_codigo").cast(pl.Utf8),
        # Em casos onde o IBGE manda "..." ou "-", substituiremos por None/Null para poder fazer o cast
        pl.col("valor_estatistico")
          .str.replace_all(r"[^0-9\.]", "", literal=False)
          .cast(pl.Float64, strict=False),
        pl.lit(datetime.utcnow()).alias("created_at")
    ])
    
    # Drop rows that failed to parse into valid float values
    df_clean = df_clean.drop_nulls(subset=["valor_estatistico"])
    
    return df_clean

def load_sidra_data(df: pl.DataFrame):
    # Task 3.3: Carga Batch no PostgreSQL
    records = df.rows()
    if not records:
        logger.info("No records to load after transformation.")
        return 0
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    insert_query = """
        INSERT INTO datacrypt.fato_demografia 
        (codigo_ibge_municipio, ano, variavel_codigo, valor_estatistico, created_at)
        VALUES %s
        ON CONFLICT (codigo_ibge_municipio, ano, variavel_codigo) 
        DO UPDATE SET 
            valor_estatistico = EXCLUDED.valor_estatistico
    """
    
    try:
        logger.info("Executing Batch Upsert on datacrypt.fato_demografia...")
        execute_values(cur, insert_query, records, page_size=2000)
        conn.commit()
        inserted = len(records)
        logger.info(f"Loaded {inserted} records successfully.")
        return inserted
    except Exception as e:
        conn.rollback()
        logger.exception(f"Failed to load SIDRA data: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

async def sync_sidra_population_2022():
    # Exemplo: Tabela 9514 (População Censo 2022), Nível 6 (Municípios),
    # filtrando todos do Paraná "in n3 41" (ou todos do Brasil se usar all)
    # Vamos pegar todos do Brasil usando "n6/all"
    url = "https://apisidra.ibge.gov.br/values/t/9514/n6/all/v/93/p/2022"
    
    raw_df = await extract_sidra_data(url)
    if raw_df is None:
        return {"inserted": 0, "status": "no_data"}
        
    df_clean = transform_sidra_data(raw_df)
    inserted = load_sidra_data(df_clean)
    
    return {"inserted": inserted, "status": "success"}

async def sync_sidra_population_2010():
    # Censo 2010: Tabela 202, Nível 6 (Municípios), Variável 93, Período 2010
    url = "https://apisidra.ibge.gov.br/values/t/202/n6/all/v/93/p/2010"
    
    raw_df = await extract_sidra_data(url)
    if raw_df is None:
        return {"inserted": 0, "status": "no_data"}
        
    df_clean = transform_sidra_data(raw_df)
    inserted = load_sidra_data(df_clean)
    
    return {"inserted": inserted, "status": "success"}
