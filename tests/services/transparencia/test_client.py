import os
import pytest
import respx
from httpx import Response
from app.services.transparencia.client import TransparenciaClient

# Injetando uma chave de API fake para todos os testes
@pytest.fixture(autouse=True)
def mock_env_vars(mocker):
    mocker.patch.dict(os.environ, {"PORTAL_TRANSPARENCIA_API_KEY": "fake-api-key"})

@pytest.mark.asyncio
@respx.mock
async def test_fetch_page_success():
    resource = "bpc-por-municipio"
    mock_response = [{"id": 1, "valor": 100.0}]
    
    # Endpoint do mock de acordo com a base_url padrão
    respx.get(f"https://api.portaldatransparencia.gov.br/api-de-dados/{resource}").mock(
        return_value=Response(200, json=mock_response)
    )
    
    async with TransparenciaClient() as client:
        data = await client.fetch_page(resource, pagina=1)
        
    assert len(data) == 1
    assert data[0]["valor"] == 100.0

@pytest.mark.asyncio
@respx.mock
async def test_iter_pages():
    resource = "despesas"
    
    # Simulamos que a primeira página tem dados e a segunda vem vazia
    respx.get(f"https://api.portaldatransparencia.gov.br/api-de-dados/{resource}?pagina=1").mock(
        return_value=Response(200, json=[{"id": 1}])
    )
    respx.get(f"https://api.portaldatransparencia.gov.br/api-de-dados/{resource}?pagina=2").mock(
        return_value=Response(200, json=[])
    )
    
    pages = []
    async with TransparenciaClient() as client:
        async for pagina, records in client.iter_pages(resource, start_page=1):
            pages.append((pagina, records))
            
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert pages[0][1][0]["id"] == 1

@pytest.mark.asyncio
@respx.mock
async def test_fetch_page_retries_on_500():
    resource = "recurso-instavel"
    
    # Criamos um roteador que falha 2 vezes com 500 e acerta na 3ª
    route = respx.get(f"https://api.portaldatransparencia.gov.br/api-de-dados/{resource}")
    route.side_effect = [
        Response(500),
        Response(500),
        Response(200, json=[{"sucesso": True}])
    ]
    
    # Configuramos backoff=0 para o teste rodar rápido
    async with TransparenciaClient(backoff_seconds=0, max_retries=3) as client:
        data = await client.fetch_page(resource, pagina=1)
        
    assert data[0]["sucesso"] is True
    assert route.call_count == 3
