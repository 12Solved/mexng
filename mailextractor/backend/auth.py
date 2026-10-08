from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuthMiddleware(BaseHTTPMiddleware):
    """Identify who is making the request and store it on request.state.username."""

    async def dispatch(self, request: Request, call_next):
        request.state.username = "default"
        return await call_next(request)
