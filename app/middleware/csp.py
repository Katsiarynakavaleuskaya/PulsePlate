"""Canonical stateless CSP nonce middleware."""

from __future__ import annotations

import secrets
from typing import cast

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSP_HEADER_NAME = "Content-Security-Policy"


def build_csp_header(nonce: str) -> str:
    """Build the legacy-compatible Content-Security-Policy value."""

    return "; ".join(
        [
            "default-src 'self'",
            (
                "script-src 'self' "
                f"'nonce-{nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com"
            ),
            (
                "style-src 'self' "
                f"'nonce-{nonce}' https://fonts.googleapis.com https://cdn.jsdelivr.net"
            ),
            "img-src 'self' data: https:",
            "font-src 'self' https://fonts.gstatic.com",
            "frame-ancestors 'none'",
            "object-src 'none'",
        ]
    )


class CSPNonceMiddleware:
    """Attach one unpredictable CSP nonce to each HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        nonce = secrets.token_urlsafe(16)
        state = scope.setdefault("state", {})
        state["csp_nonce"] = nonce
        csp_header = build_csp_header(nonce)

        async def send_with_csp(message: Message) -> None:
            if message["type"] != "http.response.start":
                await send(message)
                return

            response_start = cast(Message, dict(message))
            response_start["headers"] = list(message.get("headers", []))
            headers = MutableHeaders(scope=response_start)
            headers[CSP_HEADER_NAME] = csp_header
            await send(response_start)

        await self.app(scope, receive, send_with_csp)


__all__ = ["CSP_HEADER_NAME", "CSPNonceMiddleware", "build_csp_header"]
