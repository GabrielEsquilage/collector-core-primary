import pytest
from app.services.transparencia.jobs.service import (
    _normalize_estado_sigla,
    _normalize_codigo_ibge,
    _validate_mes_ano_value,
)

def test_normalize_estado_sigla():
    assert _normalize_estado_sigla("sp") == "SP"
    assert _normalize_estado_sigla(" RJ ") == "RJ"
    with pytest.raises(ValueError, match="exactly 2 letters"):
        _normalize_estado_sigla("S")

def test_normalize_codigo_ibge():
    assert _normalize_codigo_ibge(" 1234567 ") == "1234567"
    with pytest.raises(ValueError, match="contain only digits"):
        _normalize_codigo_ibge("")
    with pytest.raises(ValueError, match="contain only digits"):
        _normalize_codigo_ibge("123456a")

def test_validate_mes_ano_value():
    _validate_mes_ano_value("start", "202305")
    with pytest.raises(ValueError, match="AAAAMM format"):
        _validate_mes_ano_value("start", "2023")
