"""The applications Osiris names as the system's defaults, in /etc/xdg/mimeapps.list.

Without a named default, GLib and xdg-utils pick whichever installed app last
registered for a type, so a Program or a second browser could quietly take over
links. The system file is consulted only after the person's own
~/.config/mimeapps.list, so a browser they choose in Preferred Applications or
with xdg-settings still wins and no upgrade overwrites it.
"""

from __future__ import annotations

BROWSER = "chromium.desktop"

#: The types xdg-settings sets for default-web-browser, plus XHTML pages.
_BROWSER_TYPES = (
    "x-scheme-handler/http",
    "x-scheme-handler/https",
    "x-scheme-handler/about",
    "x-scheme-handler/unknown",
    "text/html",
    "application/xhtml+xml",
)

MIMEAPPS = "[Default Applications]\n" + "".join(
    f"{kind}={BROWSER}\n" for kind in _BROWSER_TYPES
)
