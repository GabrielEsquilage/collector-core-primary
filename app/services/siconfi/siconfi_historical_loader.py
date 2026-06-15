import os
import pandas as pd
from loguru import logger
import argparse
from .rreo_sync_service import RreoSyncService

def carregar_dump_csv(caminho_csv: str, ano: int):
    """
    Carrega o dump oficial em CSV do SICONFI (Dados Abertos)
    e injeta na Camada Prata do Lakehouse como se tivesse vindo da API.
    """
    logger.info(f"Iniciando carga histórica do ano {ano} a partir do arquivo: {caminho_csv}")
    
    if not os.path.exists(caminho_csv):
        logger.error(f"Arquivo não encontrado: {caminho_csv}")
        return

    # O CSV do Tesouro pode ser grande, Pandas ou Polars dão conta.
    # O encoding padrão do governo costuma ser latin1 ou utf-8, e o separador ponto e vírgula
    logger.info("Lendo arquivo CSV gigante... isso pode levar 1 ou 2 minutos.")
    try:
        df_csv = pd.read_csv(caminho_csv, sep=';', encoding='latin1', low_memory=False)
    except Exception as e:
        logger.warning(f"Falha ao ler com latin1, tentando utf-8. Erro: {e}")
        df_csv = pd.read_csv(caminho_csv, sep=';', encoding='utf-8', low_memory=False)

    logger.info(f"CSV Carregado! Total de linhas brutas: {len(df_csv)}")

    # O CSV do Governo pode vir com nomes de colunas ligeiramente diferentes do JSON da API.
    # Vamos padronizar para o nosso formato Lakehouse (Prata)
    # Exemplo de mapeamento padrão (pode precisar de ajuste dependendo do CSV do ano)
    mapa_colunas = {
        'exercicio': 'ano',
        'periodo': 'periodo',
        'cod_ibge': 'cod_ibge',
        'uf': 'uf',
        'instituicao': 'instituicao',
        'anexo': 'anexo',
        'coluna': 'coluna',
        'conta': 'conta',
        'valor': 'valor'
    }

    # Renomeando colunas (ignorando maiúsculas/minúsculas caso venha diferente)
    df_csv.columns = [c.lower().strip() for c in df_csv.columns]
    
    # Pegamos apenas as colunas que importam para o nosso Parquet
    colunas_presentes = [c for c in df_csv.columns if c in mapa_colunas.keys() or c in mapa_colunas.values()]
    df_clean = df_csv[colunas_presentes].copy()
    
    # Garante que as nomenclaturas batem com a nossa Camada Prata
    df_clean.rename(columns=mapa_colunas, inplace=True)
    
    # Tratamento de Tipos
    if 'ano' not in df_clean.columns:
        df_clean['ano'] = ano
        
    df_clean['cod_ibge'] = df_clean['cod_ibge'].astype(str)
    
    # No CSV o valor costuma vir com vírgula para decimal (ex: 1500,50)
    if df_clean['valor'].dtype == object:
        df_clean['valor'] = df_clean['valor'].str.replace(',', '.').astype(float)
    else:
        df_clean['valor'] = pd.to_numeric(df_clean['valor'], errors='coerce')

    # ==========================================
    # 2. SALVAR NA CAMADA PRATA (PARQUET)
    # ==========================================
    service = RreoSyncService()
    
    os.makedirs(service.silver_path, exist_ok=True)
    
    logger.info("Salvando na Camada Prata particionada...")
    df_clean.to_parquet(
        service.silver_path,
        engine='pyarrow',
        partition_cols=['ano'],
        index=False
    )
    logger.info(f"Carga Histórica da Camada Prata concluída! Salvo em {service.silver_path}/ano={ano}")
    
    # ==========================================
    # 3. GERAR CAMADA OURO
    # ==========================================
    logger.info("Gerando Camada Ouro (KPIs) a partir do Histórico...")
    service.build_gold_layer(ano=ano)
    logger.info("Carga Retroativa FINALIZADA COM SUCESSO!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carrega dump CSV do SICONFI para o Lakehouse.")
    parser.add_argument("--arquivo", type=str, required=True, help="Caminho para o CSV do Tesouro Nacional")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência (ex: 2018)")
    
    args = parser.parse_args()
    carregar_dump_csv(args.arquivo, args.ano)
