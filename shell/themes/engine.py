"""Load and apply Osiris themes.

Shared by the Appearance app and anything scripting a theme change, so both
take exactly the same code path.

How a theme is applied
----------------------
Each palette is compiled into a **real GTK theme** at
``~/.themes/Osiris-<palette>``, and every theme setting is pointed at it.

That matters. The obvious approach - keep one base theme and rewrite colour
overrides in ``~/.config/gtk-*/gtk.css`` - does not work: GTK reads user CSS
once at startup and Muffin caches window decorations, so running applications
and title bars keep the previous palette. Toolkits *do* reload when the theme
name changes, because that is the supported path. Giving each palette its own
theme name makes switching an ordinary theme change, which GTK, Muffin and
Cinnamon already know how to handle - no settings-key bouncing and no sleeps.

That includes Muffin's server-side title bars and the Cinnamon panel, both of
which repaint in place - verified on a running Nemo across three switches
without the shell being restarted. Nothing here replaces the shell: doing so
was measurably fragile, and it turned out not to be needed.

Theme search order, first match wins by name:
    ~/.config/osiris/themes/*.json      user themes
    /usr/share/osiris/themes/*.json     shipped themes
    <repo>/shell/themes/*.json          development checkout
"""
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icons  # noqa: E402
import plank  # noqa: E402
from paths import home, use_osiris_package  # noqa: E402

use_osiris_package()
import osiris  # noqa: E402
from osiris.platform.process import CommandError, SubprocessRunner  # noqa: E402
from osiris.provision.seeding import may_write  # noqa: E402
from osiris.skins import carried, library as skins, share  # noqa: E402
from osiris.skins.build import Built, build as build_skin_pack  # noqa: E402
from osiris.skins.pack import Look, SkinpackError  # noqa: E402
from osiris.themes import terminal  # noqa: E402
from osiris.themes.at_login import theme_to_apply  # noqa: E402
from osiris.themes.adwaita import adwaita_css  # noqa: E402
from osiris.themes.switch import Switch, keyfile  # noqa: E402


HOME = home()
REPO_THEMES = os.path.dirname(os.path.abspath(__file__))

SEARCH = [
    os.path.join(HOME, ".config", "osiris", "themes"),
    "/usr/share/osiris/themes",
    REPO_THEMES,
]
USER_ASSETS = os.path.join(HOME, ".local", "share", "osiris")
USER_PREVIEWS = os.path.join(USER_ASSETS, "previews")
USER_WALLPAPERS = os.path.join(USER_ASSETS, "wallpapers")
# Which theme each cached asset was rendered from. See _signature().
ASSET_MANIFEST = os.path.join(USER_ASSETS, "assets.json")
PREVIEW_DIRS = [
    USER_PREVIEWS,
    "/usr/share/osiris/themes/previews",
    os.path.join(REPO_THEMES, "previews"),
]
STATE = os.path.join(HOME, ".config", "osiris", "theme")
# The names of starred themes, one per line.
FAVOURITES = os.path.join(HOME, ".config", "osiris", "favourites")
#: Applied on a user's first login, before they have chosen anything.
DEFAULT_THEME = "osiris-obsidian"
#: The Osiris version this home was last brought up to at login.
BROUGHT_UP_TO = os.path.join(HOME, ".config", "osiris", "version")
WALLPAPERS = "/usr/share/backgrounds/osiris"

THEMES_DIR = os.path.join(HOME, ".themes")
# Skins, first match wins by name: the person's, shipped, development checkout.
SKIN_DIRS = [
    os.path.join(USER_ASSETS, "skins"),
    "/usr/share/osiris/skins",
    os.path.join(os.path.dirname(REPO_THEMES), "skins"),
]
SKIN_CHOICE = os.path.join(HOME, ".config", "osiris", "skin")
# Where a Skin's carried icon sets, cursors and fonts are installed, once each.
ICONS_DIR = os.path.join(HOME, ".local", "share", "icons")
FONTS_DIR = os.path.join(HOME, ".local", "share", "fonts", "osiris-skins")
SKIN_WORK = os.path.join(HOME, ".cache", "osiris", "skins")
THEME_PREFIX = "Osiris-"
CINNAMON_BASE = "/usr/share/cinnamon/theme"

