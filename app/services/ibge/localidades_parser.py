def _extract_uf(municipio):
    microrregiao = municipio.get("microrregiao")
    if microrregiao is not None:
        return microrregiao["mesorregiao"]["UF"]

    regiao_imediata = municipio.get("regiao-imediata")
    if regiao_imediata is not None:
        return regiao_imediata["regiao-intermediaria"]["UF"]

    raise RuntimeError(
        f"Municipio {municipio.get('id')} sem caminho válido para identificar a UF"
    )


def parse_localidades(municipios):
    regioes = {}
    estados = {}
    municipios_normalizados = {}

    for municipio in municipios:
        uf = _extract_uf(municipio)
        regiao = uf["regiao"]

        regioes[regiao["id"]] = {
            "id_regiao": regiao["id"],
            "nome": regiao["nome"],
        }
        estados[uf["id"]] = {
            "id_estado": uf["id"],
            "nome": uf["nome"],
            "sigla": uf["sigla"],
            "id_regiao": regiao["id"],
        }
        municipios_normalizados[municipio["id"]] = {
            "id_municipio": municipio["id"],
            "nome": municipio["nome"],
            "id_estado": uf["id"],
        }

    return {
        "regioes": list(regioes.values()),
        "estados": list(estados.values()),
        "municipios": list(municipios_normalizados.values()),
    }
