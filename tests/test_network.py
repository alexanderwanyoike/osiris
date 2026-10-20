"""Whether the install can reach Arch's mirrors, and joining a network if not."""

from __future__ import annotations

from pathlib import Path

import pytest

from osiris.model.wifi import WifiNetwork
from osiris.platform import FakeHttpClient, FakeRunner, HttpError
from osiris.platform.process import Result
from osiris.provision.network import Network, mirror_url, reachable

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


class TestOnline:
    def test_the_check_asks_the_first_mirror_in_the_medium_s_mirrorlist(
        self, tmp_path: Path
    ) -> None:
        mirrorlist = tmp_path / "mirrorlist"
        mirrorlist.write_text(MIRRORLIST)
        http = FakeHttpClient(replies={("HEAD", URL): None})
        network = Network.for_this_machine(FakeRunner(), http, mirrorlist)
        assert network.online()
        assert http.requests == [("HEAD", URL, None)]


SCAN = "nmcli -t -f IN-USE,SIGNAL,SECURITY,SSID device wifi list --rescan yes"


def a_network(runner: FakeRunner, tmp_path: Path) -> Network:
    return Network(runner, FakeHttpClient(), URL, secrets=tmp_path)


class TestWifi:
    def test_networks_are_listed_from_a_fresh_scan_best_first(
        self, tmp_path: Path
    ) -> None:
        heard = " :40:WPA2:Office\n*:70:WPA2:Home\n :20:WPA2:Home\n"
        runner = FakeRunner(results={SCAN: Result(("nmcli",), 0, heard)})
        assert a_network(runner, tmp_path).wifi() == [
            WifiNetwork("Home", 70, "WPA2", in_use=True),
            WifiNetwork("Office", 40, "WPA2"),
        ]

    def test_a_machine_without_wifi_lists_none(self, tmp_path: Path) -> None:
        runner = FakeRunner(results={SCAN: Result(("nmcli",), 10, "")})
        assert a_network(runner, tmp_path).wifi() == []


class TestJoining:
    def test_an_open_network_is_joined_by_name(self, tmp_path: Path) -> None:
        runner = FakeRunner()
        a_network(runner, tmp_path).join(WifiNetwork("Cafe", 50, ""))
        assert runner.commands == ["nmcli device wifi connect Cafe"]
