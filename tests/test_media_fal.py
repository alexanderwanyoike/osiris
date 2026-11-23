"""FAL as the media Provider: one picture from a description."""

from __future__ import annotations

import base64

import pytest

from osiris.harness.media.error import MediaError
from osiris.harness.media.fal import ENDPOINT, FalImages
from osiris.platform import FakeHttpClient, HttpError

PICTURE = b"a picture"
KEY = "a-secret-key"


def answer(picture: bytes = PICTURE) -> dict[str, object]:
    encoded = base64.b64encode(picture).decode()
    return {
        "images": [{"url": f"data:image/png;base64,{encoded}"}],
        "has_nsfw_concepts": [False],
    }


def test_a_description_comes_back_as_the_picture_fal_made() -> None:
    http = FakeHttpClient(replies={("POST", ENDPOINT): answer()})

    picture = FalImages(http, "a-key").make("A misty forest at dawn")

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
        FalImages(http, KEY).make("A misty forest")

    assert KEY not in str(caught.value)
    assert caught.value.__suppress_context__
