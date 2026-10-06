"""Rate limiting (issue #15).

slowapi is wired in exactly one place:

* :data:`limiter` — the configured :class:`slowapi.Limiter`. Router
  decorators attach the tight per-route budgets from
  :class:`app.config.Settings` (auth 5/min, AI 10/min, export 5/min);
  ``default_limits`` gives every other route ``RATE_LIMIT_GENERAL``
  (100/min) through :class:`slowapi.middleware.SlowAPIMiddleware`.
* Buckets are keyed per authenticated user when the request carries a
  valid access token, and per client IP otherwise, so one tenant cannot
  spend another tenant's allowance while anonymous callers stay capped.
* :func:`rate_limit_exceeded_handler` renders the 429 with the
  ``Retry-After`` header. slowapi's own handler omits it, and its
  X-RateLimit header injection crashes endpoints that return plain
  dicts, so ``headers_enabled`` stays off and this handler writes the
  headers itself.
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.deps import client_ip
from app.services.auth_service import decode_token

logger = logging.getLogger(__name__)

settings = get_settings()

# Conservative Retry-After when the storage backend cannot produce a
# window reset time: a 429 without Retry-After would be worse than one
# that lets the caller back in slightly later than necessary.
FALLBACK_RETRY_AFTER_SECONDS = 60


def rate_limit_key(request: Request) -> str:
    """Identify the caller: authenticated user id first, client IP otherwise."""
    token = request.cookies.get("access_token")
    if not token:
        authorization = request.headers.get("authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer" and credentials:
            token = credentials
    if token:
        payload = decode_token(token)
        if payload is not None and payload.get("type") == "access":
            subject = payload.get("sub")
            if subject:
                return f"user:{subject}"
    return f"ip:{client_ip(request) or '127.0.0.1'}"


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[settings.RATE_LIMIT_GENERAL],
    # slowapi only writes X-RateLimit headers when it is handed a Response
    # object; endpoints returning plain dicts would raise, so the 429
    # handler adds the headers it needs itself.
    headers_enabled=False,
    enabled=settings.RATE_LIMIT_ENABLED,
    strategy=settings.RATE_LIMIT_STRATEGY,
    # Bucket per endpoint function rather than per literal path, so path
    # parameters (/export/{type}) and the /api/* aliases share one bucket
    # and unbounded ids never fragment the key space.
    key_style="endpoint",
)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Answer a breached limit with 429 + Retry-After (and X-RateLimit-*)."""
    retry_after = FALLBACK_RETRY_AFTER_SECONDS
    headers: dict[str, str] = {}
    current_limit = getattr(request.state, "view_rate_limit", None)
    if current_limit is not None:
        item, args = current_limit
        try:
            stats = limiter.limiter.get_window_stats(item, *args)
            retry_after = max(1, int(1 + stats.reset_time - time.time()))
            headers["X-RateLimit-Limit"] = str(item.amount)
            headers["X-RateLimit-Remaining"] = "0"
            headers["X-RateLimit-Reset"] = str(retry_after)
        except Exception:  # storage trouble must not mask the 429 itself
            logger.warning("Could not compute rate limit reset time", exc_info=True)
    headers["Retry-After"] = str(retry_after)

    # Registered as the handler for RateLimitExceeded, which starlette also
    # invokes through the MRO of HTTPException subclasses.
    detail = exc.detail if isinstance(exc, RateLimitExceeded) else "rate limit exceeded"
    return JSONResponse(
        {"detail": f"Rate limit exceeded: {detail}"},
        status_code=429,
        headers=headers,
    )


def install_rate_limit(app: FastAPI) -> None:
    """Attach the limiter, its 429 handler and the general-API middleware.

    Call this *before* ``install_metrics`` so rejected requests are
    counted too, and leave CORS to be added last so it stays the
    outermost layer and browsers can read the 429 body.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