REQUIRED_COLORS = (
    "background surface surfaceMuted border borderActive foreground "
    "foregroundMuted accent accentMuted success warning danger").split()


# --------------------------------------------------------------------------- #
# loading

def _files() -> dict:
    found = {}
    for directory in reversed(SEARCH):        # later entries override earlier
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith(".json"):
                found[name[:-5]] = os.path.join(directory, name)
    return found


def validate(theme: dict) -> None:
    """Raise ValueError on a theme that would apply badly.

    Hand-written themes are expected, so a typo should say what is wrong rather
    than producing an unreadable desktop.
    """
    colors = theme.get("colors")
    if not isinstance(colors, dict):
        raise ValueError(f"{theme['name']}: no colors block")
    missing = [k for k in REQUIRED_COLORS if k not in colors]
    if missing:
        raise ValueError(f"{theme['name']}: missing colours: "
                         f"{', '.join(missing)}")

    def check(block: dict, where: str) -> None:
        for key, value in block.items():
            if not (isinstance(value, str) and value.startswith("#")
                    and len(value) == 7):
                raise ValueError(f"{theme['name']}: {where} {key}={value!r} "
                                 f"is not #rrggbb")

    check(colors, "colour")
    # The terminal palette goes straight into ghostty's config, so a bad value
    # there breaks the terminal rather than the desktop - still worth catching.
    terminal = theme.get("terminal")
    if isinstance(terminal, dict):
        check(terminal, "terminal colour")


def is_user_theme(name: str) -> bool:
    """Is this name served from the user's own theme directory?

    A user theme may shadow a shipped one by name - that is the documented way
    to fork "nord" without editing a root-owned file. Its preview and wallpaper
    must then also come from the user's directory, or the fork shows the
    original's artwork.
    """
    source = _files().get(name)
    return source is not None and source.startswith(SEARCH[0])


def preview_path(name: str) -> str | None:
    directories = [USER_PREVIEWS] if is_user_theme(name) else PREVIEW_DIRS
    for directory in directories:
        candidate = os.path.join(directory, f"{name}.png")
        if os.path.exists(candidate):
            return candidate
    return None


def picture_of(theme: dict) -> str | None:
    """The picture a theme was made from, which is its wallpaper, if any.

    Named by absolute path; a shipped theme's wallpaper is a bare file name.
    """
    named = theme.get("wallpaper")
    if named and os.path.isabs(named):
        return named
    return None


def wallpaper_for(theme: dict) -> str:
    name = theme["name"]
    picture = picture_of(theme)
    if picture is not None:
        return picture
    named = theme.get("wallpaper")
    if named and named != "generated":
        return os.path.join(WALLPAPERS, named)
    if not is_user_theme(name):
        shipped = os.path.join(WALLPAPERS, f"{name}.png")
        if os.path.exists(shipped):
            return shipped
    return os.path.join(USER_WALLPAPERS, f"{name}.png")


