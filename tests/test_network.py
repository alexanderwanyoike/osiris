"""Whether the install can reach Arch's mirrors, and joining a network if not."""

from __future__ import annotations

import pytest

from osiris.platform import FakeHttpClient, HttpError
from osiris.provision.network import mirror_url, reachable

MIRRORLIST = """\
##
## Arch Linux repository mirrorlist
##

## Worldwide
#Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch
Server = https://fastly.mirror.pkgbuild.com/$repo/os/$arch
Server = https://mirror.example.org/archlinux/$repo/os/$arch
"""


URL = "https://fastly.mirror.pkgbuild.com/core/os/x86_64/core.db"


class TestWhereTheCheckLooks:
    def test_the_first_mirror_the_install_will_use_is_asked_for_its_core_database(
        self,
    ) -> None:
        assert mirror_url(MIRRORLIST) == (
            "https://fastly.mirror.pkgbuild.com/core/os/x86_64/core.db"
        )

    def test_with_no_mirror_listed_it_asks_archlinux_org(self) -> None:
        assert mirror_url("#Server = https://x.org/$repo/os/$arch\n") == (
            "https://archlinux.org/"
        )


class TestWhetherItIsReachable:
    @pytest.mark.parametrize(
        ("reply", "online"),
        [
            (None, True),
            (HttpError(503, "busy"), True),
            (HttpError(0, "unreachable"), False),
        ],
        ids=["answered", "answered with an error", "no answer"],
    )
    def test_online_means_the_mirror_answered_at_all(
        self, reply: object, online: bool
    ) -> None:
        http = FakeHttpClient(replies={("HEAD", URL): reply})
        assert reachable(http, URL) is online
        assert http.requests == [("HEAD", URL, None)]
