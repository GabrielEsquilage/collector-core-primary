import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_gold_layer(tmp_path):
    """
    Creates a dummy parquet file to simulate the Siconfi Gold Layer.
    """
    ano = 2018
    file_path = tmp_path / f"kpis_macro_{ano}.parquet"
    
    data = [
        {
            "cod_ibge": "1234567",
            "uf": "SP",
            "periodo": 1,
            "receita_total": 1000.50,
            "despesa_total": 800.00,
            "receita_corrente_liquida": None,
            "despesa_saude": 200.0,
            "despesa_educacao": 150.0,
            "despesa_saneamento": 0.0,
            "despesa_urbanismo": 0.0,
            "despesa_seguranca": 0.0,
            "investimentos": 10.0,
            "despesa_pessoal": 0.0,
            "divida_consolidada": 0.0,
            "restos_a_pagar": 0.0,
            "resultado_primario": 0.0,
            "resultado_previdenciario": 0.0,
            "ppp_contratadas": 0.0
        },
        {
            "cod_ibge": "1234567",
            "uf": "SP",
            "periodo": 2,
            "receita_total": 1200.00,
            "despesa_total": 900.00,
            "receita_corrente_liquida": 1100.0,
            "despesa_saude": 220.0,
            "despesa_educacao": 160.0,
            "despesa_saneamento": 0.0,
            "despesa_urbanismo": 0.0,
            "despesa_seguranca": 0.0,
            "investimentos": 15.0,
            "despesa_pessoal": 0.0,
            "divida_consolidada": 0.0,
            "restos_a_pagar": 0.0,
            "resultado_primario": 0.0,
            "resultado_previdenciario": 0.0,
            "ppp_contratadas": 0.0
        }
    ]
    
    df = pd.DataFrame(data)
    df.to_parquet(file_path, engine="pyarrow", index=False)
    
    return tmp_path

def test_get_kpis_municipio_success(mock_gold_layer):
    with patch("app.api.routes.siconfi.GOLD_PATH", str(mock_gold_layer)):
        response = client.get("/api/v1/siconfi/municipio/1234567/kpis/2018")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ano"] == 2018
        assert len(data["data"]) == 2
        
        assert data["data"][0]["cod_ibge"] == "1234567"
        assert data["data"][0]["periodo"] == 1
        assert data["data"][0]["receita_total"] == 1000.50
        assert data["data"][0]["receita_corrente_liquida"] is None
        
        assert data["data"][1]["periodo"] == 2
        assert data["data"][1]["receita_total"] == 1200.00

def test_get_kpis_municipio_not_found_year(mock_gold_layer):
    with patch("app.api.routes.siconfi.GOLD_PATH", str(mock_gold_layer)):
        response = client.get("/api/v1/siconfi/municipio/1234567/kpis/2019")
        
        assert response.status_code == 404
        assert "não encontrados para o ano 2019" in response.json()["detail"]

def test_get_kpis_municipio_not_found_ibge(mock_gold_layer):
    with patch("app.api.routes.siconfi.GOLD_PATH", str(mock_gold_layer)):
        response = client.get("/api/v1/siconfi/municipio/9999999/kpis/2018")
        
        assert response.status_code == 404
        assert "Nenhum dado encontrado para o município 9999999 no ano 2018" in response.json()["detail"]
