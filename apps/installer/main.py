#!/usr/bin/env python3
"""Osiris installer.

GTK4 + libadwaita, the same toolkit as the Appearance app. A wizard that
collects what the install needs and hands it to archinstall, through
osiris.provision.installer. This file contains no partitioning, no package
installation and no bootloader logic; archinstall does all of that (ADR 0012).

Runs as root from the live ISO. That is deliberate: the alternative is a
polkit action and a privilege boundary in the middle of a program whose entire
purpose is to repartition the disk, on a medium where there is nothing to
protect and no other user to protect it from.
"""
import dataclasses
import os
import subprocess
import sys
import threading
import traceback
import zoneinfo

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# The osiris package sits two directories up, both in a checkout and in the
# copy on the live medium.
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

import disks  # noqa: E402
from network_page import NetworkPage  # noqa: E402

from osiris.model.disk import Disk, Filesystem, human  # noqa: E402
from osiris.model.layout import InstallMode, Layout  # noqa: E402
from osiris.model.request import InstallRequest, passphrase_problem  # noqa: E402
from osiris.platform.http import UrllibClient  # noqa: E402
from osiris.platform.process import SubprocessRunner  # noqa: E402
from osiris.provision.network import Network  # noqa: E402

LOGO_PATHS = ("/usr/share/osiris/logo-dark.png",
              os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                  os.path.abspath(__file__)))), "branding", "logo-dark.png"))

MODE_TITLES = {
    InstallMode.WHOLE_DISK: "Erase the disk and install Osiris",
    InstallMode.FREE_SPACE: "Install in free space",
    InstallMode.EXISTING_PARTITION: "Install on a partition",
}

COMMON_KEYMAPS = ("us", "uk", "gb", "de", "fr", "es", "it", "dvorak", "colemak")



@dataclasses.dataclass
class Choices:
    """What the wizard has collected so far. Becomes an InstallRequest."""

    disk: str = ""
    disk_size: int = 0
    user: str = ""
    password: str = ""
    hostname: str = "osiris"
    timezone: str = "Europe/London"
    locale: str = "en_GB.UTF-8"
    keymap: str = "us"
    filesystem: str = "ext4"
    software_rendering: bool = False
    mode: InstallMode = InstallMode.WHOLE_DISK
    root_partition: str | None = None
    encrypt: bool = False
    passphrase: str = dataclasses.field(default="", repr=False)

    def request(self) -> InstallRequest:
        return InstallRequest(
            disk=Disk(self.disk, self.disk_size),
            username=self.user,
            password=self.password,
            hostname=self.hostname,
            timezone=self.timezone,
            locale=self.locale,
            keymap=self.keymap,
            filesystem=Filesystem(self.filesystem),
            software_rendering=self.software_rendering,
            mode=self.mode,
            root_partition=self.root_partition,
            encrypt=self.encrypt,
            passphrase=self.passphrase if self.encrypt else "",
        )

CSS = b"""
.hero-logo { margin-bottom: 6px; }
.hero-title { font-size: 2.1em; font-weight: 800; }
.hero-subtitle { font-size: 1.05em; opacity: 0.7; }
.disk-size { font-feature-settings: "tnum"; opacity: 0.75; }
.log-view {
    font-family: monospace;
    font-size: 0.85em;
    padding: 10px;
}
.danger-note { color: @error_color; font-weight: 600; }
"""


def screen_size(fallback: tuple[int, int] = (1280, 800)) -> tuple[int, int]:
    """The monitor's size, so the window fills it.

    There is no window manager on the live ISO - a systemd unit starts X and
    the installer, nothing else - so fullscreen() has nobody to honour it and
    maximising does nothing. The window has to ask for the right size itself,
    or it sits at 880x660 in the corner of the screen.
    """
    display = Gdk.Display.get_default()
    if display is None:
        return fallback
    monitors = display.get_monitors()
    if monitors.get_n_items() == 0:
        return fallback
    geometry = monitors.get_item(0).get_geometry()
    if geometry.width < 640 or geometry.height < 480:
        return fallback
    return geometry.width, geometry.height


def in_virtual_machine() -> bool:
    """Is this a guest? Used to default the software-rendering switch.

    A VM usually has no GPU to accelerate anything, and a desktop that tries
    comes up to a black screen. systemd-detect-virt exits 0 and names the
    hypervisor when there is one, non-zero on bare metal.
    """
    try:
        result = subprocess.run(["systemd-detect-virt"], capture_output=True,
                                text=True)
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() not in ("", "none")


