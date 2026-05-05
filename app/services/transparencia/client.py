import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass

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


@dataclass(frozen=True)
class TransparenciaClientConfig:
    base_url: str
    timeout: float
    max_retries: int
    backoff_seconds: float
    api_key: str

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    ) -> "TransparenciaClientConfig":
        resolved_base_url = (
            base_url
            or os.getenv(
                "PORTAL_TRANSPARENCIA_BASE_URL",
                "https://api.portaldatransparencia.gov.br/api-de-dados",
            )
        ).rstrip("/")
        return cls(
            base_url=resolved_base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            api_key=_resolve_api_key(),
        )


class TransparenciaClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        before_request: Callable[[str], Awaitable[None]] | None = None,
    ):
        self.config = TransparenciaClientConfig.from_env(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        self.before_request = before_request
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TransparenciaClient":
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=self._build_headers(),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        client = self.client
        self.client = None
        if client is not None:
            await client.aclose()

    async def fetch_page(
        self,
        resource: str,
        pagina: int,
        **filters,
    ) -> list[dict]:
        response = await self._send_with_retry(
            resource=resource,
            params=self._build_params(pagina=pagina, filters=filters),
        )
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(
                f"Resposta inesperada do Portal da Transparencia para {resource}"
            )
        return data

    async def iter_pages(
        self,
        resource: str,
        *,
        start_page: int = 1,
        **filters,
    ) -> AsyncIterator[tuple[int, list[dict]]]:
        pagina = start_page
        while True:
            records = await self.fetch_page(resource=resource, pagina=pagina, **filters)
            if not records:
                break
            yield pagina, records
            pagina += 1

    def _build_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "chave-api-dados": self.config.api_key,
        }

    def _build_params(
        self,
        *,
        pagina: int,
        filters: Mapping[str, object | None],
    ) -> dict[str, object]:
        params: dict[str, object] = {"pagina": pagina}
        params.update({key: value for key, value in filters.items() if value is not None})
        return params

    async def _send_with_retry(
        self,
        *,
        resource: str,
        params: Mapping[str, object],
    ) -> httpx.Response:
        client = self._require_client()

        for attempt in range(1, self.config.max_retries + 1):
            try:
                if self.before_request is not None:
                    await self.before_request(resource)
                response = await client.get(f"/{resource.lstrip('/')}", params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                if attempt == self.config.max_retries or not self._should_retry_status(
                    exc.response.status_code
                ):
                    raise RuntimeError(
                        self._format_http_error(resource, exc.response.status_code)
                    ) from exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self.config.max_retries:
                    raise RuntimeError(
                        f"Falha de comunicacao com o Portal da Transparencia em {resource}"
                    ) from exc

            await self._sleep_before_retry(attempt)

        raise RuntimeError(f"Falha inesperada ao consultar o recurso {resource}")

    def _require_client(self) -> httpx.AsyncClient:
        if self.client is None:
            raise RuntimeError(
                "TransparenciaClient must be used inside an async context manager"
            )
        return self.client

    @staticmethod
    def _should_retry_status(status_code: int) -> bool:
        return status_code >= 500 or status_code == 429

    @staticmethod
    def _format_http_error(resource: str, status_code: int) -> str:
        return f"Portal da Transparencia respondeu HTTP {status_code} para {resource}"

    async def _sleep_before_retry(self, attempt: int) -> None:
        await asyncio.sleep(self.config.backoff_seconds * (2 ** (attempt - 1)))
