from app.services.transparencia.filters import classify_registro, is_dashboard_eligible

def test_classify_registro_invalido():
    assert classify_registro(" Este codigo invalido foo ") == "invalido"

def test_classify_registro_excecao():
    assert classify_registro("Exc - Pagamento especial") == "excecao"

def test_classify_registro_ignorado():
    assert classify_registro("ignorado pelo sistema") == "ignorado"

def test_classify_registro_valido():
    assert classify_registro("Bolsa Familia Regular") == "valido"

def test_is_dashboard_eligible():
    assert is_dashboard_eligible("valido") is True
    assert is_dashboard_eligible("invalido") is False
    assert is_dashboard_eligible("excecao") is False
    assert is_dashboard_eligible("ignorado") is False
