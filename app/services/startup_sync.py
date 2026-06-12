import asyncio
import logging
import os

from fastapi import FastAPI

from app.services.ibge.localidades_sync_service import sync_localidades_with_new_session
from app.services.transparencia.collector import (
    collect_orgaos_siape_with_new_session,
    collect_orgaos_siafi_with_new_session,
)

logger = logging.getLogger(__name__)


def _is_enabled(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def run_startup_sync(app: FastAPI):
    results = {}
    errors = {}

    if _is_enabled("IBGE_SYNC_ON_STARTUP", "true"):
        try:
            logger.info("Starting IBGE sync...")
            results["ibge"] = await asyncio.to_thread(sync_localidades_with_new_session)
            
            from app.services.ibge.metadados_sync_service import sync_metadados_pesquisas_with_new_session
            logger.info("Starting IBGE researches metadata sync...")
            results["ibge_metadados"] = await sync_metadados_pesquisas_with_new_session()
            
            from app.services.ibge.periodos_sync_service import sync_all_periodos_with_new_session
            logger.info("Starting IBGE researches periods sync...")
            results["ibge_periodos"] = await sync_all_periodos_with_new_session()
            
            from app.services.ibge.sidra_sync_service import sync_sidra_population_2022, sync_sidra_population_2010
            logger.info("Starting SIDRA population 2022 sync...")
            results["sidra_pop_2022"] = await sync_sidra_population_2022()
            
            logger.info("Starting SIDRA population 2010 sync...")
            results["sidra_pop_2010"] = await sync_sidra_population_2010()
            
            logger.info("IBGE sync finished successfully.")
        except Exception as exc:
            errors["ibge"] = str(exc)
            logger.exception("IBGE startup sync failed")

    if _is_enabled("TRANSPARENCIA_SYNC_ON_STARTUP", "true"):
        try:
            logger.info("Starting Transparencia SIAFI sync...")
            results["transparencia_siafi"] = await collect_orgaos_siafi_with_new_session()
            logger.info("Transparencia SIAFI sync finished successfully.")
        except Exception as exc:
            errors["transparencia_siafi"] = str(exc)
            logger.exception("Transparencia SIAFI startup sync failed")

        try:
            logger.info("Starting Transparencia SIAPE sync...")
            results["transparencia_siape"] = await collect_orgaos_siape_with_new_session()
            logger.info("Transparencia SIAPE sync finished successfully.")
        except Exception as exc:
            errors["transparencia_siape"] = str(exc)
            logger.exception("Transparencia SIAPE startup sync failed")

    app.state.startup_sync_results = results
    app.state.startup_sync_errors = errors
    app.state.startup_sync_finished = True


async def start_startup_sync(app: FastAPI):
    app.state.startup_sync_results = {}
    app.state.startup_sync_errors = {}
    app.state.startup_sync_finished = False
    # Executa a carga de forma síncrona na inicialização do Uvicorn
    # para garantir que os dados estejam no banco antes de aceitar requisições.
    await run_startup_sync(app)
