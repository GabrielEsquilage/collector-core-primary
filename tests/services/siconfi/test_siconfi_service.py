import pytest
import respx
from httpx import Response
from app.services.siconfi.siconfi_service import SiconfiService

@pytest.fixture
def service():
    return SiconfiService()

@pytest.mark.asyncio
@respx.mock
async def test_get_entes_success(service):
    # Mock da API do Siconfi para retornar entes simulados
    mock_response = [
        {"cod_ibge": "3550308", "ente": "São Paulo", "capital": True, "regiao": "Sudeste", "uf": "SP", "esfera": "M"},
        {"cod_ibge": "3304557", "ente": "Rio de Janeiro", "capital": True, "regiao": "Sudeste", "uf": "RJ", "esfera": "M"}
    ]
    
    # Note: O endpoint exato mockado deve bater com a URL que o SiconfiService chama por baixo dos panos
    # Aqui estamos mockando qualquer GET para apidatalake.tesouro.gov.br
    respx.get(url__startswith="https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes").mock(
        return_value=Response(200, json={"items": mock_response})
    )
    
    entes = await service.get_entes()
    
    assert len(entes) == 2
    assert entes[0]["ente"] == "São Paulo"
    assert entes[1]["ente"] == "Rio de Janeiro"

@pytest.mark.asyncio
@respx.mock
async def test_get_rreo_success(service):
    mock_rreo = [
        {"exercicio": 2023, "periodo": 1, "cod_ibge": "3550308", "valor": 1000.50}
    ]
    
    respx.get(url__startswith="https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo").mock(
        return_value=Response(200, json={"items": mock_rreo})
    )
    
    rreo = await service.get_rreo(
        an_exercicio=2023,
        nr_periodo=1,
        co_tipo_demonstrativo='RREO',
        id_ente='3550308'
    )
    
    assert len(rreo) == 1
    assert rreo[0]["exercicio"] == 2023
    assert rreo[0]["valor"] == 1000.50
