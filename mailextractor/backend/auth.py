from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuthMiddleware(BaseHTTPMiddleware):
    """Identify who is making the request and store it on request.state.username."""

    def __init__(self, app, header_name: str = "X-Web-Auth"):
        super().__init__(app)
        self.header_name = header_name.lower()

    async def dispatch(self, request: Request, call_next):
        header_value = request.headers.get(self.header_name)
        request.state.username = header_value if header_value else "anon"
        return await call_next(request)
