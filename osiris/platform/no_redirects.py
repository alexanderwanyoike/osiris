"""Refusing to follow a redirect, for a link that was checked before fetching."""

from __future__ import annotations

from urllib.request import HTTPRedirectHandler


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None
