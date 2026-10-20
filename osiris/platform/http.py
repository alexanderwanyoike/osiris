"""Talking to local services over HTTP.

``HttpClient`` is the port, ``UrllibClient`` the real adapter (the standard
library, so nothing extra is installed), and ``FakeHttpClient`` serves canned
replies so the code above it is tested without a server running.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

Body = object | None


class HttpError(RuntimeError):
    """A request answered with an error status, or not at all."""

    def __init__(self, status: int, body: str = "") -> None:
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:300]}")


@runtime_checkable
class HttpClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        body: Body = None,
        headers: Mapping[str, str] | None = None,
    ) -> Body:
        """Send ``body`` as JSON and return the parsed reply, None when empty."""
        ...

    def lines(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> Iterator[str]:
        """Each line of a long-lived response, as it arrives."""
        ...


class UrllibClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        *,
        body: Body = None,
        headers: Mapping[str, str] | None = None,
    ) -> Body:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            url,
            method=method,
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                text = response.read().decode()
        except urllib.error.HTTPError as error:
            raise HttpError(
                error.code, error.read().decode(errors="replace")
            ) from error
        except urllib.error.URLError as error:
            raise HttpError(0, str(error.reason)) from error
        return json.loads(text) if text.strip() else None

    def lines(
        self, url: str, *, headers: Mapping[str, str] | None = None
    ) -> Iterator[str]:
        request = urllib.request.Request(url, headers=dict(headers or {}))
        try:
            # No read timeout: an event stream is quiet for as long as nothing
            # happens, and its heartbeats are the server's business.
            with urllib.request.urlopen(request) as response:
                for raw in response:
                    yield raw.decode().rstrip("\r\n")
        except urllib.error.HTTPError as error:
            raise HttpError(
                error.code, error.read().decode(errors="replace")
            ) from error
        except urllib.error.URLError as error:
            raise HttpError(0, str(error.reason)) from error


@dataclass
class FakeHttpClient:
    replies: dict[tuple[str, str], Body] = field(default_factory=dict)
    streams: dict[str, list[str]] = field(default_factory=dict)
    requests: list[tuple[str, str, Body]] = field(default_factory=list)

    def request(
        self,
        method: str,
        url: str,
        *,
        body: Body = None,
        headers: Mapping[str, str] | None = None,  # noqa: ARG002
    ) -> Body:
        self.requests.append((method, url, body))
        if (method, url) not in self.replies:
            raise HttpError(404, f"no canned reply for {method} {url}")
        reply = self.replies[(method, url)]
        if isinstance(reply, HttpError):
            raise reply
        return reply

    def lines(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,  # noqa: ARG002
    ) -> Iterator[str]:
        if url not in self.streams:
            raise HttpError(404, f"no canned stream for {url}")
        yield from self.streams[url]
