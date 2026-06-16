import os
import pandas as pd
import duckdb
from loguru import logger
from typing import List

from .siconfi_service import SiconfiService
from .siconfi_catalog import SICONFI_CATALOG, IndicadorMacro

class RreoSyncService:
    def __init__(self, data_lake_root: str = "data_lake"):
        self.service = SiconfiService()
        self.silver_path = os.path.join(data_lake_root, "silver", "siconfi_rreo")
        self.gold_path = os.path.join(data_lake_root, "gold", "siconfi_macro")

    async def extract_and_load_silver(self, entes_ibge: List[str], ano: int, periodos: List[int]):
        logger.info(f"Iniciando extração RREO {ano} para {len(entes_ibge)} entes...")
        all_data = []
        
        for ente in entes_ibge:
            for periodo in periodos:
                try:
                    logger.debug(f"Coletando RREO: {ente} | Ano: {ano} | Bimestre: {periodo}")
                    rreo_data = await self.service.get_rreo(ano, periodo, 'RREO', ente)
                    all_data.extend(rreo_data)
                except Exception as e:
                    logger.error(f"Erro ao coletar Ente {ente} ({ano}/{periodo}): {e}")
                    
        if not all_data:
            logger.warning("Nenhum dado coletado.")
            return

        df = pd.DataFrame(all_data)
        
        df_clean = df[['exercicio', 'periodo', 'cod_ibge', 'uf', 'instituicao', 'anexo', 'coluna', 'conta', 'valor']].copy()
        df_clean.rename(columns={'exercicio': 'ano'}, inplace=True)
        df_clean['cod_ibge'] = df_clean['cod_ibge'].astype(str)
        df_clean['valor'] = pd.to_numeric(df_clean['valor'], errors='coerce')
        
        # Garante que só vamos salvar os dados do ano que realmente solicitamos
        df_clean = df_clean[df_clean['ano'] == ano].copy()
        
        if df_clean.empty:
            logger.warning(f"A API não retornou dados válidos para o ano {ano}. Ignorando salvamento.")
            return

        # Removemos a coluna ano pois ela será inferida pelo Hive Partitioning do DuckDB (nome da pasta)
        df_clean.drop(columns=['ano'], inplace=True)
        
        # Caminho explícito para a partição do ano
        partition_path = os.path.join(self.silver_path, f"ano={ano}")
        os.makedirs(partition_path, exist_ok=True)
        
        # Salva um arquivo determinístico por ente para evitar milhares de arquivos com UUID
        ente_ref = entes_ibge[0] if entes_ibge else "lote"
        file_path = os.path.join(partition_path, f"rreo_{ente_ref}.parquet")
        
        df_clean.to_parquet(
            file_path,
            engine='pyarrow',
            index=False
        )
        logger.info(f"Camada Prata atualizada em {file_path}")

    def build_gold_layer(self, ano: int):
        logger.info(f"Construindo Camada Ouro para o ano {ano}...")
        con = duckdb.connect()
        
        select_parts = ["cod_ibge", "uf", "periodo"]
        
        for indicador, regras in SICONFI_CATALOG.items():
            col_name = indicador.value
            anexo = regras["anexo"]
            coluna_like = regras["coluna_like"]
            conta_like = regras["conta_like"]
            
            sql_case = f"""
                SUM(CASE 
                    WHEN anexo = '{anexo}' 
                     AND coluna LIKE '{coluna_like}' 
                     AND conta LIKE '{conta_like}' 
                    THEN valor ELSE 0 
                END) AS {col_name}
            """
            select_parts.append(sql_case)

        select_clause = ",\n".join(select_parts)
        
        query = f"""
            SELECT {select_clause}
            FROM read_parquet('{self.silver_path}/**/*.parquet', hive_partitioning=1)
            WHERE ano = {ano}
            GROUP BY cod_ibge, uf, periodo
        """
        
        df_gold = con.execute(query).df()
        
        os.makedirs(self.gold_path, exist_ok=True)
        gold_file = os.path.join(self.gold_path, f"kpis_macro_{ano}.parquet")
        df_gold.to_parquet(gold_file, engine='pyarrow', index=False)
        
        logger.info(f"Camada Ouro gerada com sucesso: {gold_file} ({len(df_gold)} linhas)")
