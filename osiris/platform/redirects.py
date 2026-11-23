"""Following a redirect without handing credentials to another host."""

from __future__ import annotations

from http.client import HTTPMessage
from typing import IO
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request


class SameOriginCredentials(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> Request | None:
        onward = super().redirect_request(req, fp, code, msg, headers, newurl)
        if onward is not None and _origin(newurl) != _origin(req.full_url):
            onward.remove_header("Authorization")
        return onward


def _origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    return parts.scheme, parts.netloc
