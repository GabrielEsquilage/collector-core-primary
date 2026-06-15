import pytest
from app.services.transparencia.jobs.definitions import (
    iter_mes_ano,
    get_resource_config,
    build_monthly_job_plans,
    build_municipio_monthly_job_plans,
)

def test_iter_mes_ano():
    # Same year
    assert iter_mes_ano("202301", "202303") == ["202301", "202302", "202303"]
    # Crossing years
    assert iter_mes_ano("202211", "202302") == ["202211", "202212", "202301", "202302"]

def test_get_resource_config():
    config = get_resource_config("bolsa-familia-por-municipio")
    assert config["tipo_beneficio"] == "bolsa_familia"
    
    with pytest.raises(ValueError, match="Resource nao suportado"):
        get_resource_config("beneficio-inexistente")

def test_build_monthly_job_plans():
    plans = build_monthly_job_plans(
        estado_sigla="SP",
        resource="bolsa-familia-por-municipio",
        start="202301",
        end="202302",
        municipios=645
    )
    
    assert len(plans) == 2
    assert plans[0]["job_code"] == "bf-sp-202301"
    assert plans[0]["descricao"] == "Bolsa Familia SP 202301"
    assert plans[0]["mes_ano_inicio"] == "202301"
    assert plans[0]["municipios"] == 645
    assert plans[0]["job_granularity"] == "estado_mes"

def test_build_municipio_monthly_job_plans():
    municipios = [{"codigo_ibge": "3550308", "nome": "São Paulo"}]
    
    plans = build_municipio_monthly_job_plans(
        estado_sigla="SP",
        resource="auxilio-brasil-por-municipio",
        start="202201",
        end="202201",
        municipios=municipios
    )
    
    assert len(plans) == 1
    assert plans[0]["job_code"] == "ab-sp-202201-3550308"
    assert "São Paulo (3550308)" in plans[0]["descricao"]
    assert plans[0]["job_granularity"] == "municipio_mes"
    assert plans[0]["municipio_codigo_ibge"] == "3550308"
