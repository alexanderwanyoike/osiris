"""FAL as the Media provider: one picture from a description."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping

import pytest

from osiris.harness.media.error import MediaError
from osiris.harness.media.fal import RUN, FalImages
from osiris.harness.media.model_setting import DEFAULT_IMAGE_MODEL
from osiris.harness.media.model_spec import ModelSpec
from osiris.harness.media.wide_size import FULL_HD
from osiris.platform import FakeHttpClient, HttpError
from osiris.platform.http import Body

PICTURE = b"a picture"
KEY = "a-secret-key"
ENDPOINT = f"{RUN}/{DEFAULT_IMAGE_MODEL}"
EVERY_INPUT = frozenset(
    {"prompt", "image_size", "num_images", "output_format", "sync_mode"}
)


def fal(http: FakeHttpClient) -> FalImages:
    return FalImages(http, KEY, lambda model: ModelSpec(model, EVERY_INPUT, FULL_HD))


def answer(picture: bytes = PICTURE) -> dict[str, object]:
    encoded = base64.b64encode(picture).decode()
    return {
        "images": [{"url": f"data:image/png;base64,{encoded}"}],
        "has_nsfw_concepts": [False],
    }


def test_a_description_comes_back_as_the_picture_fal_made() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): answer()})

    picture = fal(http).make("A misty forest at dawn")

    assert picture == PICTURE
    assert http.requests == [
        (
            "POST",
            ENDPOINT,
            {
                "prompt": "A misty forest at dawn",
                "image_size": {"width": 1920, "height": 1080},
                "num_images": 1,
                "output_format": "png",
                "sync_mode": True,
            },
        )
    ]


def test_a_named_model_is_the_one_asked() -> None:
    named = f"{RUN}/vendor/another-model"
    http = FakeHttpClient(replies={("POST", named): answer()})

    assert fal(http).make("A forest", "vendor/another-model") == PICTURE

    assert http.requests[0][1] == named


def test_only_the_inputs_a_model_accepts_are_sent() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): answer()})
    accepted = frozenset({"prompt", "image_size"})

    FalImages(http, KEY, lambda model: ModelSpec(model, accepted, FULL_HD)).make(
        "A forest"
    )

    assert http.requests[0][2] == {
        "prompt": "A forest",
        "image_size": {"width": 1920, "height": 1080},
    }


def test_a_model_is_sent_the_size_its_schema_allows() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): answer()})
    accepted = frozenset({"prompt", "image_size"})

    FalImages(
        http, KEY, lambda model: ModelSpec(model, accepted, "landscape_16_9")
    ).make("A forest")

    assert http.requests[0][2] == {
        "prompt": "A forest",
        "image_size": "landscape_16_9",
    }


def test_a_model_with_no_wide_size_is_left_to_its_own_default() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): answer()})
    accepted = frozenset({"prompt", "image_size"})

    FalImages(http, KEY, lambda model: ModelSpec(model, accepted)).make("A forest")

    assert http.requests[0][2] == {"prompt": "A forest"}


def test_a_model_without_a_size_input_is_asked_for_a_wide_picture() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): answer()})
    accepted = frozenset({"prompt", "aspect_ratio"})

    FalImages(http, KEY, lambda model: ModelSpec(model, accepted)).make("A forest")

    assert http.requests[0][2] == {"prompt": "A forest", "aspect_ratio": "16:9"}


def test_a_model_the_catalog_refuses_spends_nothing() -> None:
    def refuse(model: str) -> ModelSpec:
        raise MediaError(f"{model} is not an image model FAL offers")

    http = FakeHttpClient()

    with pytest.raises(MediaError, match="not an image model"):
        FalImages(http, KEY, refuse).make("A forest", "vendor/video")

    assert http.requests == []


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "did not accept the key"),
        (403, "out of credit"),
        (0, "could not reach FAL"),
        (500, "FAL could not make the picture"),
    ],
)
def test_a_failure_is_given_a_plain_reason_without_the_key(
    status: int, reason: str
) -> None:
    refusal = HttpError(status, f"rejected {KEY}")
    http = FakeHttpClient(replies={("POST", ENDPOINT): refusal})

    with pytest.raises(MediaError, match=reason) as caught:
        fal(http).make("A misty forest")

    assert KEY not in str(caught.value)
    assert caught.value.__suppress_context__


def test_no_answer_warns_the_picture_may_still_have_been_charged() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): HttpError(0, "timed out")})

    with pytest.raises(MediaError, match="ask the person before trying again"):
        fal(http).make("A misty forest")


@pytest.mark.parametrize(
    "reply",
    [
        HttpError(500, "no"),
        {},
        {"images": [{"url": "https://v3.fal.media/files/a/picture.png"}]},
    ],
)
def test_a_failure_after_the_request_warns_it_may_have_been_charged(
    reply: object,
) -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): reply})

    with pytest.raises(MediaError, match="ask the person before trying again"):
        fal(http).make("A forest")


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (json.JSONDecodeError("not json", "", 0), "did not return a picture"),
        (UnicodeEncodeError("latin-1", "key", 0, 1, "no"), "did not accept the key"),
    ],
)
def test_a_request_that_breaks_is_given_a_plain_reason(
    failure: Exception, reason: str
) -> None:
    class Broken(FakeHttpClient):
        def request(
            self,
            method: str,
            url: str,
            *,
            body: Body = None,
            headers: Mapping[str, str] | None = None,
        ) -> Body:
            raise failure

    with pytest.raises(MediaError, match=reason) as caught:
        fal(Broken()).make("A misty forest")

    assert caught.value.__suppress_context__


def test_a_picture_the_safety_filter_blocked_is_refused() -> None:
    blocked = {**answer(), "has_nsfw_concepts": [True]}
    http = FakeHttpClient(replies={("POST", ENDPOINT): blocked})

    with pytest.raises(MediaError, match="blocked"):
        fal(http).make("A misty forest")


@pytest.mark.parametrize(
    "link",
    [
        "https://v3.fal.media/files/a/picture.png",
        "https://fal.media/files/a/picture.png",
        "https://storage.googleapis.com/falserverless/a/picture.webp",
    ],
)
def test_a_picture_returned_as_a_link_is_fetched_from_fals_storage(link: str) -> None:
    reply = {"images": [{"url": link}]}
    http = FakeHttpClient(
        replies={("POST", ENDPOINT): reply}, downloads={link: PICTURE}
    )

    assert fal(http).make("A forest") == PICTURE


@pytest.mark.parametrize(
    "link",
    [
        "http://v3.fal.media/files/a/picture.png",
        "https://fal.media.elsewhere.example/picture.png",
        "https://storage.googleapis.com/someone-else/picture.png",
    ],
)
def test_a_link_outside_fals_storage_is_never_fetched(link: str) -> None:
    reply = {"images": [{"url": link}]}
    http = FakeHttpClient(
        replies={("POST", ENDPOINT): reply}, downloads={link: PICTURE}
    )

    with pytest.raises(MediaError, match="did not return a picture"):
        fal(http).make("A forest")


def test_a_picture_that_cannot_be_fetched_is_given_a_plain_reason() -> None:
    link = "https://v3.fal.media/files/a/picture.png"
    http = FakeHttpClient(replies={("POST", ENDPOINT): {"images": [{"url": link}]}})

    with pytest.raises(MediaError, match="could not download"):
        fal(http).make("A forest")


@pytest.mark.parametrize(
    "reply",
    [
        None,
        {},
        {"images": []},
        {"images": [{"url": "https://elsewhere.example/picture.png"}]},
        {"images": [{"url": "data:image/png;base64,not base64!"}]},
    ],
)
def test_an_answer_without_a_picture_is_refused(reply: object) -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): reply})

    with pytest.raises(MediaError, match="did not return a picture"):
        fal(http).make("A misty forest")
