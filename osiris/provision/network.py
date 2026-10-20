"""Whether the install can reach Arch's mirrors, and joining a network if not."""

from __future__ import annotations

from pathlib import Path

from osiris.model.wifi import Security, WifiNetwork, choices, parse
from osiris.platform.http import HttpClient, HttpError
from osiris.platform.process import CommandError, CommandRunner

#: nmcli's format for programs; see osiris.model.wifi.parse.
SCAN = (
    "nmcli", "-t", "-f", "IN-USE,SIGNAL,SECURITY,SSID",
    "device", "wifi", "list", "--rescan", "yes",
)  # fmt: skip

#: Where a Wi-Fi password is written for nmcli to read, and deleted after.
SECRETS = Path("/root/osiris-install")

#: The live medium's mirrorlist, which archinstall installs from.
MIRRORLIST = Path("/etc/pacman.d/mirrorlist")

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


class JoinFailed(RuntimeError):
    """A Wi-Fi network was not joined; the message is for the person."""


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

    @classmethod
    def for_this_machine(
        cls, runner: CommandRunner, http: HttpClient, mirrorlist: Path = MIRRORLIST
    ) -> Network:
        try:
            listed = mirrorlist.read_text()
        except OSError:
            listed = ""
        return cls(runner, http, mirror_url(listed))

    def online(self) -> bool:
        """Whether the install's downloads would work right now."""
        return reachable(self._http, self._url)

    def wifi(self) -> list[WifiNetwork]:
        """The Wi-Fi networks in range, best first; none without a Wi-Fi device."""
        try:
            heard = self._runner.capture(*SCAN)
        except CommandError:
            return []
        return choices(parse(heard))

    def join(self, network: WifiNetwork, password: str = "") -> None:
        """Join a Wi-Fi network; raises JoinFailed saying why it did not."""
        if network.how is Security.OPEN:
            self._runner.run(
                "nmcli", "device", "wifi", "connect", network.ssid, quiet=True
            )  # fmt: skip
            return
        self._join_secured(network, password)

    def _join_secured(self, network: WifiNetwork, password: str) -> None:
        """A profile naming its key management, activated with the password
        read from a file, so it never appears in a process's argv.
        """
        name = network.ssid
        # A profile left by an earlier attempt, or by nm-applet, would make
        # `id <name>` ambiguous.
        self._runner.run(
            "nmcli", "connection", "delete", "id", name, check=False, quiet=True
        )  # fmt: skip
        self._runner.run(
            "nmcli", "connection", "add", "type", "wifi",
            "con-name", name, "ssid", name,
            "wifi-sec.key-mgmt", network.how.value,
            quiet=True,
        )  # fmt: skip
        secret = self._write_secret(f"802-11-wireless-security.psk:{password}\n")
        try:
            self._runner.run(
                "nmcli", "connection", "up", "id", name,
                "passwd-file", str(secret),
                quiet=True,
            )  # fmt: skip
        finally:
            secret.unlink(missing_ok=True)

    def _write_secret(self, text: str) -> Path:
        self._secrets.mkdir(parents=True, exist_ok=True)
        secret = self._secrets / "wifi-password"
        # Readable by root alone before the password goes in.
        secret.touch(mode=0o600)
        secret.chmod(0o600)
        secret.write_text(text)
        return secret
