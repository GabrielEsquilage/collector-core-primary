import asyncio
from datetime import datetime
import pytest
from app.services.transparencia.jobs.rate_limit import (
    PortalRequestRateLimiter,
    get_shared_portal_request_limiter,
)
from app.services.transparencia.jobs.definitions import RESTRICTED_RESOURCE

@pytest.fixture
def rate_limiter():
    return PortalRequestRateLimiter()

def test_singleton_limiter():
    limiter1 = get_shared_portal_request_limiter()
    limiter2 = get_shared_portal_request_limiter()
    assert limiter1 is limiter2

def test_current_limit_for_resource(rate_limiter, mocker):
    # Mocking datetime to return a specific hour
    class MockDatetime:
        @classmethod
        def now(cls, tz):
            return datetime(2023, 1, 1, 10, 0, 0, tzinfo=tz) # 10 AM (day time)
            
    mocker.patch("app.services.transparencia.jobs.rate_limit.datetime", MockDatetime)
    
    # Check restricted resource limit
    limit = rate_limiter._current_limit_for_resource(RESTRICTED_RESOURCE)
    assert isinstance(limit, int)
    
    # Check day unrestricted resource limit
    limit_day = rate_limiter._current_limit_for_resource("outro-recurso")
    assert isinstance(limit_day, int)

@pytest.mark.asyncio
async def test_acquire_rate_limit(rate_limiter, mocker):
    # Mock sleep so tests run instantly
    mock_sleep = mocker.patch("app.services.transparencia.jobs.rate_limit.asyncio.sleep", new_callable=mocker.AsyncMock)
    
    # Acquire once
    await rate_limiter.acquire("recurso-teste")
    assert rate_limiter.requests_in_window == 1
    
    # Acquire second time (should trigger min interval sleep if fast enough)
    await rate_limiter.acquire("recurso-teste")
    assert rate_limiter.requests_in_window == 2
    mock_sleep.assert_awaited()
