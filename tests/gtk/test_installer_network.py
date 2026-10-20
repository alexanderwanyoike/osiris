"""The installer's Connect to the internet step."""

from __future__ import annotations

from dataclasses import dataclass, field

from gi.repository import Gtk
from network_page import NetworkPage

from osiris.model.wifi import WifiNetwork

from .conftest import find, now, shown

HOME = WifiNetwork("Home", 80, "WPA2")
CAFE = WifiNetwork("Cafe", 40, "")


@dataclass
class FakeNetwork:
    connected: bool = False
    heard: list[WifiNetwork] = field(default_factory=list)
    joined: list[tuple[str, str]] = field(default_factory=list)

    def online(self) -> bool:
        return self.connected

    def wifi(self) -> list[WifiNetwork]:
        return self.heard

    def join(self, network: WifiNetwork, password: str = "") -> None:
        self.joined.append((network.ssid, password))
        self.connected = True


def a_page(network: FakeNetwork) -> tuple[NetworkPage, list[str]]:
    continued: list[str] = []
    page = NetworkPage(
        network,
        on_online=lambda: continued.append("on"),
        background=now,
        poll_seconds=0,
    )
    return page, continued


def test_the_step_says_why_and_lists_the_networks_in_range() -> None:
    page, _ = a_page(FakeNetwork(heard=[HOME, CAFE]))
    seen = shown(page)
    assert any("downloads most of the system" in text for text in seen)
    assert "Home" in seen
    assert HOME.summary in seen
    assert "Cafe" in seen


def test_continue_waits_for_a_connection_that_check_again_finds() -> None:
    network = FakeNetwork()
    page, continued = a_page(network)
    go = find(page, Gtk.Button, "Continue")
    assert not go.get_sensitive()
    assert "Not connected" in shown(page)
    network.connected = True  # a cable, plugged in
    find(page, Gtk.Button, "Check again").emit("clicked")
    assert go.get_sensitive()
    assert "Connected to the internet" in shown(page)
    go.emit("clicked")
    assert continued == ["on"]