def _signature(theme: dict, version: int) -> str:
    """What the cached assets for this theme were rendered from.

    A content hash rather than the theme file's timestamp. Timestamps answer
    the wrong question twice over: copying a theme file changes its mtime
    without changing the theme, and - the case that actually bit - editing the
    renderer changes the output without touching any theme at all. The version
    covers the second.
    """
    payload = json.dumps(theme, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{version}\x00{payload}".encode()).hexdigest()


def _manifest() -> dict:
    try:
        with open(ASSET_MANIFEST) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def ensure_assets(theme: dict) -> None:
    """Render the preview and wallpaper for a theme that needs them.

    Shipped themes get theirs at build time; anything a user writes is rendered
    on first sight, and re-rendered after an edit, so a hand-written theme is
    first-class rather than a blank card with no wallpaper. Failures are
    reported, not swallowed - a silently blank card is far harder to diagnose
    than a line on stderr.
    """
    name = theme["name"]
    try:
        import preview as renderer
    except ImportError as error:
        print(f"osiris-theme: cannot render assets: {error}", file=sys.stderr)
        return

    # Only assets under the user's own directory are ours to render. A shipped
    # theme's preview and wallpaper are built with the package and live in
    # root-owned directories; trying to refresh those just fails noisily.
    preview = preview_path(name)
    wallpaper = wallpaper_for(theme)
    # A picture the theme was made from is never rendered over.
    mine = {"preview": preview is None or preview.startswith(USER_ASSETS),
            "wallpaper": (wallpaper.startswith(USER_ASSETS)
                          and picture_of(theme) is None)}
    if not any(mine.values()):
        return

    signature = _signature(theme, renderer.RENDERER_VERSION)
    manifest = _manifest()
    current = (manifest.get(name) == signature
               and (preview is not None or not mine["preview"])
               and (os.path.exists(wallpaper) or not mine["wallpaper"]))
    if current:
        return

    rendered = True
    if mine["preview"]:
        try:
            renderer.render_theme(theme,
                                  os.path.join(USER_PREVIEWS, f"{name}.png"))
        except Exception as error:                          # noqa: BLE001
            rendered = False
            print(f"osiris-theme: preview for {name}: {error}", file=sys.stderr)
    if mine["wallpaper"]:
        try:
            renderer.render_wallpaper(theme, wallpaper)
        except Exception as error:                          # noqa: BLE001
            rendered = False
            print(f"osiris-theme: wallpaper for {name}: {error}",
                  file=sys.stderr)

    if rendered:
        manifest[name] = signature
        try:
            _write(ASSET_MANIFEST, json.dumps(manifest, indent=4) + "\n")
        except OSError as error:
            print(f"osiris-theme: recording assets for {name}: {error}",
                  file=sys.stderr)


def load(name: str) -> dict:
    path = _files().get(name)
    if path is None:
        raise KeyError(name)
    with open(path) as fh:
        theme = json.load(fh)
    theme.setdefault("name", name)
    theme.setdefault("label", name)
    validate(theme)
    ensure_assets(theme)
    theme["preview"] = preview_path(name)
    return theme


def all_themes() -> list[dict]:
    themes = []
    for name in _files():
        try:
            themes.append(load(name))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return sorted(themes, key=lambda t: (not t.get("dark", True), t["label"]))


def exists(name: str) -> bool:
    return name in _files()


def user_theme_path(name: str) -> str:
    return os.path.join(SEARCH[0], f"{name}.json")


def save(theme: dict) -> str:
    """Write a theme to the user's directory. Returns its name.

    Validated before it lands: a theme with a malformed colour would otherwise
    be written, fail to load, and vanish from the picker with no explanation.
    """
    validate(theme)
    name = theme["name"]
    _write(user_theme_path(name), json.dumps(theme, indent=4) + "\n")
    return name


def delete(name: str) -> None:
    """Remove a user theme and the assets generated for it.

    Refuses to touch a shipped theme - those belong to the package, and
    removing one would not survive the next update anyway.
    """
    if not is_user_theme(name):
        raise ValueError(f"{name} is not a user theme")
    picture = picture_of(load(name))
    os.remove(user_theme_path(name))
    for path in (os.path.join(USER_PREVIEWS, f"{name}.png"),
                 os.path.join(USER_WALLPAPERS, f"{name}.png"),
                 # Only a copy made for the theme; never a picture elsewhere.
                 *([picture] if picture and picture.startswith(USER_WALLPAPERS)
                   else [])):
        if os.path.exists(path):
            os.remove(path)
    manifest = _manifest()
    if manifest.pop(name, None) is not None:
        _write(ASSET_MANIFEST, json.dumps(manifest, indent=4) + "\n")


def favourites() -> set[str]:
    """The names of the themes the user has starred."""
    try:
        with open(FAVOURITES) as fh:
            return {line.strip() for line in fh if line.strip()}
    except OSError:
        return set()


def set_favourite(name: str, starred: bool) -> None:
    names = favourites()
    if starred:
        names.add(name)
    else:
        names.discard(name)
    _write(FAVOURITES, "".join(f"{n}\n" for n in sorted(names)))


def current() -> str | None:
    try:
        with open(STATE) as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def missing_packages(theme: dict) -> list[str]:
    """Required packages that are not installed.

    A theme naming an icon or GTK theme that is absent does not fail loudly -
    the toolkit silently falls back - so check before applying rather than
    leaving a half-applied theme.
    """
    absent = []
    for package in theme.get("requires") or []:
        if subprocess.run(["pacman", "-Q", package],
                          capture_output=True).returncode != 0:
            absent.append(package)
    return absent


# --------------------------------------------------------------------------- #
# derived values

def _ui(theme: dict) -> dict:
    ui = dict(theme.get("ui") or {})
    dark = theme.get("dark", True)
    ui.setdefault("gtk", "adw-gtk3-dark" if dark else "adw-gtk3")
    ui.setdefault("icons", "Papirus-Dark" if dark else "Papirus-Light")
    ui.setdefault("cursor", "Adwaita")
    ui.setdefault("font", "Noto Sans 10")
    ui.setdefault("mono", "FiraCode Nerd Font")
    return ui


def theme_name(theme: dict) -> str:
    return THEME_PREFIX + theme["name"]


# --------------------------------------------------------------------------- #
# generated config

def palette_css(theme: dict, base: str) -> str:
    """Import the base stylesheet, then override its colour definitions.

    url() inside the imported sheet resolves relative to that sheet, so the
    base theme's assets keep working from here.
    """
    c = theme["colors"]
    on_accent = c["background"]
    return f"""/* Generated by the Osiris theme engine: {theme['name']}. */
@import url("{base}");

@define-color accent_color {c['accent']};
@define-color accent_bg_color {c['accent']};
@define-color accent_fg_color {on_accent};

@define-color window_bg_color {c['surface']};
@define-color window_fg_color {c['foreground']};
@define-color view_bg_color {c['background']};
@define-color view_fg_color {c['foreground']};

@define-color headerbar_bg_color {c['surface']};
@define-color headerbar_fg_color {c['foreground']};
@define-color headerbar_border_color {c['border']};
@define-color headerbar_backdrop_color {c['background']};

@define-color sidebar_bg_color {c['surface']};
@define-color sidebar_fg_color {c['foreground']};
@define-color sidebar_backdrop_color {c['background']};
@define-color sidebar_border_color {c['border']};

@define-color popover_bg_color {c['surface']};
@define-color popover_fg_color {c['foreground']};
@define-color card_bg_color {c['surfaceMuted']};
@define-color card_fg_color {c['foreground']};
@define-color dialog_bg_color {c['surface']};
@define-color dialog_fg_color {c['foreground']};

@define-color destructive_bg_color {c['danger']};
@define-color destructive_color {c['danger']};
@define-color success_bg_color {c['success']};
@define-color success_color {c['success']};
@define-color warning_bg_color {c['warning']};
@define-color warning_color {c['warning']};

@define-color borders {c['border']};
@define-color theme_selected_bg_color {c['accent']};
@define-color theme_selected_fg_color {on_accent};

/* Server-side decorations: Muffin styles title bars from the GTK theme. */
.titlebar, headerbar.titlebar, .titlebar.default-decoration {{
  background-color: {c['surface']};
  color: {c['foreground']};
  border-bottom: 1px solid {c['border']}; }}

.titlebar:backdrop, headerbar.titlebar:backdrop,
.titlebar.default-decoration:backdrop {{
  background-color: {c['background']};
  color: {c['foregroundMuted']}; }}
"""


def cinnamon_css(theme: dict) -> str:
    """Palette overrides appended to Cinnamon's built-in shell stylesheet.

    Cinnamon's panel and menu use a shell theme, separate from GTK. No packaged
    theme ships a `cinnamon` directory, so Cinnamon falls back to its built-in
    stylesheet of hardcoded greys. The built-in is copied verbatim and these
    rules appended - later rules win, so only colours change and upstream
    layout fixes still apply.
    """
    c = theme["colors"]
    return f"""

/* ---- Osiris palette overrides ({theme['name']}) ---- */

.panel-top, .panel-bottom, .panel-left, .panel-right {{
  color: {c['foreground']};
  background-color: {c['surface']}; }}

.panel-status-button, .panel-button {{ color: {c['foreground']}; }}
.panel-button:hover {{ background-color: {c['surfaceMuted']}; }}

.popup-menu-content {{
  background-color: {c['surface']};
  border: 1px solid {c['border']}; }}

.menu {{ color: {c['foreground']}; }}
.popup-menu-item:active {{
  background-color: {c['accent']};
  color: {c['background']}; }}
.popup-menu-item:insensitive {{ color: {c['foregroundMuted']}; }}

.menu-category-button, .menu-application-button {{ color: {c['foreground']}; }}
.menu-category-button-selected, .menu-application-button-selected {{
  background-color: {c['accent']};
  color: {c['background']};
  border: 1px solid {c['borderActive']}; }}

.menu-search-entry, #menu-search-entry {{
  color: {c['foreground']};
  background-color: {c['background']};
  border: 1px solid {c['border']}; }}

.notification, .notification-with-image, .calendar, .osd-window {{
  background-color: {c['surface']};
  color: {c['foreground']};
  border: 1px solid {c['border']}; }}

.calendar-today {{
  background-color: {c['accent']};
  color: {c['background']}; }}

.window-list-item-box {{ color: {c['foregroundMuted']}; }}
.window-list-item-box:focus, .window-list-item-box:hover {{
  background-color: {c['surfaceMuted']};
  color: {c['foreground']}; }}

.workspace-switcher, .workspace-button {{ color: {c['foregroundMuted']}; }}
"""


ROFI_CONFIG = """configuration {
    modi: "drun,run";
    show-icons: true;
    drun-display-format: "{name}";
    display-drun: "";
}

@theme "osiris"
"""


def rofi_theme(theme: dict) -> str:
    c, ui = theme["colors"], _ui(theme)
    return f"""/* Generated by the Osiris theme engine. */
* {{
    background:     {c['background']};
    background-alt: {c['surface']};
    foreground:     {c['foreground']};
    muted:          {c['foregroundMuted']};
    accent:         {c['accent']};
    border-col:     {c['border']};
    font:           "{ui['mono']} 12";
}}
window {{ transparency: "real"; background-color: @background; border: 1px;
    border-color: @border-col; border-radius: 14px; width: 640px; padding: 0px; }}
mainbox {{ background-color: transparent; children: [ inputbar, listview ];
    padding: 10px; spacing: 8px; }}
inputbar {{ background-color: @background-alt; border-radius: 10px;
    padding: 10px 14px; spacing: 10px; children: [ prompt, entry ]; }}
prompt {{ background-color: transparent; text-color: @accent; }}
entry {{ background-color: transparent; text-color: @foreground;
    placeholder: "Search"; placeholder-color: @muted; }}
listview {{ background-color: transparent; lines: 8; columns: 1;
    scrollbar: false; spacing: 2px; fixed-height: false; }}
element {{ background-color: transparent; text-color: @muted;
    border-radius: 8px; padding: 9px 12px; spacing: 10px;
    children: [ element-icon, element-text ]; }}
element-icon {{ background-color: transparent; size: 20px; vertical-align: 0.5; }}
element-text {{ background-color: transparent; text-color: inherit;
    vertical-align: 0.5; }}
element selected {{ background-color: @accent; text-color: @background; }}
"""


# --------------------------------------------------------------------------- #
# applying

def _session_env() -> dict:
    """Environment that can reach the user's dconf.

    Over ssh or via ``su`` there is no session bus and gsettings writes into a
    throwaway database. /run/user/<uid>/bus is where logind puts the real one.
    """
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        bus = f"/run/user/{os.getuid()}/bus"
        if os.path.exists(bus):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus}"
    return env


