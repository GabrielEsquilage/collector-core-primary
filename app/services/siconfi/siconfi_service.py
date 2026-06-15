import httpx
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class SiconfiService:
    BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def get_entes(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/entes")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])

    async def get_rreo(self, an_exercicio: int, nr_periodo: int, co_tipo_demonstrativo: str, id_ente: str) -> List[Dict[str, Any]]:
        params = {
            "an_exercicio": an_exercicio,
            "nr_periodo": nr_periodo,
            "co_tipo_demonstrativo": co_tipo_demonstrativo,
            "id_ente": id_ente
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/rreo", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])

    async def get_rgf(self, an_exercicio: int, nr_periodo: int, co_tipo_demonstrativo: str, id_ente: str, in_periodicidade: str = "Q") -> List[Dict[str, Any]]:
        params = {
            "an_exercicio": an_exercicio,
            "nr_periodo": nr_periodo,
            "co_tipo_demonstrativo": co_tipo_demonstrativo,
            "id_ente": id_ente,
            "in_periodicidade": in_periodicidade
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/rgf", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
