"""The Osiris boot splash: Plymouth's theme files, and where its hook goes.

The installed system (provision/branding.py) and the install medium
(iso/profile.py) both put these in place, so they are written down once, here.
"""

from __future__ import annotations

import re

THEME = "osiris"
THEME_DIR = f"/usr/share/plymouth/themes/{THEME}"

#: Kernel parameters that keep the console quiet, so Plymouth has the screen,
#: beyond the `quiet splash` that turns it on.
QUIET = "loglevel=3 rd.udev.log_level=3 vt.global_cursor_default=0"

THEME_FILE = f"""[Plymouth Theme]
Name=Osiris
Description=Osiris boot splash
ModuleName=script

[script]
ImageDir={THEME_DIR}
ScriptFile={THEME_DIR}/osiris.script
"""

# Plymouth's scripting language. Background colours are the Osiris Obsidian
# palette (#0d0d10) expressed as 0-1 floats.
SCRIPT = """# Osiris boot splash.
#
# Modelled on plymouth's own /usr/share/plymouth/themes/script example, which is
# known to render. The earlier version set sprite positions once at load and
# used a bare refresh callback; it drew nothing. Positions are recomputed in the
# callback here because Window geometry is not final when the script loads.

Window.SetBackgroundTopColor(0.051, 0.051, 0.063);
Window.SetBackgroundBottomColor(0.051, 0.051, 0.063);

logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
logo.opacity_angle = 0;

fun refresh_callback ()
  {
    logo.opacity_angle += ((2 * 3.14) / 60) * 0.5;
    min_opacity = 0.45;
    opacity = (Math.Cos(logo.opacity_angle) + 1) / 2;
    opacity *= 1 - min_opacity;
    opacity += min_opacity;

    logo.sprite.SetX(Window.GetX() + Window.GetWidth()  / 2
                     - logo.image.GetWidth()  / 2);
    logo.sprite.SetY(Window.GetY() + Window.GetHeight() / 2
                     - logo.image.GetHeight() / 2);
    logo.sprite.SetOpacity(opacity);
  }

Plymouth.SetRefreshFunction(refresh_callback);
"""

_HOOK = re.compile(r"^HOOKS=.*\bplymouth\b", re.MULTILINE)


def has_hook(text: str) -> bool:
    """Whether mkinitcpio configuration `text` already runs the plymouth hook."""
    return _HOOK.search(text) is not None


def with_hook(text: str) -> str:
    """mkinitcpio configuration `text` with the plymouth hook in its HOOKS.

    Arch's plymouth package ships exactly one hook, named `plymouth`
    (`sd-plymouth` is a Fedora/Ubuntu convention and does not exist here -
    using it makes mkinitcpio fail and leaves an incomplete initramfs).
    It goes after `systemd` on the default systemd initramfs, or after `udev`
    on a busybox one. Without either, `text` is returned unchanged.
    """
    if has_hook(text):
        return text
    for anchor in ("systemd", "udev"):
        new = re.sub(
            rf"^(HOOKS=\(.*?\b{anchor}\b)",
            r"\1 plymouth",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if new != text:
            return new
    return text
