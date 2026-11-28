"""The HTTP port: JSON requests and line streams, against a loopback server."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from osiris.platform import FakeHttpClient, HttpError, UrllibClient

# Holds /silent's reply back until the test is over, however slow the machine.
RELEASE = threading.Event()


class Handler(BaseHTTPRequestHandler):
    """Echoes what it was sent, and serves the fixed routes the tests use."""

    def log_message(self, *_args: object) -> None:
        pass

    def _reply(self, status: int, payload: object | None = None) -> None:
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b"data: one\n\n: heartbeat\n\ndata: two\n\n")
            return
        if self.path == "/events-cut":
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(b"b\r\ndata: one\n\r\n")
            return
        if self.path == "/silent":
            RELEASE.wait()
            return
        if self.path == "/hangup":
            return
        if self.path == "/cut":
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b'{"cut')
            return
        if self.path == "/missing-cut":
            self.send_response(404)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b'{"no')
            return
        if self.path == "/missing":
            self._reply(404, {"message": "no such thing"})
            return
        self._reply(200, {"auth": self.headers.get("Authorization")})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        sent = json.loads(self.rfile.read(length)) if length else None
        if self.path == "/empty":
            self._reply(204)
            return
        self._reply(200, {"sent": sent})


@pytest.fixture
def server() -> Iterator[str]:
    RELEASE.clear()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    RELEASE.set()
    httpd.shutdown()
    httpd.server_close()


class TestUrllibClient:
    def test_a_json_body_goes_out_and_the_reply_comes_back_parsed(
        self, server: str
    ) -> None:
        reply = UrllibClient().request("POST", f"{server}/echo", body={"text": "hi"})
        assert reply == {"sent": {"text": "hi"}}

    def test_headers_are_sent(self, server: str) -> None:
        reply = UrllibClient().request(
            "GET", f"{server}/", headers={"Authorization": "Basic abc"}
        )
        assert reply == {"auth": "Basic abc"}

    def test_no_content_is_none(self, server: str) -> None:
        assert UrllibClient().request("POST", f"{server}/empty", body={}) is None

    def test_an_error_status_raises_with_the_status_and_body(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().request("GET", f"{server}/missing")
        assert raised.value.status == 404
        assert "no such thing" in raised.value.body

    def test_an_error_status_with_its_body_cut_short_keeps_the_status(
        self, server: str
    ) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().request("GET", f"{server}/missing-cut")
        assert raised.value.status == 404

    @pytest.mark.parametrize("path", ["/silent", "/hangup"])
    def test_no_answer_once_connected_is_status_0(self, server: str, path: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient(timeout=0.1).request("GET", f"{server}{path}")
        assert raised.value.status == 0

    def test_a_reply_cut_short_is_status_0(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().request("GET", f"{server}/cut")
        assert raised.value.status == 0

    def test_a_stream_arrives_line_by_line(self, server: str) -> None:
        lines = list(UrllibClient().lines(f"{server}/events"))
        assert [line for line in lines if line] == [
            "data: one",
            ": heartbeat",
            "data: two",
        ]

    def test_a_stream_cut_short_is_status_0(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            list(UrllibClient().lines(f"{server}/events-cut"))
        assert raised.value.status == 0


class TestFakeHttpClient:
    def test_replies_are_served_and_requests_recorded(self) -> None:
        client = FakeHttpClient(replies={("POST", "http://x/a"): {"ok": True}})
        assert client.request("POST", "http://x/a", body={"n": 1}) == {"ok": True}
        assert client.requests == [("POST", "http://x/a", {"n": 1})]

    def test_an_unknown_request_is_an_error_not_a_silent_none(self) -> None:
        with pytest.raises(HttpError) as raised:
            FakeHttpClient().request("GET", "http://x/nowhere")
        assert raised.value.status == 404

    def test_streams_replay_their_lines(self) -> None:
        client = FakeHttpClient(streams={"http://x/events": ["data: a", ""]})
        assert list(client.lines("http://x/events")) == ["data: a", ""]
