from unittest.mock import AsyncMock
import pytest
from app.services.transparencia.beneficios import (
    _collect_beneficio_municipio,
    _collect_beneficio_municipio_ano,
    _get_beneficio_spec,
    _normalize_beneficio_record,
)

def test_normalize_beneficio_record():
    spec = _get_beneficio_spec("bolsa_familia")
    item = {
        "id": 123,
        "dataReferencia": "202001",
        "municipio": {"codigoIBGE": "3550308"},
        "valor": "100.50",
        "quantidadeBeneficiados": "50",
    }
    
    result = _normalize_beneficio_record(item, spec=spec)
    
    assert result["id_externo"] == 123
    assert result["tipo_beneficio"] == "bolsa_familia"
    assert result["municipio_codigo_ibge"] == "3550308"
    assert float(result["valor"]) == 100.50
    assert result["quantidade_beneficiados"] == 50

@pytest.mark.asyncio
async def test_collect_beneficio_municipio(mocker):
    # Mockando a classe TransparenciaClient para não ir para a internet
    # e retornar apenas 1 página com 2 registros simulados
    mock_client_instance = mocker.AsyncMock()
    async def mock_iter_pages(*args, **kwargs):
        yield (1, [{"id": 1, "dataReferencia": "202001", "municipio": {"codigoIBGE": "123"}, "valor": 10, "quantidadeBeneficiados": 1},
                   {"id": 2, "dataReferencia": "202001", "municipio": {"codigoIBGE": "123"}, "valor": 20, "quantidadeBeneficiados": 2}])
        
    mock_client_instance.iter_pages = mock_iter_pages
    
    # Precisamos mockar o context manager (__aenter__ e __aexit__)
    mock_client_class = mocker.patch("app.services.transparencia.beneficios.TransparenciaClient")
    mock_client_class.return_value.__aenter__.return_value = mock_client_instance
    
    # Mockamos a função de salvar no parquet
    mock_save = mocker.patch("app.services.transparencia.beneficios._save_beneficio_to_parquet", new_callable=AsyncMock)
    mock_save.return_value = 2 # 2 registros inseridos
    
    spec = _get_beneficio_spec("bolsa_familia")
    
    summary = await _collect_beneficio_municipio(
        db=None,  # db is unused
        spec=spec,
        mes_ano="202001",
        codigo_ibge="123"
    )
    
    assert summary["pages_collected"] == 1
    assert summary["records_received"] == 2
    assert summary["inserted"] == 2
    mock_save.assert_awaited_once()

@pytest.mark.asyncio
async def test_collect_beneficio_municipio_ano(mocker):
    # Mockando _collect_beneficio_municipio para simular os 12 meses
    mock_collect = mocker.patch("app.services.transparencia.beneficios._collect_beneficio_municipio", new_callable=AsyncMock)
    mock_collect.return_value = {
        "tipo_beneficio": "bolsa_familia",
        "mes_ano": "mocked",
        "codigo_ibge": "123",
        "pages_collected": 1,
        "records_received": 10,
        "inserted": 10,
        "updated": 0
    }
    
    spec = _get_beneficio_spec("bolsa_familia")
    
    result = await _collect_beneficio_municipio_ano(
        db=None,
        spec=spec,
        ano=2020,
        codigo_ibge="123"
    )
    
    # 12 meses do ano x 1 página cada = 12 páginas, 120 registros
    assert result["months_processed"] == 12
    assert result["pages_collected"] == 12
    assert result["records_received"] == 120
    assert result["inserted"] == 120
    assert mock_collect.call_count == 12
