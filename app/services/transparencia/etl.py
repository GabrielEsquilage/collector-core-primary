import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
import polars as pl
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

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

def run_etl():
    parquet_path = Path("app/data/parquet")
    if not parquet_path.exists():
        print("Nenhum arquivo Parquet encontrado. ETL abortado.")
        return

    print("Iniciando varredura dos arquivos Parquet...")
    
    try:
        # Usa hive_partitioning para descobrir as colunas ano e mes dinamicamente
        df = pl.read_parquet(
            "app/data/parquet/*/*/*/*.parquet",
            hive_partitioning=False  # Nao precisamos pois podemos extrair da estrutura da pasta se for preciso, ou confiar no df
        )
    except Exception as e:
        print(f"Erro ao ler parquet: {e}")
        return
        
    print(f"Registros encontrados no Data Lake: {len(df)}")
    
    if len(df) == 0:
        print("Nenhum dado para processar.")
        return

    # O Parquet gerado ja contem:
    # id_externo, tipo_beneficio, data_referencia, municipio_codigo_ibge, valor, quantidade_beneficiados, payload_json
    # Queremos descartar id_externo e payload_json
    df_clean = df.select([
        "tipo_beneficio",
        "data_referencia",
        "municipio_codigo_ibge",
        "valor",
        "quantidade_beneficiados"
    ])
    
    # Remove duplicatas lógicas (mesmo município, mesmo mês e mesmo tipo_beneficio) pegando o mais recente
    # Mas como já limpamos e cada arquivo parquet tem 1 linha, não deve ter.
    # Mas é uma boa prática
    df_clean = df_clean.unique(
        subset=["tipo_beneficio", "data_referencia", "municipio_codigo_ibge"],
        keep="last"
    )
    
    records = df_clean.to_dicts()
    
    print(f"Registros únicos pós-limpeza: {len(records)}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Cria a tabela caso não exista (via Alembic seria o ideal, mas garantimos aqui)
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS datacrypt;
            CREATE TABLE IF NOT EXISTS datacrypt.fato_repasse_municipio (
                id SERIAL PRIMARY KEY,
                tipo_beneficio VARCHAR(50) NOT NULL,
                data_referencia DATE NOT NULL,
                municipio_codigo_ibge VARCHAR(10) NOT NULL,
                valor NUMERIC(18, 2) NOT NULL,
                quantidade_beneficiados INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(tipo_beneficio, data_referencia, municipio_codigo_ibge)
            );
        """)
        
        insert_query = """
            INSERT INTO datacrypt.fato_repasse_municipio 
            (tipo_beneficio, data_referencia, municipio_codigo_ibge, valor, quantidade_beneficiados)
            VALUES %s
            ON CONFLICT (tipo_beneficio, data_referencia, municipio_codigo_ibge) 
            DO UPDATE SET 
                valor = EXCLUDED.valor,
                quantidade_beneficiados = EXCLUDED.quantidade_beneficiados
        """
        
        values = [
            (
                r["tipo_beneficio"],
                r["data_referencia"],
                r["municipio_codigo_ibge"],
                r["valor"],
                r["quantidade_beneficiados"]
            )
            for r in records
        ]
        
        print("Realizando Upsert no PostgreSQL...")
        execute_values(cur, insert_query, values, page_size=1000)
        
        conn.commit()
        print("Carga Gold (PostgreSQL) concluída com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro durante a carga: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_etl()
