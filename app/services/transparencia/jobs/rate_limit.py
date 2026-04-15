import asyncio
import os
from datetime import datetime
from time import monotonic
from zoneinfo import ZoneInfo

from app.services.transparencia.jobs.definitions import RESTRICTED_RESOURCE

TIMEZONE_NAME = os.getenv("PORTAL_TRANSPARENCIA_RATE_LIMIT_TIMEZONE", "America/Sao_Paulo")


class PortalRequestRateLimiter:
    def __init__(self):
        self.window_started_at = monotonic()
        self.requests_in_window = 0
        self.current_limit: int | None = None
        self.lock = asyncio.Lock()
        self.timezone = ZoneInfo(TIMEZONE_NAME)

    def _current_limit_for_resource(self, resource: str) -> int:
        if resource == RESTRICTED_RESOURCE:
            return int(os.getenv("PORTAL_TRANSPARENCIA_RESTRICTED_REQUESTS_PER_MINUTE", "180"))

        now = datetime.now(self.timezone)
        if 0 <= now.hour < 6:
            return int(
                os.getenv(
                    "PORTAL_TRANSPARENCIA_UNRESTRICTED_NIGHT_REQUESTS_PER_MINUTE",
                    "700",
                )
            )

        return int(
            os.getenv(
                "PORTAL_TRANSPARENCIA_UNRESTRICTED_DAY_REQUESTS_PER_MINUTE",
                "400",
            )
        )

    async def acquire(self, resource: str) -> None:
        async with self.lock:
            limit = self._current_limit_for_resource(resource)
            elapsed = monotonic() - self.window_started_at

            if self.current_limit != limit or elapsed >= 60:
                self.current_limit = limit
                self.window_started_at = monotonic()
                self.requests_in_window = 0
                elapsed = 0

            if self.requests_in_window >= limit:
                wait_seconds = max(0.0, 60 - elapsed)
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                self.current_limit = self._current_limit_for_resource(resource)
                self.window_started_at = monotonic()
                self.requests_in_window = 0

            self.requests_in_window += 1