def _load(settings: str, env: dict) -> None:
    """Write settings as one dconf change; see osiris/themes/switch.py."""
    subprocess.run(["dconf", "load", "/"], input=settings, text=True,
                   check=False, capture_output=True, env=env)


# The transition extension (shell/themes/transition@osiris, ADR 0014).
TRANSITION_BUS = "dev.osiris.Transition"
TRANSITION_PATH = "/dev/osiris/Transition"
# How long the frozen frame stays once the switch is written, so applications
# have repainted beneath it, and how long it takes to fade.
SETTLE_MS = 400
FADE_MS = 300


def _transition(method: str, *args: str, env: dict) -> bool:
    """Call the transition extension; False when it is not there."""
    try:
        result = subprocess.run(
            ["gdbus", "call", "--session", "--dest", TRANSITION_BUS,
             "--object-path", TRANSITION_PATH,
             "--method", f"{TRANSITION_BUS}.{method}", *args],
            check=False, capture_output=True, timeout=3, env=env)
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def _own_processes(command: str) -> list[int]:
    """The ids of this user's processes running `command`."""
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/comm") as fh:
                name = fh.read().strip()
            owner = os.stat(f"/proc/{entry}").st_uid
        except OSError:
            continue
        if name == command and owner == os.getuid():
            found.append(int(entry))
    return found


