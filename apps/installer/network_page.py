"""The installer's Connect to the internet step.

Draws what osiris.provision.network decides; nothing here knows nmcli.
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

INTRO = ("Osiris downloads most of the system while it installs, so it needs "
         "an internet connection. Plug in a network cable, or join a Wi-Fi "
         "network below.")


class NetworkPage(Adw.NavigationPage):
    """Shown while the medium is offline; Continue waits for a connection.

    `background(work, done)` runs work off the main loop and hands its
    result to done on it.
    """

    def __init__(self, network, on_online, background, poll_seconds=5):
        super().__init__(title="Connect", tag="network")
        self.network = network
        self.on_online = on_online
        self.background = background
        self.rows = []

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for side in ("top", "bottom"):
            getattr(box, f"set_margin_{side}")(24)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_size_request(560, -1)

        intro = Gtk.Label(label=INTRO, xalign=0, wrap=True)
        box.append(intro)

        self.wifi_group = Adw.PreferencesGroup(title="Wi-Fi")
        box.append(self.wifi_group)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(box)
        toolbar.set_content(scroller)
        self.set_child(toolbar)

        self.refresh()

    def refresh(self) -> None:
        """Ask again whether the medium is online, and what Wi-Fi is near."""
        self.background(
            lambda: (self.network.online(), self.network.wifi()), self.show)

    def show(self, found) -> None:
        _online, networks = found
        for row in self.rows:
            self.wifi_group.remove(row)
        self.rows = []
        for network in networks:
            row = Adw.ActionRow(title=network.ssid, subtitle=network.summary)
            row.add_prefix(Gtk.Image(icon_name=network.icon))
            self.wifi_group.add(row)
            self.rows.append(row)
