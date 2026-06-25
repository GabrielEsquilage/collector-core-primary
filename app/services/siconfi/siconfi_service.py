import httpx
from typing import Dict, Any, List, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

class SiconfiService:
    BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def _request_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    if response.status_code in [502, 503, 504, 429]:
                        logger.warning(f"Erro {response.status_code} na API do Siconfi. Tentativa {attempt + 1}/{max_retries}.")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt + 1)  # Exponential backoff
                            continue
                    response.raise_for_status()
                    data = response.json()
                    return data.get("items", [])
            except httpx.HTTPError as e:
                logger.error(f"HTTP erro ao consultar {url}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt + 1)
                else:
                    raise

    async def get_entes(self) -> List[Dict[str, Any]]:
        return await self._request_with_retry(f"{self.BASE_URL}/entes")

    async def get_rreo(self, an_exercicio: int, nr_periodo: int, co_tipo_demonstrativo: str, id_ente: str) -> List[Dict[str, Any]]:
        params = {
            "an_exercicio": an_exercicio,
            "nr_periodo": nr_periodo,
            "co_tipo_demonstrativo": co_tipo_demonstrativo,
            "id_ente": id_ente
        }
        return await self._request_with_retry(f"{self.BASE_URL}/rreo", params=params)

    async def get_rgf(self, an_exercicio: int, nr_periodo: int, co_tipo_demonstrativo: str, id_ente: str, in_periodicidade: str = "Q") -> List[Dict[str, Any]]:
        params = {
            "an_exercicio": an_exercicio,
            "nr_periodo": nr_periodo,
            "co_tipo_demonstrativo": co_tipo_demonstrativo,
            "id_ente": id_ente,
            "in_periodicidade": in_periodicidade
        }
        return await self._request_with_retry(f"{self.BASE_URL}/rgf", params=params)
