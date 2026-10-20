"""Whether the install can reach Arch's mirrors, and joining a network if not."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from osiris.model.wifi import WifiNetwork
from osiris.platform import FakeHttpClient, FakeRunner, HttpError
from osiris.platform.process import Result
from osiris.provision.network import JoinFailed, Network, mirror_url, reachable

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


@dataclass
class ReadsPasswordFiles(FakeRunner):
    """Records what each passwd-file held at the moment nmcli was given it."""

    password_files: list[str] = field(default_factory=list)

    def run(self, *argv: str, check: bool = True, quiet: bool = False) -> Result:
        if "passwd-file" in argv:
            path = Path(argv[argv.index("passwd-file") + 1])
            self.password_files.append(path.read_text())
        return super().run(*argv, check=check, quiet=quiet)


class TestJoining:
    def test_an_open_network_is_joined_by_name(self, tmp_path: Path) -> None:
        runner = FakeRunner()
        a_network(runner, tmp_path).join(WifiNetwork("Cafe", 50, ""))
        assert runner.commands == ["nmcli device wifi connect Cafe"]

    @pytest.mark.parametrize(
        ("security", "key_mgmt"), [("WPA1 WPA2", "wpa-psk"), ("WPA3", "sae")]
    )
    def test_a_secured_network_gets_its_password_from_a_file_never_argv(
        self, tmp_path: Path, security: str, key_mgmt: str
    ) -> None:
        runner = ReadsPasswordFiles()
        network = a_network(runner, tmp_path)
        network.join(WifiNetwork("Home", 70, security), "hunter22")
        secret = tmp_path / "wifi-password"
        assert runner.commands == [
            "nmcli connection delete id Home",
            f"nmcli connection add type wifi con-name Home ssid Home "
            f"wifi-sec.key-mgmt {key_mgmt}",
            f"nmcli connection up id Home passwd-file {secret}",
        ]
        assert runner.password_files == ["802-11-wireless-security.psk:hunter22\n"]
        assert not any("hunter22" in command for command in runner.commands)
        assert not secret.exists()

    def test_a_refused_password_is_said_plainly_and_leaves_no_profile(
        self, tmp_path: Path
    ) -> None:
        secret = tmp_path / "wifi-password"
        up = f"nmcli connection up id Home passwd-file {secret}"
        runner = FakeRunner(results={up: Result(("nmcli",), 4)})
        with pytest.raises(JoinFailed) as caught:
            a_network(runner, tmp_path).join(WifiNetwork("Home", 70, "WPA2"), "nope")
        assert str(caught.value) == (
            "Osiris could not join Home. Check the password and try again."
        )
        assert runner.commands[-1] == "nmcli connection delete id Home"
        assert not secret.exists()

    def test_an_open_network_that_will_not_join_says_so(self, tmp_path: Path) -> None:
        runner = FakeRunner(results={"nmcli": Result(("nmcli",), 4)})
        with pytest.raises(JoinFailed, match="could not join Cafe"):
            a_network(runner, tmp_path).join(WifiNetwork("Cafe", 50, ""))

    def test_an_enterprise_network_is_refused_before_anything_runs(
        self, tmp_path: Path
    ) -> None:
        runner = FakeRunner()
        with pytest.raises(JoinFailed, match="network cable"):
            a_network(runner, tmp_path).join(WifiNetwork("Work", 70, "WPA2 802.1X"))
        assert runner.calls == []
