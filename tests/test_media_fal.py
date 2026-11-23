"""FAL as the media Provider: one picture from a description."""

from __future__ import annotations

import base64

from osiris.harness.media.fal import ENDPOINT, FalImages
from osiris.platform import FakeHttpClient

PICTURE = b"a picture"


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
