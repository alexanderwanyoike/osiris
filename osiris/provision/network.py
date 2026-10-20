"""Whether the install can reach Arch's mirrors, and joining a network if not."""

from __future__ import annotations

from pathlib import Path

from osiris.model.wifi import WifiNetwork, choices, parse
from osiris.platform.http import HttpClient, HttpError
from osiris.platform.process import CommandError, CommandRunner

#: nmcli's format for programs; see osiris.model.wifi.parse.
SCAN = (
    "nmcli", "-t", "-f", "IN-USE,SIGNAL,SECURITY,SSID",
    "device", "wifi", "list", "--rescan", "yes",
)  # fmt: skip

#: Where a Wi-Fi password is written for nmcli to read, and deleted after.
SECRETS = Path("/root/osiris-install")

#: Asked when the medium's mirrorlist names no server at all.
FALLBACK = "https://archlinux.org/"


def mirror_url(mirrorlist: str) -> str:
    """Where to ask whether the install's downloads will work.

    The first server in the medium's mirrorlist, which is the one pacman
    tries first: Osiris sets no mirror regions, so archinstall leaves that
    file as it is. Its core database is small and always there.
    """
    for line in mirrorlist.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "Server" and value.strip():
            base = value.strip().replace("$repo", "core").replace("$arch", "x86_64")
            return f"{base.rstrip('/')}/core.db"
    return FALLBACK


def reachable(http: HttpClient, url: str) -> bool:
    """Whether anything at url answers.

    Any status counts: a mirror that answers 503 is still proof the network
    works. HttpError's status 0 is the adapter's "no answer at all".
    """
    try:
        http.request("HEAD", url)
    except HttpError as error:
        return error.status != 0
    return True


class Network:
    """The live medium's connection: whether it is online, and joining Wi-Fi."""

    def __init__(
        self,
        runner: CommandRunner,
        http: HttpClient,
        url: str,
        secrets: Path = SECRETS,
    ) -> None:
        self._runner = runner
        self._http = http
        self._url = url
        self._secrets = secrets

    def wifi(self) -> list[WifiNetwork]:
        """The Wi-Fi networks in range, best first; none without a Wi-Fi device."""
        try:
            heard = self._runner.capture(*SCAN)
        except CommandError:
            return []
        return choices(parse(heard))
