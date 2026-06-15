import pytest
from unittest.mock import AsyncMock, patch

from app.services.transparencia.jobs.runner import (
    get_item_executor,
)

def test_get_item_executor():
    from app.services.transparencia.beneficios import (
        _collect_beneficio_municipio_ano as collect_bolsa_familia_municipio_ano,
    )
    # Testa se o roteamento está correto
    executor_bf = get_item_executor("bolsa_familia")
    assert executor_bf is not None
    
    executor_ab = get_item_executor("auxilio_brasil")
    assert executor_ab is not None
    
    executor_nbf = get_item_executor("novo_bolsa_familia")
    assert executor_nbf is not None
    
    with pytest.raises(ValueError, match="Tipo de beneficio nao suportado no job runner"):
        get_item_executor("inexistente")
