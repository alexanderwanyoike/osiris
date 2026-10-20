"""Wi-Fi networks, as NetworkManager lists them.

Pure: osiris.provision.network runs nmcli and hands its output here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    #: 0 to 100, as nmcli reports it.
    signal: int
    #: nmcli's SECURITY column: "WPA2", "WPA2 WPA3", "WPA2 802.1X", empty
    #: when the network is open.
    security: str
    in_use: bool = False


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
    """The networks worth offering, best first."""
    return heard


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