def logo() -> str | None:
    for path in LOGO_PATHS:
        if os.path.exists(path):
            return path
    return None


def locales() -> list[str]:
    """UTF-8 locales glibc knows about, common ones first."""
    found = []
    try:
        with open("/usr/share/i18n/SUPPORTED") as fh:
            for line in fh:
                name, _, charset = line.strip().partition(" ")
                if charset == "UTF-8" and name.endswith(".UTF-8"):
                    found.append(name)
    except OSError:
        pass
    if not found:
        found = ["en_GB.UTF-8", "en_US.UTF-8"]
    preferred = [n for n in ("en_GB.UTF-8", "en_US.UTF-8") if n in found]
    return preferred + sorted(n for n in found if n not in preferred)


def keymaps() -> list[str]:
    try:
        listed = sorted(set(
            SubprocessRunner().capture("localectl", "list-keymaps").split()))
    except Exception:                                       # noqa: BLE001
        listed = []
    if not listed:
        return list(COMMON_KEYMAPS)
    first = [k for k in COMMON_KEYMAPS if k in listed]
    return first + [k for k in listed if k not in first]


def timezones() -> list[str]:
    try:
        found = sorted(zoneinfo.available_timezones())
    except Exception:                                       # noqa: BLE001
        found = []
    return found or ["Europe/London", "UTC"]


