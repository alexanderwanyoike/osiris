"""The installer's Connect to the internet step.

Draws what osiris.provision.network decides; nothing here knows nmcli.
"""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from osiris.provision.network import JoinFailed  # noqa: E402

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
        self.chosen = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for side in ("top", "bottom"):
            getattr(box, f"set_margin_{side}")(24)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_size_request(560, -1)

        intro = Gtk.Label(label=INTRO, xalign=0, wrap=True)
        box.append(intro)

        status = Adw.PreferencesGroup()
        self.status = Adw.ActionRow(title="Checking the connection")
        self.status_icon = Gtk.Image(icon_name="network-offline-symbolic")
        self.status.add_prefix(self.status_icon)
        status.add(self.status)
        box.append(status)

        self.wifi_group = Adw.PreferencesGroup(title="Wi-Fi")
        box.append(self.wifi_group)

        secret = Adw.PreferencesGroup()
        self.password = Adw.PasswordEntryRow(visible=False)
        join = Gtk.Button(label="Join", valign=Gtk.Align.CENTER)
        join.add_css_class("suggested-action")
        join.connect("clicked", lambda _b: self.join())
        self.password.add_suffix(join)
        self.password.connect("entry-activated", lambda _r: self.join())
        secret.add(self.password)
        box.append(secret)

        self.problem = Gtk.Label(xalign=0, wrap=True, visible=False)
        self.problem.add_css_class("danger-note")
        box.append(self.problem)

        buttons = Gtk.Box(halign=Gtk.Align.END, spacing=8)
        buttons.set_margin_top(10)
        again = Gtk.Button(label="Check again")
        again.add_css_class("pill")
        again.connect("clicked", lambda _b: self.refresh())
        buttons.append(again)
        self.go = Gtk.Button(label="Continue", sensitive=False)
        self.go.add_css_class("pill")
        self.go.add_css_class("suggested-action")
        self.go.connect("clicked", lambda _b: self.on_online())
        buttons.append(self.go)
        box.append(buttons)

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
        online, networks = found
        self.go.set_sensitive(online)
        self.status_icon.set_from_icon_name(
            "network-transmit-receive-symbolic" if online
            else "network-offline-symbolic")
        if online:
            self.status.set_title("Connected to the internet")
            self.status.set_subtitle("Continue when you are ready.")
        else:
            self.status.set_title("Not connected")
            self.status.set_subtitle("Install stays unavailable until Osiris "
                                     "can reach the internet.")
        for row in self.rows:
            self.wifi_group.remove(row)
        self.rows = []
        for network in networks:
            row = Adw.ActionRow(title=network.ssid, subtitle=network.summary)
            row.add_prefix(Gtk.Image(icon_name=network.icon))
            if network.asks_password:
                row.add_suffix(Gtk.Image(
                    icon_name="network-wireless-encrypted-symbolic"))
            row.set_activatable(True)
            row.connect("activated", lambda _r, chosen=network: self.choose(chosen))
            self.wifi_group.add(row)
            self.rows.append(row)

    def choose(self, network) -> None:
        self.chosen = network
        if not network.asks_password:
            self.join()
            return
        self.password.set_text("")
        self.password.set_title(f"Password for {network.ssid}")
        self.password.set_visible(True)
        self.password.grab_focus()

    def join(self) -> None:
        network, secret = self.chosen, self.password.get_text()
        if network is None:
            return

        def work():
            try:
                self.network.join(network, secret)
            except JoinFailed as refusal:
                return str(refusal)
            return self.network.online(), self.network.wifi()

        self.background(work, self.joined)

    def joined(self, outcome) -> None:
        if isinstance(outcome, str):
            self.problem.set_text(outcome)
            self.problem.set_visible(True)
            return
        self.problem.set_visible(False)
        self.password.set_visible(False)
        self.show(outcome)
