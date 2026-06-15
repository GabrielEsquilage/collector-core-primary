import json
from io import BytesIO
import pytest
from urllib.error import HTTPError, URLError

from app.services.ibge.ibge_service import fetch_municipios, _request_ibge

def test_fetch_municipios_success(mocker):
    # Prepare a fake JSON response
    mock_data = [{"id": 3550308, "nome": "São Paulo"}]
    mock_payload = json.dumps(mock_data).encode("utf-8")
    
    # Mock the urlopen context manager
    mock_response = mocker.MagicMock()
    mock_response.read.return_value = mock_payload
    mock_response.headers.get.return_value = "application/json"
    
    # We mock urlopen to return our fake context manager
    mock_urlopen = mocker.patch("app.services.ibge.ibge_service.urlopen")
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = fetch_municipios()
    
    assert len(result) == 1
    assert result[0]["nome"] == "São Paulo"
    mock_urlopen.assert_called_once()

def test_request_ibge_http_error(mocker):
    mock_urlopen = mocker.patch("app.services.ibge.ibge_service.urlopen")
    # Simulate an HTTPError
    mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)
    
    with pytest.raises(RuntimeError, match="IBGE respondeu HTTP 404"):
        _request_ibge("municipios")

def test_request_ibge_url_error(mocker):
    mock_urlopen = mocker.patch("app.services.ibge.ibge_service.urlopen")
    # Simulate an URLError
    mock_urlopen.side_effect = URLError("Network is unreachable")
    
    with pytest.raises(RuntimeError, match="Falha ao acessar a API do IBGE"):
        _request_ibge("municipios")
