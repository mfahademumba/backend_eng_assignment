from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


async def log_api_request_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log API request completion with timing and basic request metadata."""
    start_time = time.perf_counter()
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "api_request_failed method=%s path=%s duration_ms=%.2f client=%s",
            method,
            path,
            duration_ms,
            client_host,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "api_request_completed method=%s path=%s status_code=%s duration_ms=%.2f client=%s",
        method,
        path,
        response.status_code,
        duration_ms,
        client_host,
    )
    return response
