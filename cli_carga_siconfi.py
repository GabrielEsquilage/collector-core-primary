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
    Script de execução manual projetado para projetos Open Source.
    Baixa os dados um a um, de forma respeitosa (polite scraper), 
    garantindo que qualquer contribuidor possa popular seu banco de dados local.
    """
    logger.info("==================================================")
    logger.info(f" INICIANDO CARGA HISTÓRICA SICONFI OPEN SOURCE ")
    logger.info(f" Anos Alvo: {anos}")
    logger.info(f" Delay configurado: {delay_segundos}s entre cada requisição")
    logger.info("==================================================")
    
    siconfi = SiconfiService()
    sync_service = RreoSyncService()
    
    # 1. Pegar catálogo de entes
    logger.info("Consultando dicionário de Municípios (IBGE)...")
    entes = await siconfi.get_entes()
    codigos_ibge = [str(ente['cod_ibge']) for ente in entes if ente.get('cod_ibge')]
    
    if limite > 0:
        logger.warning(f"Modo Teste (--limite): Limitando a extração para apenas os {limite} primeiros municípios.")
        codigos_ibge = codigos_ibge[:limite]
        
    logger.info(f"Total de Municípios encontrados para extração: {len(codigos_ibge)}")
    
    for ano in anos:
        logger.info(f"\n---> Iniciando processamento do ano {ano} <---")
        periodos = [1, 2, 3, 4, 5, 6] # RREO possui 6 bimestres
        
        # Iteração Município por Município para garantir o delay
        for idx, ente in enumerate(codigos_ibge, start=1):
            logger.info(f"[{idx}/{len(codigos_ibge)}] Ano: {ano} | IBGE: {ente} | Baixando os 6 bimestres...")
            
            try:
                # O sync_service vai tentar baixar e já salvar no Parquet particionado
                await sync_service.extract_and_load_silver(
                    entes_ibge=[ente], 
                    ano=ano, 
                    periodos=periodos
                )
            except Exception as e:
                logger.error(f"Falha ao extrair dado do ente {ente}: {str(e)}")
            
            # Respeitar a regra imposta do Open Source (1.5 minutos entre cada bloco de requisição)
            # Apenas pausa se não for o último município
            if idx < len(codigos_ibge):
                logger.debug(f"Pausa de {delay_segundos} segundos ativada para proteger a API do Tesouro...")
                await asyncio.sleep(delay_segundos)
                
        # Ao final do laço de todos os municípios, consolida a Camada Ouro para o ano
        logger.info(f"Gerando o consolidado Final (Camada Ouro) para o ano {ano}...")
        sync_service.build_gold_layer(ano=ano)
        logger.info(f"Ano {ano} finalizado com Sucesso!")

    logger.info("=== CARGA HISTÓRICA 100% CONCLUÍDA ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script Manual de Carga Histórica do SICONFI")
    # Padrão: 2018 até 2025
    parser.add_argument("--anos", nargs="+", type=int, default=[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], 
                        help="Anos a serem processados separados por espaço (ex: --anos 2018 2019)")
    # Padrão: 1,5 minutos = 90 segundos
    parser.add_argument("--delay", type=float, default=90.0, 
                        help="Tempo de espera entre os entes em segundos (Padrão: 90.0 = 1,5 min)")
    parser.add_argument("--limite", type=int, default=0, 
                        help="Limite de municípios para baixar (útil para testes rápidos)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(executar_carga_manual(args.anos, args.delay, args.limite))

    except KeyboardInterrupt:
        logger.warning("\nExecução interrompida manualmente pelo desenvolvedor. Os dados salvos até agora no Parquet estão seguros!")
