import asyncio
from loguru import logger
from app.services.siconfi.siconfi_service import SiconfiService
from app.services.siconfi.rreo_sync_service import RreoSyncService

async def carregar_historico_via_api(ano: int, max_municipios: int = 0):
    logger.info(f"=== Iniciando Carga Histórica via API para o Ano {ano} ===")
    
    siconfi = SiconfiService()
    sync_service = RreoSyncService()
    
    # 1. Pegar a lista oficial de municípios na própria API do Siconfi
    logger.info("Buscando catálogo de municípios do Governo...")
    entes = await siconfi.get_entes()
    codigos_ibge = [str(ente['cod_ibge']) for ente in entes if ente.get('cod_ibge')]
    
    # Se passarmos um limite, pega só os N primeiros para teste
    if max_municipios > 0:
        logger.warning(f"Modo Teste: Coletando apenas os {max_municipios} primeiros municípios...")
        codigos_ibge = codigos_ibge[:max_municipios]
        
    logger.info(f"Iniciando coleta na API para {len(codigos_ibge)} municípios. (6 bimestres cada)")
    
    # 2. RREO tem 6 bimestres
    periodos = [1, 2, 3, 4, 5, 6]
    
    # O método que já tínhamos criado faz a mágica (Extrai e salva no Parquet Silver)
    await sync_service.extract_and_load_silver(entes_ibge=codigos_ibge, ano=ano, periodos=periodos)
    
    # 3. Constrói o Resumo Gold
    sync_service.build_gold_layer(ano=ano)
    
    logger.info("=== Carga Retroativa via API Finalizada! ===")

if __name__ == "__main__":
    # Vamos rodar o teste para 2018 limitando a 3 municípios só para você 
    # ver o comportamento real e a velocidade de resposta da API do governo.
    asyncio.run(carregar_historico_via_api(ano=2018, max_municipios=3))
