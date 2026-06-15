import duckdb
import pandas as pd

def main():
    con = duckdb.connect()
    query = """
        SELECT anexo, conta, SUM(valor) as total
        FROM read_parquet('data_lake/silver/siconfi_rreo/**/*.parquet', hive_partitioning=1)
        WHERE coluna LIKE '%DESPESAS LIQUIDADAS%' OR coluna LIKE '%RECEITAS REALIZADAS%' OR coluna LIKE '%TOTAL%'
        GROUP BY anexo, conta
        ORDER BY total DESC
        LIMIT 100;
    """
    try:
        df = con.execute(query).df()
        pd.set_option('display.max_rows', 100)
        pd.set_option('display.max_colwidth', 80)
        print("--- Principais Contas por Volume Financeiro ---")
        print(df.head(50))
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
