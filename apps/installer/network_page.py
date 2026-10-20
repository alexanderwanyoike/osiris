"""The installer's Connect to the internet step.

Draws what osiris.provision.network decides; nothing here knows nmcli.
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402


class NetworkPage(Adw.NavigationPage):
    def __init__(self, network, on_online, background, poll_seconds=5):
        super().__init__(title="Connect", tag="network")