def _reload_terminals() -> None:
    """Have the user's running ghostty processes re-read their config.

    ghostty reloads on SIGUSR2; it would otherwise keep the old palette until
    relaunched.
    """
    for pid in _own_processes("ghostty"):
        try:
            os.kill(pid, signal.SIGUSR2)
        except OSError:
            pass


def _drift(theme: dict) -> None:
    """Change the moving wallpaper with everything else.

    Beneath the transition's frozen picture when there is one; drift.py on its
    own would notice the switch at its next poll, seconds after the rest.
    """
    try:
        # Here rather than at the top: drift imports this module.
        import drift
        drift.publish_now(theme)
    except Exception as error:                          # noqa: BLE001
        print(f"osiris-theme: moving wallpaper: {error}", file=sys.stderr)


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def _read(path: str) -> str | None:
    try:
        with open(path) as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def _seed(path: str, text: str) -> None:
    """Write a file the person keeps, unless they already have one."""
    if may_write(_read(path)):
        _write(path, text)


def _osiris_cinnamon(theme: dict, root: str) -> None:
    """Cinnamon's own stylesheet with the Theme's colours laid over it."""
    if os.path.isdir(CINNAMON_BASE):
        shutil.copytree(CINNAMON_BASE, os.path.join(root, "cinnamon"),
                        dirs_exist_ok=True)
        with open(os.path.join(root, "cinnamon", "cinnamon.css"), "a") as fh:
            fh.write(cinnamon_css(theme))


