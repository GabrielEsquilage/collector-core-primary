from datetime import date
import pytest
from app.services.transparencia.beneficios import (
    _parse_mes_ano,
    _parse_data_referencia,
    _normalize_estado_sigla,
    validate_beneficio_mes_ano,
    validate_beneficio_ano,
    BeneficioPeriodoInvalidoError,
)

def test_parse_mes_ano_valid():
    assert _parse_mes_ano("202305") == date(2023, 5, 1)

def test_parse_mes_ano_invalid():
    with pytest.raises(ValueError, match="AAAAMM"):
        _parse_mes_ano("2023")
    with pytest.raises(ValueError, match="AAAAMM"):
        _parse_mes_ano("2023AA")

def test_parse_data_referencia():
    # Passando Date
    d = date(2023, 1, 1)
    assert _parse_data_referencia(d) == d
    # Passando string YYYYMM
    assert _parse_data_referencia("202305") == date(2023, 5, 1)
    # Passando data ISO
    assert _parse_data_referencia("2023-08-15T00:00:00") == date(2023, 8, 15)

def test_normalize_estado_sigla():
    assert _normalize_estado_sigla("sp") == "SP"
    assert _normalize_estado_sigla(" rj ") == "RJ"
    with pytest.raises(ValueError, match="exactly 2 letters"):
        _normalize_estado_sigla("S")
    with pytest.raises(ValueError, match="exactly 2 letters"):
        _normalize_estado_sigla("12")

def test_validate_beneficio_mes_ano_bolsa_familia():
    # Valido
    validate_beneficio_mes_ano("bolsa_familia", "202001")
    
    # Transicao
    with pytest.raises(BeneficioPeriodoInvalidoError, match="transicao"):
        validate_beneficio_mes_ano("bolsa_familia", "202111")
        
    # Fora do range
    with pytest.raises(BeneficioPeriodoInvalidoError, match="nao pertence ao periodo"):
        validate_beneficio_mes_ano("bolsa_familia", "202201")

def test_validate_beneficio_ano_bolsa_familia():
    validate_beneficio_ano("bolsa_familia", 2015)
    
    with pytest.raises(BeneficioPeriodoInvalidoError, match="transicao"):
        validate_beneficio_ano("bolsa_familia", 2021)
        
    with pytest.raises(BeneficioPeriodoInvalidoError, match="nao pertence"):
        validate_beneficio_ano("bolsa_familia", 2022)

def test_validate_beneficio_mes_ano_auxilio_brasil():
    validate_beneficio_mes_ano("auxilio_brasil", "202205")
    with pytest.raises(BeneficioPeriodoInvalidoError, match="transicao"):
        validate_beneficio_mes_ano("auxilio_brasil", "202110")
    with pytest.raises(BeneficioPeriodoInvalidoError, match="nao pertence"):
        validate_beneficio_mes_ano("auxilio_brasil", "202401")

def test_validate_beneficio_ano_auxilio_brasil():
    validate_beneficio_ano("auxilio_brasil", 2022)
    with pytest.raises(BeneficioPeriodoInvalidoError, match="transicao"):
        validate_beneficio_ano("auxilio_brasil", 2023)

def test_validate_beneficio_mes_ano_novo_bolsa():
    validate_beneficio_mes_ano("novo_bolsa_familia", "202305")
    with pytest.raises(BeneficioPeriodoInvalidoError, match="transicao"):
        validate_beneficio_mes_ano("novo_bolsa_familia", "202302")
    with pytest.raises(BeneficioPeriodoInvalidoError, match="nao pertence"):
        validate_beneficio_mes_ano("novo_bolsa_familia", "202201")

def test_validate_beneficio_invalid_type():
    with pytest.raises(ValueError, match="Tipo de beneficio nao suportado"):
        validate_beneficio_ano("auxilio_emergencial", 2020)
