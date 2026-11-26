"""The HTTP port: JSON requests and line streams, against a loopback server."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from osiris.platform import FakeHttpClient, HttpError, UrllibClient

PICTURE = b"\x89PNG a picture"


class Handler(BaseHTTPRequestHandler):
    """Echoes what it was sent, and serves the fixed routes the tests use."""

    redirect_to = ""

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
        if self.path == "/missing":
            self._reply(404, {"message": "no such thing"})
            return
        if self.path == "/moved":
            self.send_response(302)
            self.send_header("Location", self.redirect_to)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/dropped":
            self.close_connection = True
            return
        if self.path == "/short":
            self.send_response(200)
            self.send_header("Content-Length", "10")
            self.end_headers()
            self.wfile.write(b"{}")
            self.close_connection = True
            return
        if self.path == "/slow":
            time.sleep(0.6)
            return
        if self.path == "/cut-off-error":
            self.send_response(500)
            self.send_header("Content-Length", "10")
            self.end_headers()
            self.wfile.write(b"{}")
            self.close_connection = True
            return
        if self.path == "/picture":
            self.send_response(200)
            self.send_header("Content-Length", str(len(PICTURE)))
            self.end_headers()
            self.wfile.write(PICTURE)
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
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
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

    @pytest.mark.parametrize("path", ["/dropped", "/short", "/slow"])
    def test_a_connection_lost_midway_is_no_answer(
        self, server: str, path: str
    ) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient(timeout=0.2).request("GET", f"{server}{path}")
        assert raised.value.status == 0

    def test_an_error_whose_body_is_cut_off_keeps_its_status(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().request("GET", f"{server}/cut-off-error")
        assert raised.value.status == 500

    def test_a_redirect_to_another_host_does_not_carry_the_credentials(
        self, server: str
    ) -> None:
        port = server.rsplit(":", 1)[1]
        Handler.redirect_to = f"http://localhost:{port}/"

        reply = UrllibClient().request(
            "GET", f"{server}/moved", headers={"Authorization": "Key secret"}
        )

        assert reply == {"auth": None}

    def test_a_redirect_on_the_same_host_keeps_the_credentials(
        self, server: str
    ) -> None:
        Handler.redirect_to = f"{server}/"

        reply = UrllibClient().request(
            "GET", f"{server}/moved", headers={"Authorization": "Key secret"}
        )

        assert reply == {"auth": "Key secret"}

    def test_a_redirected_stream_does_not_carry_the_credentials(
        self, server: str
    ) -> None:
        port = server.rsplit(":", 1)[1]
        Handler.redirect_to = f"http://localhost:{port}/"

        lines = UrllibClient().lines(
            f"{server}/moved", headers={"Authorization": "Key secret"}
        )

        assert "secret" not in "".join(lines)

    def test_a_download_comes_back_as_bytes(self, server: str) -> None:
        assert UrllibClient().download(f"{server}/picture", limit=100) == PICTURE

    def test_a_download_over_its_limit_is_refused(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().download(f"{server}/picture", limit=4)
        assert raised.value.status == 0

    def test_a_download_does_not_follow_a_redirect(self, server: str) -> None:
        Handler.redirect_to = f"{server}/picture"

        with pytest.raises(HttpError) as raised:
            UrllibClient().download(f"{server}/moved", limit=100)

        assert raised.value.status == 302

    def test_a_download_cut_off_midway_is_refused(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().download(f"{server}/short", limit=100)

        assert raised.value.status == 0

    def test_a_download_keeps_the_status_it_failed_with(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().download(f"{server}/missing", limit=100)

        assert raised.value.status == 404

    def test_a_link_that_is_not_a_valid_address_is_no_answer(self, server: str) -> None:
        with pytest.raises(HttpError) as raised:
            UrllibClient().download(f"{server}/pict\u00fcre", limit=100)

        assert raised.value.status == 0

    def test_a_stream_arrives_line_by_line(self, server: str) -> None:
        lines = list(UrllibClient().lines(f"{server}/events"))
        assert [line for line in lines if line] == [
            "data: one",
            ": heartbeat",
            "data: two",
        ]


class TestFakeHttpClient:
    def test_downloads_are_served_from_what_it_was_given(self) -> None:
        client = FakeHttpClient(downloads={"http://x/p": PICTURE})
        assert client.download("http://x/p", limit=100) == PICTURE

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