def build_theme(theme: dict) -> str | None:
    """Compile the palette into ~/.themes/Osiris-<palette>; return its name."""
    ui = _ui(theme)
    name = theme_name(theme)
    root = os.path.join(THEMES_DIR, name)
    try:
        if os.path.isdir(root):
            shutil.rmtree(root)
        os.makedirs(root, exist_ok=True)

        for version in ("gtk-3.0", "gtk-4.0"):
            base = f"/usr/share/themes/{ui['gtk']}/{version}/gtk.css"
            if not os.path.exists(base):
                continue
            _write(os.path.join(root, version, "gtk.css"),
                   palette_css(theme, base))

        _write(os.path.join(root, "index.theme"),
               "[X-GNOME-Metatheme]\n"
               f"Name={name}\n"
               "Type=X-GNOME-Metatheme\n"
               f"Comment=Osiris {theme.get('label', theme['name'])}\n"
               "Encoding=UTF-8\n"
               f"GtkTheme={name}\n"
               f"MetacityTheme={name}\n"
               f"IconTheme={ui['icons']}\n")

        _osiris_cinnamon(theme, root)
    except OSError as error:
        print(f"osiris-theme: building {name}: {error}", file=sys.stderr)
        return None

    _drop_themes_but(name)
    return name


def _drop_themes_but(name: str) -> None:
    """Drop Osiris's other generated themes so ~/.themes does not accumulate."""
    for entry in os.listdir(THEMES_DIR):
        if entry.startswith(THEME_PREFIX) and entry != name:
            shutil.rmtree(os.path.join(THEMES_DIR, entry), ignore_errors=True)


