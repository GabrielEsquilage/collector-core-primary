import os
import sys
import shutil
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
    finished_path = Path("app/data/parquet_finished")
    
    if not parquet_path.exists():
        print("Nenhum arquivo Parquet encontrado. ETL abortado.")
        return

    # Mapeia todos os arquivos .parquet disponíveis na Landing Zone
    files_to_process = list(parquet_path.glob("*/*/*/*.parquet"))
    
    if not files_to_process:
        print("Nenhum dado novo para processar.")
        return

    print(f"Iniciando leitura de {len(files_to_process)} arquivos Parquet...")
    
    try:
        df = pl.read_parquet(files_to_process)
    except Exception as e:
        print(f"Erro ao ler parquets: {e}")
        return
        
    print(f"Registros encontrados no Data Lake: {len(df)}")
    
    if len(df) == 0:
        print("Nenhum dado válido extraído.")
        return

    df_clean = df.select([
        "tipo_beneficio",
        "data_referencia",
        "municipio_codigo_ibge",
        "valor",
        "quantidade_beneficiados"
    ])
    
    df_clean = df_clean.unique(
        subset=["tipo_beneficio", "data_referencia", "municipio_codigo_ibge"],
        keep="last"
    )
    
    values = df_clean.rows()
    
    print(f"Registros únicos pós-limpeza prontos para inserção: {len(values)}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
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
            (tipo_beneficio, data_referencia, municipio_codigo_ibge, valor, quantidade_beneficiados, created_at)
            VALUES %s
            ON CONFLICT (tipo_beneficio, data_referencia, municipio_codigo_ibge) 
            DO UPDATE SET 
                valor = EXCLUDED.valor,
                quantidade_beneficiados = EXCLUDED.quantidade_beneficiados
        """
        
        
        
        print("Realizando Upsert no PostgreSQL...")
        execute_values(cur, insert_query, values, page_size=1000, template="(%s, %s, %s, %s, %s, NOW())")
        
        conn.commit()
        print("Carga Gold (PostgreSQL) concluída com sucesso!")
        
        print(f"Movendo {len(files_to_process)} arquivos para a Processed Zone...")
        for file in files_to_process:
            rel_path = file.relative_to(parquet_path)
            dest_file = finished_path / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file), str(dest_file))
            
        print("Arquivos arquivados com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro durante a carga: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_etl()
