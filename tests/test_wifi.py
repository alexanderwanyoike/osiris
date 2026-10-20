"""Wi-Fi networks as nmcli lists them, and what the installer shows of them."""

from __future__ import annotations

import pytest

from osiris.model.wifi import Security, WifiNetwork, choices, parse


def test_each_line_of_nmcli_terse_output_is_a_network() -> None:
    # -t -f IN-USE,SIGNAL,SECURITY,SSID: terse mode escapes ':' and '\\'.
    terse = "*:72:WPA2:Home\\:Net\n :40::Cafe\n :18:WPA1 WPA2:back\\\\slash\n"
    assert parse(terse) == [
        WifiNetwork("Home:Net", 72, "WPA2", in_use=True),
        WifiNetwork("Cafe", 40, ""),
        WifiNetwork("back\\slash", 18, "WPA1 WPA2"),
    ]


def test_each_name_is_offered_once_connected_first_then_strongest() -> None:
    heard = [
        WifiNetwork("Cafe", 40, ""),
        WifiNetwork("", 90, "WPA2"),
        WifiNetwork("Home", 30, "WPA2"),
        WifiNetwork("Office", 55, "WPA2"),
        WifiNetwork("Home", 80, "WPA2", in_use=True),
        WifiNetwork("Cafe", 65, ""),
    ]
    assert choices(heard) == [
        WifiNetwork("Home", 80, "WPA2", in_use=True),
        WifiNetwork("Cafe", 65, ""),
        WifiNetwork("Office", 55, "WPA2"),
    ]


@pytest.mark.parametrize(
    ("column", "security"),
    [
        ("", Security.OPEN),
        ("WPA2", Security.WPA_PSK),
        ("WPA1 WPA2", Security.WPA_PSK),
        ("WPA2 WPA3", Security.WPA_PSK),
        ("WPA3", Security.SAE),
        ("WPA2 802.1X", Security.UNSUPPORTED),
        ("WEP", Security.UNSUPPORTED),
    ],
)
def test_how_a_network_is_joined_follows_its_security_column(
    column: str, security: Security
) -> None:
    assert WifiNetwork("x", 50, column).how == security
