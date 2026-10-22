"""AuthMiddleware: username comes from the proxy header, or "anon" without it."""
import asyncio

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mailextractor.backend.auth import AuthMiddleware


async def _whoami(request):
    return PlainTextResponse(request.state.username)


def _username(headers: dict, **middleware_kwargs) -> str:
    """Run one GET through the middleware (no httpx needed) and return the body."""
    app = Starlette(routes=[Route("/", _whoami)])
    app.add_middleware(AuthMiddleware, **middleware_kwargs)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("test", 0),
        "server": ("test", 80),
    }
    body = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.body":
            body.append(message.get("body", b""))

    asyncio.run(app(scope, receive, send))
    return b"".join(body).decode()


def test_header_sets_username():
    assert _username({"X-Web-Auth": "alice"}) == "alice"


def test_header_name_is_case_insensitive():
    assert _username({"x-web-auth": "alice"}) == "alice"


def test_missing_header_is_anon():
    assert _username({}) == "anon"


def test_empty_header_is_anon():
    assert _username({"X-Web-Auth": ""}) == "anon"


def test_custom_header_name():
    assert _username({"X-Forwarded-User": "bob"}, header_name="X-Forwarded-User") == "bob"
    assert _username({"X-Web-Auth": "bob"}, header_name="X-Forwarded-User") == "anon"
