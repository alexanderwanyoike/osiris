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
    return []
