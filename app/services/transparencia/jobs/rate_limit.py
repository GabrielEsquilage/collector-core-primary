import asyncio
import os
from datetime import datetime
from time import monotonic
from zoneinfo import ZoneInfo

from app.services.transparencia.jobs.definitions import RESTRICTED_RESOURCE

TIMEZONE_NAME = os.getenv("PORTAL_TRANSPARENCIA_RATE_LIMIT_TIMEZONE", "America/Sao_Paulo")
GLOBAL_MAX_REQUESTS_PER_MINUTE = int(os.getenv("PORTAL_TRANSPARENCIA_MAX_REQUESTS_PER_MINUTE", "10"))
MIN_REQUEST_INTERVAL_SECONDS = float(os.getenv("PORTAL_TRANSPARENCIA_MIN_INTERVAL_SECONDS", "5"))


class PortalRequestRateLimiter:
    def __init__(self):
        self.window_started_at = monotonic()
        self.requests_in_window = 0
        self.current_limit: int | None = None
        self.last_request_at: float | None = None
        self.lock = asyncio.Lock()
        self.timezone = ZoneInfo(TIMEZONE_NAME)

    def _current_limit_for_resource(self, resource: str) -> int:
        if resource == RESTRICTED_RESOURCE:
            resource_limit = int(os.getenv("PORTAL_TRANSPARENCIA_RESTRICTED_REQUESTS_PER_MINUTE", "10"))
            return max(1, min(resource_limit, GLOBAL_MAX_REQUESTS_PER_MINUTE))

        now = datetime.now(self.timezone)
        if 0 <= now.hour < 6:
            resource_limit = int(
                os.getenv(
                    "PORTAL_TRANSPARENCIA_UNRESTRICTED_NIGHT_REQUESTS_PER_MINUTE",
                    "700",
                )
            )
            return max(1, min(resource_limit, GLOBAL_MAX_REQUESTS_PER_MINUTE))

        resource_limit = int(
            os.getenv(
                "PORTAL_TRANSPARENCIA_UNRESTRICTED_DAY_REQUESTS_PER_MINUTE",
                "400",
            )
        )
        return max(1, min(resource_limit, GLOBAL_MAX_REQUESTS_PER_MINUTE))

    async def acquire(self, resource: str) -> None:
        async with self.lock:
            limit = self._current_limit_for_resource(resource)
            elapsed = monotonic() - self.window_started_at

            if self.current_limit != limit or elapsed >= 60:
                self.current_limit = limit
                self.window_started_at = monotonic()
                self.requests_in_window = 0
                elapsed = 0

            if self.last_request_at is not None:
                spacing_elapsed = monotonic() - self.last_request_at
                if spacing_elapsed < MIN_REQUEST_INTERVAL_SECONDS:
                    await asyncio.sleep(MIN_REQUEST_INTERVAL_SECONDS - spacing_elapsed)
                    elapsed = monotonic() - self.window_started_at

            if self.requests_in_window >= limit:
                wait_seconds = max(0.0, 60 - elapsed)
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                self.current_limit = self._current_limit_for_resource(resource)
                self.window_started_at = monotonic()
                self.requests_in_window = 0

            self.requests_in_window += 1
            self.last_request_at = monotonic()


_shared_portal_request_limiter: PortalRequestRateLimiter | None = None


def get_shared_portal_request_limiter() -> PortalRequestRateLimiter:
    global _shared_portal_request_limiter

    if _shared_portal_request_limiter is None:
        _shared_portal_request_limiter = PortalRequestRateLimiter()

    return _shared_portal_request_limiter