def build_skin(theme: dict) -> tuple[Built, Look] | None:
    """Build the chosen Skin in this Theme's colours; None for Osiris's own look.

    What the pack carries (icon sets, cursors, fonts) is installed first, so the
    look it names exists by the time the settings point at it.
    """
    folders = [Path(folder) for folder in SKIN_DIRS]
    pack = skins.find(folders, skins.chosen(Path(SKIN_CHOICE)))
    if pack is None:
        return None
    runner = SubprocessRunner()
    try:
        if carried.install(pack, Path(ICONS_DIR), Path(FONTS_DIR)):
            runner.run("fc-cache", "-f", FONTS_DIR, check=False, quiet=True)
        built = build_skin_pack(pack, theme, Path(THEMES_DIR), Path(SKIN_WORK),
                                runner)
    except (CommandError, SkinpackError, OSError) as error:
        # Osiris's own look rather than a half-built Skin.
        print(f"osiris-theme: Skin {pack.name}: {error}", file=sys.stderr)
        return None
    if not built.cinnamon:
        _osiris_cinnamon(theme, os.path.join(THEMES_DIR, built.theme))
    _drop_themes_but(built.theme)
    return built, pack.look("dark" if theme.get("dark", True) else "light")


def _link_adwaita_assets(skin: Built | None) -> None:
    """Point ~/.config/gtk-4.0/assets at the Skin's pictures, or remove our link.

    A Skin's libadwaita sheet names its pictures relative to itself, and it is
    installed as ~/.config/gtk-4.0/gtk.css. Only a link is ever removed, never a
    folder the person made.
    """
    link = os.path.join(HOME, ".config", "gtk-4.0", "assets")
    if os.path.islink(link):
        os.remove(link)
    pictures = os.path.join(THEMES_DIR, skin.theme, "gtk-4.0", "assets") if skin else ""
    if pictures and os.path.isdir(pictures) and not os.path.exists(link):
        os.symlink(pictures, link)


def skin_choices() -> list[tuple[str, str, str]]:
    """Every Skin as (name, label, who made it), Osiris's own first."""
    packs = skins.available([Path(folder) for folder in SKIN_DIRS])
    return [(skins.OSIRIS, "Osiris", "Osiris's own look")] + [
        (pack.name, pack.label, f"{pack.author}, {pack.licence}") for pack in packs
    ]


def chosen_skin() -> str:
    return skins.chosen(Path(SKIN_CHOICE))


def own_skins() -> set[str]:
    """The Skins the person opened or made, which they may delete."""
    return {pack.name for pack in skins.available([Path(SKIN_DIRS[0])])}


def _pack(name: str):
    pack = skins.find([Path(folder) for folder in SKIN_DIRS], name)
    if pack is None:
        raise SkinpackError(f"no Skin called {name}")
    return pack


def export_skin(name: str, folder: str) -> str:
    return str(share.export(_pack(name), Path(folder)))


def open_skin(path: str) -> str:
    """Add a shared Skin to the person's own; returns its name."""
    return share.open_file(Path(path), Path(SKIN_DIRS[0])).name


def duplicate_skin(name: str) -> str:
    """Copy a Skin into the person's own; returns the copy's name."""
    copy = share.duplicate(_pack(name), Path(SKIN_DIRS[0]), SubprocessRunner())
    return copy.name


def skin_folder(name: str) -> str:
    return str(_pack(name).root)


def delete_skin(name: str) -> None:
    """Delete one of the person's Skins, back to Osiris's look if it was worn."""
    share.delete(_pack(name), Path(SKIN_DIRS[0]))
    if chosen_skin() == name:
        set_skin(skins.OSIRIS)


def set_skin(name: str) -> list[str]:
    """Choose a Skin and wear it in the current Theme."""
    skins.choose(Path(SKIN_CHOICE), name)
    return apply(current() or DEFAULT_THEME)


