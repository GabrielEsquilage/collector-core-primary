import json
import os
from gzip import decompress
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

IBGE_BASE_URL = os.getenv(
    "IBGE_BASE_URL", "https://servicodados.ibge.gov.br/api/v1/localidades"
)
IBGE_TIMEOUT_SECONDS = float(os.getenv("IBGE_TIMEOUT_SECONDS", "30"))


def _request_ibge(resource: str):
    url = f"{IBGE_BASE_URL.rstrip('/')}/{resource.lstrip('/')}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "datacrypt-collector/1.0",
        },
    )

    try:
        with urlopen(request, timeout=IBGE_TIMEOUT_SECONDS) as response:
            payload = response.read()
            if response.headers.get("Content-Encoding") == "gzip" or payload[:2] == b"\x1f\x8b":
                payload = decompress(payload)
            payload = payload.decode("utf-8")
    except HTTPError as exc:
        raise RuntimeError(f"IBGE respondeu HTTP {exc.code} para {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Falha ao acessar a API do IBGE em {url}") from exc

    data = json.loads(payload)
    if not isinstance(data, list):
        raise RuntimeError(f"Resposta inesperada da API do IBGE para {url}")

    return data


def fetch_municipios():
    return _request_ibge("municipios")
