from app.services.transparencia.normalizer import normalize_raw_record, normalize_clean_record

def test_normalize_raw_record():
    item = {"codigo": " 123 ", "descricao": " Pagamento ", "extra": "data"}
    pagina = 2
    
    result = normalize_raw_record(item, pagina)
    
    assert result["codigo"] == "123"
    assert result["descricao"] == "Pagamento"
    assert result["pagina_origem"] == 2
    assert result["payload_original_json"] == item

def test_normalize_clean_record_valido():
    item = {"codigo": "456", "descricao": "Auxílio"}
    
    result = normalize_clean_record(item)
    
    assert result["codigo"] == "456"
    assert result["descricao"] == "Auxílio"
    assert result["status_registro"] == "valido"
    assert result["elegivel_dashboard"] is True

def test_normalize_clean_record_invalido():
    item = {"codigo": "000", "descricao": "codigo invalido aqui"}
    
    result = normalize_clean_record(item)
    
    assert result["codigo"] == "000"
    assert result["descricao"] == "codigo invalido aqui"
    assert result["status_registro"] == "invalido"
    assert result["elegivel_dashboard"] is False
