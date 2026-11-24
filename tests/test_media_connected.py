"""FAL as the tool server reaches it: through the saved key and the daily limit."""

from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from osiris.harness.media.connected import USAGE_FILE, ConnectedFal
from osiris.harness.media.error import MediaError
from osiris.harness.media.fal import RUN, FalImages
from osiris.harness.media.key import save_fal_key
from osiris.harness.media.limit_setting import set_daily_limit
from osiris.harness.media.model_setting import DEFAULT_IMAGE_MODEL, save_model
from osiris.harness.media.model_spec import ModelSpec
from osiris.platform import FakeFileSystem, FakeHttpClient, HttpError

HOME = Path("/home/tester")
MONDAY = date(2026, 11, 23)
ENDPOINT = f"{RUN}/{DEFAULT_IMAGE_MODEL}"
ANSWER = {
    "images": [{"url": "data:image/png;base64," + base64.b64encode(b"p").decode()}],
    "has_nsfw_concepts": [False],
}


def any_model(model: str) -> ModelSpec:
    return ModelSpec(model, frozenset({"prompt"}))


def connected(
    files: FakeFileSystem,
    http: FakeHttpClient,
    spec: Callable[[str], ModelSpec] = any_model,
) -> ConnectedFal:
    return ConnectedFal(
        files,
        HOME,
        lambda key, before: FalImages(http, key, spec, before),
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


def test_a_named_model_is_the_one_asked() -> None:
    files = FakeFileSystem()
    named = f"{RUN}/vendor/named"
    http = FakeHttpClient(replies={("POST", named): ANSWER})
    save_fal_key(files, HOME, "a-key")

    assert connected(files, http).make("A forest", "vendor/named") == b"p"

    assert http.requests[0][1] == named


def test_the_persons_default_model_is_used_when_none_is_named() -> None:
    files = FakeFileSystem()
    saved = f"{RUN}/vendor/saved"
    http = FakeHttpClient(replies={("POST", saved): ANSWER})
    save_fal_key(files, HOME, "a-key")
    save_model(files, HOME, "vendor/saved")

    connected(files, http).make("A forest")

    assert http.requests[0][1] == saved


def test_a_model_named_for_one_picture_beats_the_default() -> None:
    files = FakeFileSystem()
    named = f"{RUN}/vendor/named"
    http = FakeHttpClient(replies={("POST", named): ANSWER})
    save_fal_key(files, HOME, "a-key")
    save_model(files, HOME, "vendor/saved")

    connected(files, http).make("A forest", "vendor/named")

    assert http.requests[0][1] == named


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


def test_a_refused_model_does_not_use_up_a_daily_picture() -> None:
    def spec(model: str) -> ModelSpec:
        if model == "vendor/refused":
            raise MediaError("vendor/refused is not an image model FAL offers")
        return any_model(model)

    files = FakeFileSystem()
    http = FakeHttpClient(replies={("POST", ENDPOINT): ANSWER})
    save_fal_key(files, HOME, "a-key")
    set_daily_limit(files, HOME, 1)
    fal = connected(files, http, spec)

    with pytest.raises(MediaError, match="not an image model"):
        fal.make("One", "vendor/refused")

    assert fal.make("Two") == b"p"


def test_a_failed_request_still_counts_because_it_may_have_been_billed() -> None:
    files = FakeFileSystem()
    http = FakeHttpClient(replies={("POST", ENDPOINT): HttpError(500, "no")})
    save_fal_key(files, HOME, "a-key")
    set_daily_limit(files, HOME, 1)
    fal = connected(files, http)

    with pytest.raises(MediaError, match="could not make"):
        fal.make("One")
    with pytest.raises(MediaError, match="limit of 1"):
        fal.make("Two")

    assert len(http.requests) == 1
