"""The applications Osiris names as defaults for the whole system."""

from __future__ import annotations

import configparser

from osiris.provision import default_apps


def test_chromium_opens_links_and_web_pages() -> None:
    parser = configparser.ConfigParser(delimiters=("=",))
    parser.read_string(default_apps.MIMEAPPS)
    defaults = parser["Default Applications"]
    for kind in ("x-scheme-handler/http", "x-scheme-handler/https", "text/html"):
        assert defaults[kind] == "chromium.desktop"
