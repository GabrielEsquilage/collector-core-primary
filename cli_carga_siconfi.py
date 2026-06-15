import asyncio
import argparse
from loguru import logger
import sys
import os

# Adiciona a raiz do projeto ao path para rodar como script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.siconfi.siconfi_service import SiconfiService
from app.services.siconfi.rreo_sync_service import RreoSyncService

async def executar_carga_manual(anos: list[int], delay_segundos: float = 90.0, limite: int = 0):
    """
    Executa a carga histórica em lote, baixando dados do SICONFI de forma sequencial.
    Aplica um delay entre requisições para evitar rate limits na API do Tesouro.
    """
    logger.info("==================================================")
    logger.info(f" INICIANDO CARGA HISTÓRICA SICONFI ")
    logger.info(f" Anos Alvo: {anos}")
    logger.info(f" Delay configurado: {delay_segundos}s entre cada ente")
    logger.info("==================================================")
    
    siconfi = SiconfiService()
    sync_service = RreoSyncService()
    
    logger.info("Consultando dicionário de Municípios (IBGE)...")
    entes = await siconfi.get_entes()
    codigos_ibge = [str(ente['cod_ibge']) for ente in entes if ente.get('cod_ibge')]
    
    if limite > 0:
        logger.warning(f"Modo Teste (--limite): Restringindo a extração para {limite} municípios.")
        codigos_ibge = codigos_ibge[:limite]
        
    logger.info(f"Total de municípios para extração: {len(codigos_ibge)}")
    
    for ano in anos:
        logger.info(f"\n---> Processando o ano {ano} <---")
        periodos = [1, 2, 3, 4, 5, 6]
        
        for idx, ente in enumerate(codigos_ibge, start=1):
            logger.info(f"[{idx}/{len(codigos_ibge)}] Ano: {ano} | IBGE: {ente} | Coletando bimestres...")
            
            try:
                await sync_service.extract_and_load_silver(
                    entes_ibge=[ente], 
                    ano=ano, 
                    periodos=periodos
                )
            except Exception as e:
                logger.error(f"Falha ao extrair ente {ente}: {str(e)}")
            
            if idx < len(codigos_ibge):
                logger.debug(f"Pausa de {delay_segundos}s ativada.")
                await asyncio.sleep(delay_segundos)
                
        logger.info(f"Consolidando a Camada Ouro para o ano {ano}...")
        sync_service.build_gold_layer(ano=ano)
        logger.info(f"Ano {ano} finalizado.")

    logger.info("=== CARGA HISTÓRICA CONCLUÍDA ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de Carga Histórica do SICONFI")
    
    parser.add_argument("--anos", nargs="+", type=int, default=[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], 
                        help="Anos a serem processados (ex: --anos 2018 2019)")
    
    parser.add_argument("--delay", type=float, default=90.0, 
                        help="Espera entre os entes em segundos (Padrão: 90.0)")
    
    parser.add_argument("--limite", type=int, default=0, 
                        help="Limite de municípios para teste rápido")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(executar_carga_manual(args.anos, args.delay, args.limite))
    except KeyboardInterrupt:
        logger.warning("\nExecução interrompida pelo usuário.")
