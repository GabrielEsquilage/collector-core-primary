import httpx
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class SiconfiService:
    BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def get_entes(self) -> List[Dict[str, Any]]:
        """
        Retorna a lista de entes federativos mapeados no SICONFI.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/entes")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])

    async def get_rreo(self, an_exercicio: int, nr_periodo: int, co_tipo_demonstrativo: str, id_ente: str) -> List[Dict[str, Any]]:
        """
        Retorna os dados do Relatório Resumido de Execução Orçamentária (RREO).
        
        Args:
            an_exercicio: Ano de exercício (ex: 2023)
            nr_periodo: Número do período (ex: 1 para o 1º bimestre)
            co_tipo_demonstrativo: Tipo do demonstrativo (ex: 'RREO')
            id_ente: Código IBGE do ente federativo
        """
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
        """
        Retorna os dados do Relatório de Gestão Fiscal (RGF).
        
        Args:
            an_exercicio: Ano de exercício (ex: 2023)
            nr_periodo: Número do período (ex: 1, 2, 3 para quadrimestral, ou 1, 2 para semestral)
            co_tipo_demonstrativo: Tipo do demonstrativo (ex: 'RGF')
            id_ente: Código IBGE do ente federativo
            in_periodicidade: 'Q' para Quadrimestral, 'S' para Semestral
        """
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