def apply(name: str) -> list[str]:
    """Apply a theme to the current user.

    Returns the surfaces that will not pick the palette up until they are
    restarted. Everything else - GTK applications, window decorations, the
    Cinnamon panel, the wallpaper, running terminals - repaints in place, and
    the launcher reads its theme each time it opens.
    """
    theme = load(name)
    ui = _ui(theme)
    env = _session_env()
    # Without the extension the switch still applies, as one change.
    frozen = _transition("Freeze", env=env)

    # One theme name for every surface. Because the name differs per palette
    # this is an ordinary theme change, which GTK applications, Muffin's window
    # decorations and the Cinnamon shell all already reload on.
    worn = build_skin(theme)
    skin, look = worn if worn else (None, Look(None, None, None))
    applied = skin.theme if skin else build_theme(theme) or ui["gtk"]
    # Folders tinted to the accent, over the theme's declared icon set. Falls
    # back to that set when Papirus is absent rather than naming a theme that
    # does not exist.
    icon_theme = look.icons or icons.build(theme, ui["icons"]) or ui["icons"]
    wallpaper = wallpaper_for(theme)
    # Plank reads its theme when the setting changes, so the name carries the
    # palette - the same reason the GTK theme does.
    dock = (plank.install(skin.theme, skin.dock) if skin and skin.dock
            else plank.build(theme))

    _write(os.path.join(HOME, ".config", "rofi", "themes", "osiris.rasi"),
           skin.launcher if skin and skin.launcher else rofi_theme(theme))
    _seed(os.path.join(HOME, ".config", "rofi", "config.rasi"), ROFI_CONFIG)
    _write(os.path.join(HOME, terminal.THEME_FILE),
           terminal.theme_file(theme, mono=ui["mono"]))
    _seed(os.path.join(HOME, terminal.CONFIG_FILE), terminal.CONFIG)

    _load(keyfile(Switch(
        theme=applied,
        icons=icon_theme,
        cursor=look.cursor or ui["cursor"],
        font=look.font or ui["font"],
        dark=theme.get("dark", True),
        wallpaper=wallpaper if os.path.exists(wallpaper) else None,
        dock=dock,
    ), plank.PATH), env)

    _reload_terminals()

    # Superseded by the generated theme; left in place it would override it.
    stale = os.path.join(HOME, ".config", "gtk-3.0", "gtk.css")
    if os.path.exists(stale):
        os.remove(stale)
    # libadwaita ignores the generated theme and reads only this. A Skin's sheet
    # gives shape; the Theme's follows it because libadwaita 1.6+ takes its
    # accent only from the variables adwaita_css sets (ADR 0019).
    shape = _read(str(skin.adwaita)) if skin and skin.adwaita else None
    _write(os.path.join(HOME, ".config", "gtk-4.0", "gtk.css"),
           (shape + "\n" if shape else "") + adwaita_css(theme))
    _link_adwaita_assets(skin)

    _write(STATE, name + "\n")
    _drift(theme)
    if frozen:
        _transition("Release", str(SETTLE_MS), str(FADE_MS), env=env)
    return []


def login() -> None:
    """Bring this home up to the installed Osiris; see osiris.themes.at_login.

    Run from an autostart entry in every session. Without it a new account
    starts on the bare system defaults - Plank's own dock theme, rofi with no
    configuration at all - until the user happens to open Appearance.
    """
    brought_up_to = (_read(BROUGHT_UP_TO) or "").strip() or None
    name = theme_to_apply(current(), brought_up_to, osiris.__version__,
                          DEFAULT_THEME)
    if name is not None:
        apply(name)
    _write(BROUGHT_UP_TO, osiris.__version__ + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply an Osiris theme.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", metavar="NAME", help="apply this theme")
    group.add_argument("--skin", metavar="NAME",
                       help="wear this Skin (osiris for Osiris's own look)")
    group.add_argument("--login", action="store_true",
                       help="bring this home up to the installed Osiris")
    args = parser.parse_args()
    if args.login:
        login()
    elif args.skin:
        set_skin(args.skin)
    else:
        apply(args.apply)


if __name__ == "__main__":
    main()
