def classify_registro(descricao: str) -> str:
    descricao_normalizada = descricao.strip()
    descricao_upper = descricao_normalizada.upper()

    if "CODIGO INVALIDO" in descricao_upper:
        return "invalido"
    if descricao_normalizada.startswith("Exc -"):
        return "excecao"
    if descricao_upper.startswith("IGNORADO"):
        return "ignorado"
    return "valido"


def is_dashboard_eligible(status_registro: str) -> bool:
    return status_registro == "valido"