def dropdown(items: list[str], selected: str | None = None) -> Gtk.DropDown:
    """A searchable dropdown. Long lists here are unusable without search."""
    model = Gtk.StringList(strings=items)
    widget = Gtk.DropDown(model=model)
    widget.set_enable_search(True)
    widget.set_expression(
        Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
    widget.set_valign(Gtk.Align.CENTER)
    if selected in items:
        widget.set_selected(items.index(selected))
    return widget


def combo_row(title: str, subtitle: str, widget: Gtk.Widget) -> Adw.ActionRow:
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    row.add_suffix(widget)
    row.set_activatable_widget(widget)
    return row


def page(tag: str, title: str, child: Gtk.Widget,
         header: bool = True) -> Adw.NavigationPage:
    toolbar = Adw.ToolbarView()
    if header:
        toolbar.add_top_bar(Adw.HeaderBar())
    scroller = Gtk.ScrolledWindow(vexpand=True)
    scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroller.set_child(child)
    toolbar.set_content(scroller)
    return Adw.NavigationPage(child=toolbar, title=title, tag=tag)


def column(spacing: int = 18) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    box.set_margin_top(24)
    box.set_margin_bottom(24)
    box.set_halign(Gtk.Align.CENTER)
    # Centred in both directions: the window is the whole screen, and content
    # pinned to the top of a 1080p display looks like a rendering failure.
    box.set_valign(Gtk.Align.CENTER)
    box.set_size_request(560, -1)
    return box


def footer(label: str, handler, style: str = "suggested-action") -> Gtk.Box:
    box = Gtk.Box(halign=Gtk.Align.END)
    button = Gtk.Button(label=label)
    button.add_css_class("pill")
    button.add_css_class(style)
    button.connect("clicked", handler)
    box.append(button)
    box.button = button
    return box


class Window(Adw.ApplicationWindow):
    def __init__(self, app, network=None, background=None):
        super().__init__(application=app, title="Install Osiris")
        self.set_default_size(*screen_size())
        self.options = Choices()
        self.installing = False
        # A short timeout: offline, the check should fail in seconds, not
        # leave Next looking dead for half a minute.
        self.network = network or Network.for_this_machine(
            SubprocessRunner(), UrllibClient(timeout=10))
        self.background = background or self.in_background
        # archinstall's view of this machine's disks and firmware. Made when
        # the disk page is first shown: importing archinstall reads every
        # disk, which is not something the welcome page should wait on.
        self.machine = None
        self.contents = None

        self.nav = Adw.NavigationView()
        self.welcome = self.welcome_page()
        self.nav.add(self.welcome)
        self.set_content(self.nav)

        # Closing mid-install leaves a half-written disk and a running
        # pacstrap, so refuse until it is finished one way or the other.
        self.connect("close-request", lambda _w: self.installing)

    # ------------------------------------------------------------- 1 welcome

    def welcome_page(self) -> Adw.NavigationPage:
        box = column(10)
        mark = logo()
        if mark:
            picture = Gtk.Picture.new_for_filename(mark)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(-1, 150)
            picture.add_css_class("hero-logo")
            box.append(picture)

        title = Gtk.Label(label="Osiris")
        title.add_css_class("hero-title")
        box.append(title)
        subtitle = Gtk.Label(label="Install this system onto a disk")
        subtitle.add_css_class("hero-subtitle")
        subtitle.set_margin_bottom(14)
        box.append(subtitle)

        group = Adw.PreferencesGroup(title="Region")
        self.locale = dropdown(locales(), self.options.locale)
        group.add(combo_row("Language", "Sets the system locale", self.locale))
        self.timezone = dropdown(timezones(), self.options.timezone)
        group.add(combo_row("Time zone", "Used for the system clock",
                            self.timezone))
        self.keymap = dropdown(keymaps(), self.options.keymap)
        group.add(combo_row("Keyboard", "Console keymap", self.keymap))
        box.append(group)

        hardware = Adw.PreferencesGroup(title="Hardware")
        self.software_rendering = Adw.SwitchRow(
            title="Software rendering",
            subtitle="For machines with no working GPU driver, including most "
                     "virtual machines. Slower, but it comes up.")
        self.software_rendering.set_active(in_virtual_machine())
        hardware.add(self.software_rendering)
        box.append(hardware)

        bar = footer("Next", lambda _b: self.leave_welcome())
        self.welcome_next = bar.button
        bar.set_margin_top(10)
        box.append(bar)
        return page("welcome", "Welcome", box, header=False)

    def leave_welcome(self) -> None:
        self.options.locale = self.locale.get_selected_item().get_string()
        self.options.timezone = self.timezone.get_selected_item().get_string()
        self.options.keymap = self.keymap.get_selected_item().get_string()
        self.options.software_rendering = self.software_rendering.get_active()
        self.welcome_next.set_sensitive(False)
        self.background(self.network.online, self.after_connection_check)

    def after_connection_check(self, online: bool) -> None:
        """The disk page if the install can download, the connect step if not."""
        self.welcome_next.set_sensitive(True)
        if online:
            self.nav.push(self.disk_page())
            return
        self.nav.push(self.network_page(
            lambda: self.nav.replace([self.welcome, self.disk_page()])))

    def network_page(self, on_online) -> NetworkPage:
        return NetworkPage(self.network, on_online, self.background)

    def in_background(self, work, done) -> None:
        """Run work off the main loop and hand its result back to it."""
        def run():
            try:
                result = work()
            except Exception:                               # noqa: BLE001
                traceback.print_exc()
                return
            GLib.idle_add(lambda: done(result) or False)
        threading.Thread(target=run, daemon=True).start()

    # ---------------------------------------------------------------- 2 disk

    def disk_page(self) -> Adw.NavigationPage:
        box = column()
        found = disks.available()
        if self.machine is None:
            from osiris.provision.installer import Installer

            self.machine = Installer.for_this_machine(SubprocessRunner())
        group = Adw.PreferencesGroup(
            title="Target disk",
            description="Pick the disk, then how Osiris goes onto it.")

        self.disk_choice = None
        self.disk_next = None
        if not found:
            group.add(Adw.ActionRow(
                title="No disks found",
                subtitle="Osiris needs a writable disk of at least "
                         f"{disks.human(disks.MINIMUM_BYTES)}."))
        first = None
        for disk in found:
            row = Adw.ActionRow(title=disk["label"] or disk["path"])
            detail = [disk["path"], disks.human(disk["size"])]
            if disk["transport"]:
                detail.append(disk["transport"])
            # A mounted disk is almost always the medium being booted from.
            # Erasing it fails halfway through with an I/O error, so it is
            # offered greyed out with the reason rather than left off the list
            # to be hunted for.
            if disk["too_small"]:
                detail.append(f"too small - needs "
                              f"{disks.human(disks.MINIMUM_BYTES)}")
            elif disk["in_use"]:
                detail.append("in use - cannot be erased while mounted")
            row.set_subtitle("  ".join(detail))

            usable = not (disk["too_small"] or disk["in_use"])
            radio = Gtk.CheckButton()
            radio.set_valign(Gtk.Align.CENTER)
            if first is None:
                first = radio
            else:
                radio.set_group(first)
            if usable:
                radio.connect("toggled", self.choose_disk, disk)
            else:
                row.set_sensitive(False)
            row.add_prefix(radio)
            row.set_activatable_widget(radio)
            group.add(row)
        box.append(group)

        box.append(self.layout_group())

        bar = footer("Next", lambda _b: self.leave_disk())
        bar.button.set_sensitive(False)
        self.disk_next = bar.button
        bar.set_margin_top(10)
        box.append(bar)
        return page("disk", "Disk", box)

    def layout_group(self) -> Gtk.Box:
        """How Osiris goes onto the chosen disk, and what that costs."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)

        self.mode_group = Adw.PreferencesGroup(title="How to install")
        box.append(self.mode_group)
        self.mode_rows = []

        tools = Adw.PreferencesGroup()
        gparted = Adw.ActionRow(
            title="Make room for Osiris",
            subtitle="Shrink or delete partitions in GParted, then come back. "
                     "Back up anything you care about first.")
        button = Gtk.Button(label="Open GParted", valign=Gtk.Align.CENTER)
        button.connect("clicked", lambda _b: self.open_gparted())
        gparted.add_suffix(button)
        tools.add(gparted)
        box.append(tools)

        group = Adw.PreferencesGroup(title="Layout")
        self.filesystem = dropdown(["ext4", "btrfs"], self.options.filesystem)
        group.add(combo_row(
            "Filesystem",
            "btrfs adds compression and snapshot-ready subvolumes; "
            "ext4 is the simpler, more predictable choice",
            self.filesystem))

        self.plan = Gtk.Label(xalign=0, wrap=True)
        self.plan.add_css_class("disk-size")
        self.plan.add_css_class("monospace")
        self.plan.set_margin_top(8)
        self.plan.set_margin_start(4)
        group.add(self.plan)
        box.append(group)

        box.append(self.encryption_group())

        self.filesystem.connect("notify::selected", lambda *_a: self.show_plan())
        self.show_modes()
        return box

    def encryption_group(self) -> Adw.PreferencesGroup:
        """Encrypt the root, and the passphrase that opens it at every boot."""
        group = Adw.PreferencesGroup(title="Encryption")
        self.encrypt = Adw.SwitchRow(
            title="Encrypt the system",
            subtitle="A passphrase is asked for every time the computer "
                     "starts. Without it, nothing on the disk can be read.")
        self.encrypt.set_active(self.options.encrypt)
        group.add(self.encrypt)

        self.passphrase_row = Adw.PasswordEntryRow(title="Passphrase")
        self.passphrase_confirm = Adw.PasswordEntryRow(
            title="Confirm passphrase")
        group.add(self.passphrase_row)
        group.add(self.passphrase_confirm)

        # A row rather than a free label: a long wrapping GtkLabel in the
        # group stretched the whole page to the width of its text.
        self.passphrase_note = Adw.ActionRow(
            title="A forgotten passphrase cannot be recovered",
            subtitle="The data on this disk would be lost for good. Nobody "
                     "can recover it, including Osiris. Write it down "
                     "somewhere safe.")
        self.passphrase_note.add_prefix(
            Gtk.Image(icon_name="dialog-warning-symbolic"))
        group.add(self.passphrase_note)

        self.passphrase_problem = Gtk.Label(xalign=0, wrap=True)
        self.passphrase_problem.add_css_class("danger-note")
        self.passphrase_problem.set_margin_start(4)
        group.add(self.passphrase_problem)

        self.encrypt.connect("notify::active", lambda *_a: self.show_plan())
        for row in (self.passphrase_row, self.passphrase_confirm):
            row.connect("changed", lambda *_a: self.show_plan())
        return group

    def check_passphrase(self) -> str | None:
        """What is wrong with the passphrase, or None.

        Shown only once there is something typed to be wrong; an empty form
        just keeps Next disabled.
        """
        encrypt = self.encrypt.get_active()
        for widget in (self.passphrase_row, self.passphrase_confirm,
                       self.passphrase_note, self.passphrase_problem):
            widget.set_visible(encrypt)
        if not encrypt:
            return None
        passphrase = self.passphrase_row.get_text()
        confirm = self.passphrase_confirm.get_text()
        problem = passphrase_problem(passphrase)
        if problem is None and passphrase != confirm:
            problem = "the passphrases do not match"
        shown = problem if passphrase or confirm else None
        self.passphrase_problem.set_text(
            shown[0].upper() + shown[1:] if shown else "")
        self.passphrase_problem.set_visible(bool(shown))
        return problem

    def show_modes(self) -> None:
        """Offer only the modes this disk and this machine can do."""
        for row in self.mode_rows:
            self.mode_group.remove(row)
        self.mode_rows = []
        self.partition_choice = None

        contents = self.contents
        if contents is None:
            self.mode_group.set_description("Choose a disk first.")
            self.show_plan()
            return
        offered = contents.modes(self.machine.uefi)
        if self.options.mode not in offered:
            self.options.mode = InstallMode.WHOLE_DISK

        notes = []
        if not self.machine.uefi:
            notes.append("Installing beside another system needs a UEFI "
                         "machine; this one started in BIOS mode.")
        elif not contents.gpt:
            notes.append("Installing beside another system needs a GPT disk.")
        self.mode_group.set_description(" ".join(notes) or None)

        first = None
        for mode in offered:
            row = Adw.ActionRow(title=MODE_TITLES[mode],
                                subtitle=self.mode_subtitle(mode))
            radio = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            if first is None:
                first = radio
            else:
                radio.set_group(first)
            radio.set_active(mode is self.options.mode)
            radio.connect("toggled", self.choose_mode, mode)
            row.add_prefix(radio)
            row.set_activatable_widget(radio)
            if mode is InstallMode.EXISTING_PARTITION:
                candidates = contents.candidates_for_root()
                self.partition_choice = dropdown(
                    [p.description for p in candidates])
                self.partition_paths = [p.path for p in candidates]
                self.partition_choice.connect(
                    "notify::selected", lambda *_a: self.show_plan())
                row.add_suffix(self.partition_choice)
            self.mode_group.add(row)
            self.mode_rows.append(row)
        self.show_plan()

    def mode_subtitle(self, mode: InstallMode) -> str:
        if mode is InstallMode.WHOLE_DISK:
            return "Everything on the disk is erased."
        if mode is InstallMode.FREE_SPACE:
            region = self.contents.largest_free if self.contents else None
            size = human(region.size) if region else "the"
            return f"Uses {size} of unallocated space. Nothing else is touched."
        return "Formats the partition you choose. Nothing else is touched."

    def choose_mode(self, radio: Gtk.CheckButton, mode: InstallMode) -> None:
        if radio.get_active():
            self.options.mode = mode
            self.show_plan()

    def read_layout(self) -> None:
        self.options.filesystem = self.filesystem.get_selected_item().get_string()
        self.options.encrypt = self.encrypt.get_active()
        self.options.passphrase = self.passphrase_row.get_text()
        self.options.root_partition = None
        if (self.options.mode is InstallMode.EXISTING_PARTITION
                and self.partition_choice is not None
                and self.partition_paths):
            index = self.partition_choice.get_selected()
            self.options.root_partition = self.partition_paths[index]

    def current_layout(self) -> Layout | None:
        if self.contents is None:
            return None
        root = next((p for p in self.contents.partitions
                     if p.path == self.options.root_partition), None)
        return Layout(self.contents, self.options.mode,
                      Filesystem(self.options.filesystem), root_partition=root,
                      encrypted=self.options.encrypt)

    def show_plan(self) -> None:
        """Say what the disk will look like afterwards, in so many words."""
        self.read_layout()
        passphrase = self.check_passphrase()
        layout = self.current_layout()
        if layout is None:
            self.plan.set_text("")
            return
        lines = layout.describe()
        lines += [""] + [f"erased   {item}" for item in layout.destroys]
        lines += [f"kept     {item}" for item in layout.keeps]
        lines += [f"problem  {item}" for item in layout.problems]
        self.plan.set_text("\n".join(lines))
        if self.disk_next is not None:
            self.disk_next.set_sensitive(
                not layout.problems and passphrase is None)

    def open_gparted(self) -> None:
        """Run GParted, then read the disks again and redraw this page."""
        path = self.options.disk or None

        def run() -> None:
            argv = ["gparted"] + ([path] if path else [])
            try:
                subprocess.run(argv, check=False)
            except OSError:
                pass
            GLib.idle_add(self.after_gparted)

        threading.Thread(target=run, daemon=True).start()

    def after_gparted(self) -> bool:
        """Re-read the disks and redraw the options for the chosen one.

        In place rather than by replacing the page: the disks themselves are
        the same, only what is on them changed.
        """
        from osiris.provision import disk_contents

        disk_contents.rescan()
        if self.options.disk:
            self.contents = self.machine.contents(self.options.disk)
        self.show_modes()
        return GLib.SOURCE_REMOVE

    def leave_disk(self) -> None:
        self.read_layout()
        self.nav.push(self.account_page())

    def choose_disk(self, radio: Gtk.CheckButton, disk: dict) -> None:
        if not radio.get_active():
            return
        self.disk_choice = disk
        self.options.disk = disk["path"]
        self.options.disk_size = disk["size"]
        self.contents = self.machine.contents(disk["path"])
        self.show_modes()

    # ------------------------------------------------------------- 3 account

    def account_page(self) -> Adw.NavigationPage:
        box = column()
        group = Adw.PreferencesGroup(
            title="Your account",
            description="This account can administer the system with sudo.")

        self.hostname_row = Adw.EntryRow(title="Computer name")
        self.hostname_row.set_text(self.options.hostname)
        group.add(self.hostname_row)

        self.user_row = Adw.EntryRow(title="Username")
        group.add(self.user_row)

        self.password_row = Adw.PasswordEntryRow(title="Password")
        group.add(self.password_row)
        self.confirm_row = Adw.PasswordEntryRow(title="Confirm password")
        group.add(self.confirm_row)
        box.append(group)

        self.account_problem = Gtk.Label(xalign=0)
        self.account_problem.add_css_class("danger-note")
        self.account_problem.set_visible(False)
        box.append(self.account_problem)

        bar = footer("Next", lambda _b: self.leave_account())
        bar.button.set_sensitive(False)
        self.account_next = bar.button
        bar.set_margin_top(10)
        box.append(bar)

        for row in (self.hostname_row, self.user_row,
                    self.password_row, self.confirm_row):
            row.connect("changed", lambda *_a: self.check_account())
        return page("account", "Account", box)

    def check_account(self) -> None:
        """Say what is wrong, but only once there is something to be wrong."""
        user = self.user_row.get_text().strip()
        password = self.password_row.get_text()
        confirm = self.confirm_row.get_text()
        host = self.hostname_row.get_text().strip()

        problem = ""
        if user and not user.isascii():
            problem = "Username must be ASCII"
        elif user and not (user[0].isalpha() or user[0] == "_"):
            problem = "Username must start with a letter"
        elif user and not all(c.isalnum() or c in "_-" for c in user):
            problem = "Username may only contain letters, digits, - and _"
        elif user and user != user.lower():
            problem = "Username must be lowercase"
        elif host and not all(c.isalnum() or c == "-" for c in host):
            problem = "Computer name may only contain letters, digits and -"
        elif password and len(password) < 6:
            problem = "Password must be at least 6 characters"
        elif confirm and password != confirm:
            problem = "Passwords do not match"

        self.account_problem.set_text(problem)
        self.account_problem.set_visible(bool(problem))
        self.account_next.set_sensitive(
            bool(user and host and len(password) >= 6 and password == confirm
                 and not problem))

    def leave_account(self) -> None:
        self.options.hostname = self.hostname_row.get_text().strip()
        self.options.user = self.user_row.get_text().strip()
        self.options.password = self.password_row.get_text()
        self.nav.push(self.confirm_page())

    # ------------------------------------------------------------- 4 confirm

    def confirm_page(self) -> Adw.NavigationPage:
        box = column()
        disk = self.disk_choice or {}
        summary = Adw.PreferencesGroup(title="Summary")
        for title, value in (
            ("Install to", f"{disk.get('label', '')} "
                           f"({self.options.disk}, "
                           f"{disks.human(disk.get('size', 0))})".strip()),
            ("Computer name", self.options.hostname),
            ("Username", self.options.user),
            ("Language", self.options.locale),
            ("Time zone", self.options.timezone),
            ("Keyboard", self.options.keymap),
            ("How", MODE_TITLES[self.options.mode]),
            ("Filesystem", self.options.filesystem),
            ("Encryption", "LUKS2, passphrase asked at every start"
                           if self.options.encrypt else "None"),
            ("Graphics", "Software rendering"
                         if self.options.software_rendering
                         else "Hardware accelerated"),
        ):
            row = Adw.ActionRow(title=title, subtitle=value)
            row.add_css_class("property")
            summary.add(row)
        box.append(summary)

        layout = self.current_layout()
        if self.options.mode is InstallMode.WHOLE_DISK or layout is None:
            heading = "Everything on this disk will be erased"
            detail = (f"{self.options.disk} will be repartitioned. There is no "
                      "undo, and anything on it now will be gone.")
            consent = f"I understand that {self.options.disk} will be erased"
        elif self.options.mode is InstallMode.FREE_SPACE:
            heading = "Osiris goes into the free space"
            detail = ("No existing partition is erased. Kept: "
                      + "; ".join(layout.keeps or ["nothing else on the disk"]))
            consent = ("I understand that the disk's partition table will be "
                       "changed, and I have a backup")
        else:
            erased = "; ".join(layout.destroys)
            heading = "One partition will be erased"
            detail = (f"Erased: {erased}. Kept: "
                      + "; ".join(layout.keeps or ["nothing else"]))
            consent = f"I understand that {self.options.root_partition} will be erased"

        warning = Adw.PreferencesGroup()
        banner = Adw.ActionRow(title=heading, subtitle=detail)
        banner.add_prefix(Gtk.Image(icon_name="dialog-warning-symbolic"))
        banner.add_css_class("error")
        warning.add(banner)
        box.append(warning)

        self.understood = Gtk.CheckButton(label=consent)
        self.understood.set_margin_top(4)
        box.append(self.understood)

        bar = footer("Install", lambda _b: self.start(), "destructive-action")
        bar.button.set_sensitive(False)
        self.install_button = bar.button
        self.understood.connect(
            "toggled", lambda c: bar.button.set_sensitive(c.get_active()))
        bar.set_margin_top(10)
        box.append(bar)
        return page("confirm", "Confirm", box)

    # ------------------------------------------------------------ 5 progress

    def progress_page(self) -> Adw.NavigationPage:
        box = column(14)
        box.set_size_request(640, -1)

        self.step_label = Gtk.Label(label="Starting", xalign=0)
        self.step_label.add_css_class("title-2")
        box.append(self.step_label)

        self.bar = Gtk.ProgressBar()
        self.bar.set_show_text(False)
        box.append(self.bar)

        self.retry_bar = Gtk.Box(halign=Gtk.Align.END, spacing=8)
        self.retry_bar.set_visible(False)
        back = Gtk.Button(label="Change settings")
        back.add_css_class("pill")
        back.connect("clicked", lambda _b: self.retry(to_start=True))
        again = Gtk.Button(label="Try again")
        again.add_css_class("pill")
        again.add_css_class("suggested-action")
        again.connect("clicked", lambda _b: self.retry())
        self.retry_bar.append(back)
        self.retry_bar.append(again)
        box.append(self.retry_bar)

        self.log = Gtk.TextView(editable=False, cursor_visible=False,
                                monospace=True)
        self.log.add_css_class("log-view")
        self.log.set_wrap_mode(Gtk.WrapMode.CHAR)
        log_window = Gtk.ScrolledWindow(vexpand=True)
        log_window.set_size_request(-1, 300)
        log_window.set_child(self.log)
        log_window.add_css_class("card")

        details = Gtk.Expander(label="Details")
        details.set_child(log_window)
        details.set_vexpand(True)
        box.append(details)

        # No header bar: there is nothing to go back to once the disk has been
        # partitioned, and offering a back arrow that does nothing is worse
        # than offering none.
        return page("progress", "Installing", box, header=False)

    def start(self) -> None:
        self.install_button.set_sensitive(False)
        self.background(self.network.online, self.start_if_online)

    def start_if_online(self, online: bool) -> None:
        """Install, or the connect step first if the connection went since."""
        if not online:
            self.install_button.set_sensitive(self.understood.get_active())
            self.nav.push(self.network_page(lambda: self.nav.pop()))
            return
        self.installing = True
        self.nav.push(self.progress_page())
        self.run_install()

    def run_install(self) -> None:
        self.installing = True
        self.retry_bar.set_visible(False)
        self.bar.remove_css_class("error")
        self.bar.set_fraction(0.0)
        self.step_label.set_text("Starting")
        # archinstall reports no fraction complete, so the bar says "working"
        # rather than inventing a percentage. The Details log shows each step.
        GLib.timeout_add(120, self.pulse)
        threading.Thread(target=self.worker, daemon=True).start()

    def retry(self, to_start: bool = False) -> None:
        """Run it again, or go back and change something first.

        Retrying is safe to offer because archinstall unmounts whatever a
        previous attempt left mounted on the disk before it repartitions it.
        Most failures here are a dropped network or a mirror that went away
        mid-download, and those succeed on a second run without changing a
        thing.
        """
        if to_start:
            self.nav.pop()
            return
        self.append_log("")
        self.append_log("--- retrying ---")
        self.run_install()

    def worker(self) -> None:
        try:
            # Imported here, not at the top: archinstall reads the disks when
            # it is imported, and a disk plugged in after the installer
            # started would otherwise be missing from its list.
            from osiris.provision.installer import Installer

            runner = SubprocessRunner(sink=self.log_line)
            Installer.for_this_machine(runner).install(
                self.options.request(), progress=self.on_progress)
        except BaseException as error:                      # noqa: BLE001
            detail = traceback.format_exc()
            GLib.idle_add(self.failed, error, detail)
        else:
            GLib.idle_add(self.finished)

    # Called from the worker thread; everything touching GTK goes through
    # idle_add so it runs on the main loop.

    def log_line(self, line: str) -> None:
        GLib.idle_add(self.append_log, line)

    def on_progress(self, status) -> None:
        GLib.idle_add(self.set_progress, status.fraction, status.title)

    def append_log(self, line: str) -> bool:
        buffer = self.log.get_buffer()
        buffer.insert(buffer.get_end_iter(), line + "\n")
        # Keep the view on the newest line without a scroll mark dance.
        self.log.scroll_to_iter(buffer.get_end_iter(), 0.0, False, 0.0, 0.0)
        return GLib.SOURCE_REMOVE

    def pulse(self) -> bool:
        if self.installing:
            self.bar.pulse()
        return self.installing

    def set_progress(self, fraction: float, message: str) -> bool:
        if fraction >= 1.0:
            self.bar.set_fraction(fraction)
        self.step_label.set_text(message)
        return GLib.SOURCE_REMOVE

    def failed(self, error: BaseException, detail: str) -> bool:
        self.installing = False
        self.append_log("")
        self.append_log(detail.rstrip())
        self.step_label.set_text("Install failed")
        self.bar.add_css_class("error")
        self.retry_bar.set_visible(True)
        dialog = Adw.AlertDialog(
            heading="Install failed",
            body=f"{error}\n\nNothing on the disk is usable yet. Try again, "
                 "or go back and change the settings. Open Details for the "
                 "full output.")
        dialog.add_response("close", "Close")
        dialog.present(self)
        return GLib.SOURCE_REMOVE

    def finished(self) -> bool:
        self.installing = False
        self.nav.push(self.done_page())
        return GLib.SOURCE_REMOVE

    # ---------------------------------------------------------------- 6 done

    def done_page(self) -> Adw.NavigationPage:
        box = column(12)
        mark = logo()
        if mark:
            picture = Gtk.Picture.new_for_filename(mark)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(-1, 130)
            box.append(picture)

        title = Gtk.Label(label="Osiris is installed")
        title.add_css_class("hero-title")
        box.append(title)
        note = Gtk.Label(
            label="Remove the installation medium and restart.\n"
                  f"Sign in as {self.options.user}.",
            justify=Gtk.Justification.CENTER)
        note.add_css_class("hero-subtitle")
        box.append(note)

        bar = footer("Restart now", lambda _b: self.reboot())
        bar.set_halign(Gtk.Align.CENTER)
        bar.set_margin_top(16)
        box.append(bar)
        return page("done", "Finished", box, header=False)

    def reboot(self) -> None:
        try:
            SubprocessRunner().run("systemctl", "reboot")
        except Exception as error:                          # noqa: BLE001
            dialog = Adw.AlertDialog(
                heading="Could not restart",
                body=f"{error}\n\nRestart the machine manually.")
            dialog.add_response("close", "Close")
            dialog.present(self)


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.osiris.Installer")

    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK)
        display = Gdk.Display.get_default()
        if display is not None:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Window(self).present()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
