import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

slow_logger = logging.getLogger("stem.slow")
access_logger = logging.getLogger("stem.access")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class SlowRequestMiddleware(BaseHTTPMiddleware):
    """Логує повільні запити (шлях + request_id), без PII."""

    async def dispatch(self, request: Request, call_next):
        from config import settings

        t0 = time.perf_counter()
        response = await call_next(request)
        if settings.slow_request_threshold_ms <= 0:
            return response
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if elapsed_ms >= settings.slow_request_threshold_ms:
            rid = getattr(request.state, "request_id", "-")
            slow_logger.warning(
                "slow_request path=%s ms=%.0f rid=%s",
                request.url.path,
                elapsed_ms,
                rid,
            )
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Один рядок на запит: method, path, status, тривалість, request_id (без query/тілу)."""

    async def dispatch(self, request: Request, call_next):
        from config import settings

        t0 = time.perf_counter()
        response = await call_next(request)
        if settings.access_log:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            rid = getattr(request.state, "request_id", "-")
            access_logger.info(
                "method=%s path=%s status=%s ms=%.1f rid=%s",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                rid,
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
