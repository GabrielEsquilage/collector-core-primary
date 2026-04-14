import asyncio
import os

import httpx

DEFAULT_TIMEOUT_SECONDS = float(os.getenv("PORTAL_TRANSPARENCIA_TIMEOUT_SECONDS", "30"))
DEFAULT_MAX_RETRIES = int(os.getenv("PORTAL_TRANSPARENCIA_MAX_RETRIES", "3"))
DEFAULT_BACKOFF_SECONDS = float(os.getenv("PORTAL_TRANSPARENCIA_BACKOFF_SECONDS", "0.5"))


def _resolve_api_key() -> str:
    raw_value = os.getenv("PORTAL_TRANSPARENCIA_API_KEY")
    if raw_value is None or not raw_value.strip():
        raise RuntimeError("PORTAL_TRANSPARENCIA_API_KEY environment variable not set")

    raw_value = raw_value.strip().strip('"').strip("'")
    if raw_value.lower().startswith("chave-api-dados:"):
        return raw_value.split(":", 1)[1].strip()
    return raw_value


class TransparenciaClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    ):
        self.base_url = (
            base_url
            or os.getenv(
                "PORTAL_TRANSPARENCIA_BASE_URL",
                "https://api.portaldatransparencia.gov.br/api-de-dados",
            )
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.api_key = _resolve_api_key()

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "chave-api-dados": self.api_key,
            },
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

    async def fetch_page(
        self,
        resource: str,
        pagina: int,
        **filters,
    ) -> list[dict]:
        params = {"pagina": pagina}
        for key, value in filters.items():
            if value is not None:
                params[key] = value

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.get(f"/{resource.lstrip('/')}", params=params)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    raise RuntimeError(
                        f"Resposta inesperada do Portal da Transparencia para {resource}"
                    )
                return data
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code < 500 and status_code != 429:
                    raise RuntimeError(
                        f"Portal da Transparencia respondeu HTTP {status_code} para {resource}"
                    ) from exc
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Portal da Transparencia respondeu HTTP {status_code} para {resource}"
                    ) from exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Falha de comunicacao com o Portal da Transparencia em {resource}"
                    ) from exc

            await asyncio.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
