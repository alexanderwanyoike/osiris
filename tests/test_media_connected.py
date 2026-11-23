"""FAL as the tool server reaches it: through the saved key and the daily limit."""

from __future__ import annotations

import base64
from datetime import date
from pathlib import Path

import pytest

from osiris.harness.media.connected import USAGE_FILE, ConnectedFal
from osiris.harness.media.error import MediaError
from osiris.harness.media.fal import DEFAULT_MODEL, RUN, FalImages
from osiris.harness.media.key import save_fal_key
from osiris.harness.media.limit_setting import set_daily_limit
from osiris.platform import FakeFileSystem, FakeHttpClient

HOME = Path("/home/tester")
MONDAY = date(2026, 11, 23)
ENDPOINT = f"{RUN}/{DEFAULT_MODEL}"
ANSWER = {
    "images": [{"url": "data:image/png;base64," + base64.b64encode(b"p").decode()}],
    "has_nsfw_concepts": [False],
}


def connected(files: FakeFileSystem, http: FakeHttpClient) -> ConnectedFal:
    return ConnectedFal(
        files,
        HOME,
        lambda key: FalImages(http, key, lambda _model: frozenset({"prompt"})),
        lambda: MONDAY,
    )


def test_without_a_key_nothing_is_sent_or_counted() -> None:
    files, http = FakeFileSystem(), FakeHttpClient()

    with pytest.raises(MediaError, match="Settings"):
        connected(files, http).make("A forest")

    assert http.requests == []
    assert not files.exists(HOME / USAGE_FILE)


def test_with_a_key_and_no_limit_a_picture_is_made_and_nothing_is_counted() -> None:
    files = FakeFileSystem()
    http = FakeHttpClient(replies={("POST", ENDPOINT): ANSWER})
    save_fal_key(files, HOME, "a-key")

    assert connected(files, http).make("A forest") == b"p"

    assert not files.exists(HOME / USAGE_FILE)


def test_a_limit_the_person_set_is_counted_and_holds() -> None:
    files = FakeFileSystem()
    http = FakeHttpClient(replies={("POST", ENDPOINT): ANSWER})
    save_fal_key(files, HOME, "a-key")
    set_daily_limit(files, HOME, 1)
    fal = connected(files, http)

    fal.make("One")
    with pytest.raises(MediaError, match="limit of 1"):
        fal.make("Two")

    assert files.read(HOME / USAGE_FILE) == "2026-11-23\n"
    assert len(http.requests) == 1
