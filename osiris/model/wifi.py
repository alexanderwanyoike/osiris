"""Wi-Fi networks, as NetworkManager lists them.

Pure: osiris.provision.network runs nmcli and hands its output here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Security(StrEnum):
    OPEN = "open"
    WPA_PSK = "wpa-psk"
    SAE = "sae"
    UNSUPPORTED = "unsupported"


_SECURITY_WORDS = {
    Security.OPEN: "open",
    Security.WPA_PSK: "secured",
    Security.SAE: "secured",
    Security.UNSUPPORTED: "enterprise or WEP, which the installer cannot join",
}

_SIGNAL_ICONS = ((75, "excellent"), (50, "good"), (25, "ok"), (0, "weak"))


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    #: 0 to 100, as nmcli reports it.
    signal: int
    #: nmcli's SECURITY column: "WPA2", "WPA2 WPA3", "WPA2 802.1X", empty
    #: when the network is open.
    security: str
    in_use: bool = False

    @property
    def how(self) -> Security:
        """How the installer joins it.

        A WPA2/WPA3 transition network takes wpa-psk, which every client
        that can join it supports.
        """
        words = set(self.security.split())
        if words & {"802.1X", "WEP"}:
            return Security.UNSUPPORTED
        if words & {"WPA1", "WPA2"}:
            return Security.WPA_PSK
        if "WPA3" in words:
            return Security.SAE
        return Security.OPEN

    @property
    def asks_password(self) -> bool:
        return False

    @property
    def summary(self) -> str:
        words = ["Connected"] if self.in_use else []
        words.append(_SECURITY_WORDS[self.how])
        words.append(f"signal {self.signal}%")
        sentence = ", ".join(words)
        return sentence[0].upper() + sentence[1:]

    @property
    def icon(self) -> str:
        strength = next(name for floor, name in _SIGNAL_ICONS if self.signal >= floor)
        return f"network-wireless-signal-{strength}-symbolic"


def parse(terse: str) -> list[WifiNetwork]:
    """`nmcli -t -f IN-USE,SIGNAL,SECURITY,SSID device wifi list` output."""
    found = []
    for line in terse.splitlines():
        fields = _fields(line)
        if len(fields) < 4:
            continue
        in_use, signal, security, ssid = fields[:4]
        found.append(
            WifiNetwork(
                ssid=ssid,
                signal=int(signal) if signal.isdigit() else 0,
                security=security.strip(),
                in_use=in_use.strip() == "*",
            )
        )
    return found


def choices(heard: list[WifiNetwork]) -> list[WifiNetwork]:
    """The networks worth offering, best first.

    One per name: nmcli lists each access point, and a mesh is several. The
    one kept is the joined one if any, else the strongest. Hidden networks
    have no name to offer.
    """
    best: dict[str, WifiNetwork] = {}
    for network in heard:
        if not network.ssid:
            continue
        kept = best.get(network.ssid)
        if kept is None or _rank(network) > _rank(kept):
            best[network.ssid] = network
    return sorted(best.values(), key=_rank, reverse=True)


def _rank(network: WifiNetwork) -> tuple[bool, int]:
    return network.in_use, network.signal


def _fields(line: str) -> list[str]:
    """One terse line split on unescaped ':', with the escapes removed."""
    fields, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields
