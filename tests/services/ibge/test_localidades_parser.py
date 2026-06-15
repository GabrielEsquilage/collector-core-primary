import pytest
from app.services.ibge.localidades_parser import _extract_uf, parse_localidades

def test_extract_uf_microrregiao():
    municipio = {
        "id": 1,
        "microrregiao": {
            "mesorregiao": {
                "UF": {"id": 35, "nome": "São Paulo", "sigla": "SP", "regiao": {"id": 3, "nome": "Sudeste"}}
            }
        }
    }
    uf = _extract_uf(municipio)
    assert uf["sigla"] == "SP"

def test_extract_uf_regiao_imediata():
    municipio = {
        "id": 1,
        "regiao-imediata": {
            "regiao-intermediaria": {
                "UF": {"id": 33, "nome": "Rio de Janeiro", "sigla": "RJ", "regiao": {"id": 3, "nome": "Sudeste"}}
            }
        }
    }
    uf = _extract_uf(municipio)
    assert uf["sigla"] == "RJ"

def test_extract_uf_invalid():
    with pytest.raises(RuntimeError, match="sem caminho válido para identificar a UF"):
        _extract_uf({"id": 999})

def test_parse_localidades():
    municipios = [
        {
            "id": 3550308,
            "nome": "São Paulo",
            "microrregiao": {
                "mesorregiao": {
                    "UF": {
                        "id": 35,
                        "nome": "São Paulo",
                        "sigla": "SP",
                        "regiao": {"id": 3, "nome": "Sudeste"}
                    }
                }
            }
        }
    ]
    
    result = parse_localidades(municipios)
    
    assert len(result["regioes"]) == 1
    assert result["regioes"][0]["id_regiao"] == 3
    
    assert len(result["estados"]) == 1
    assert result["estados"][0]["sigla"] == "SP"
    
    assert len(result["municipios"]) == 1
    assert result["municipios"][0]["nome"] == "São Paulo"
    assert result["municipios"][0]["id_estado"] == 35
