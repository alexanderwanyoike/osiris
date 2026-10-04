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

status = "normal";

fun refresh_callback ()
  {
    logo.opacity_angle += ((2 * 3.14) / 60) * 0.5;
    min_opacity = 0.45;
    opacity = (Math.Cos(logo.opacity_angle) + 1) / 2;
    opacity *= 1 - min_opacity;
    opacity += min_opacity;
    # Held steady while a passphrase is asked for: a pulsing logo above an
    # input reads as "still busy", which is the opposite of the truth.
    if (global.status == "password")
      opacity = 1;

    logo.sprite.SetX(Window.GetX() + Window.GetWidth()  / 2
                     - logo.image.GetWidth()  / 2);
    logo.sprite.SetY(Window.GetY() + Window.GetHeight() / 2
                     - logo.image.GetHeight() / 2);
    logo.sprite.SetOpacity(opacity);
  }

Plymouth.SetRefreshFunction(refresh_callback);

# Passphrase prompt, for an encrypted root.
#
# The initramfs `encrypt` hook asks through `plymouth ask-for-password`, and
# Plymouth hands the question to the theme. A script theme that does not
# register these two callbacks draws nothing, and the machine looks hung at
# the logo while it waits for a passphrase nobody was asked for. Text only, so
# the theme needs no images beyond the logo; the font is the one the plymouth
# initramfs hook copies in.

prompt.sprite = Sprite();
bullets.sprite = Sprite();

fun place_below_logo (sprite, image, gap)
  {
    sprite.SetX(Window.GetX() + Window.GetWidth() / 2 - image.GetWidth() / 2);
    sprite.SetY(Window.GetY() + Window.GetHeight() / 2
                + logo.image.GetHeight() / 2 + gap);
    sprite.SetZ(10000);
  }

fun display_password_callback (text, count)
  {
    global.status = "password";

    if (!text)
      text = "Passphrase";
    prompt.image = Image.Text(text, 0.85, 0.85, 0.88);
    prompt.sprite.SetImage(prompt.image);
    place_below_logo(prompt.sprite, prompt.image, 48);
    prompt.sprite.SetOpacity(1);

    # One mark per character typed, never the characters themselves. ASCII
    # on purpose: the initramfs text renderer drew U+2022 as an empty box.
    dots = "";
    for (index = 0; index < count; index++)
      dots = dots + "* ";
    if (count > 0)
      {
        bullets.image = Image.Text(dots, 0.85, 0.85, 0.88);
        bullets.sprite.SetImage(bullets.image);
        place_below_logo(bullets.sprite, bullets.image,
                         48 + prompt.image.GetHeight() + 16);
        bullets.sprite.SetOpacity(1);
      }
    else
      bullets.sprite.SetOpacity(0);
  }

fun display_normal_callback ()
  {
    global.status = "normal";
    prompt.sprite.SetOpacity(0);
    bullets.sprite.SetOpacity(0);
  }

Plymouth.SetDisplayPasswordFunction(display_password_callback);
Plymouth.SetDisplayNormalFunction(display_normal_callback);
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
