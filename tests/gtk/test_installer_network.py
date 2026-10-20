"""The installer's Connect to the internet step."""

from __future__ import annotations

from dataclasses import dataclass, field

from gi.repository import Adw, Gtk
from network_page import NetworkPage

from osiris.model.wifi import WifiNetwork

from .conftest import find, now, shown, widgets

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


def row(page: NetworkPage, ssid: str) -> Adw.ActionRow:
    return next(
        w
        for w in widgets(page)
        if isinstance(w, Adw.ActionRow) and w.get_title() == ssid
    )


def password(page: NetworkPage) -> Adw.PasswordEntryRow:
    found = find(page, Adw.PasswordEntryRow)
    assert isinstance(found, Adw.PasswordEntryRow)
    return found


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


def test_a_secured_network_asks_for_its_password_then_joins() -> None:
    network = FakeNetwork(heard=[HOME])
    page, _ = a_page(network)
    assert not password(page).get_visible()
    row(page, "Home").emit("activated")
    assert password(page).get_visible()
    assert password(page).get_title() == "Password for Home"
    password(page).set_text("hunter22")
    find(page, Gtk.Button, "Join").emit("clicked")
    assert network.joined == [("Home", "hunter22")]
    assert find(page, Gtk.Button, "Continue").get_sensitive()


def test_an_open_network_is_joined_as_soon_as_it_is_chosen() -> None:
    network = FakeNetwork(heard=[CAFE])
    page, _ = a_page(network)
    row(page, "Cafe").emit("activated")
    assert network.joined == [("Cafe", "")]
    assert not password(page).get_visible()
