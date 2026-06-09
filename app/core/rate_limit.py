from collections import defaultdict, deque
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_window: int, window_seconds: int):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        client_host = request.client.host if request.client else "unknown"
        now = monotonic()
        hits = self._hits[client_host]

        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.requests_per_window:
            return JSONResponse(
                {"detail": "Rate limit exceeded."},
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )

        hits.append(now)
        return await call_next(request)
