"""What the browser group's address line makes of what is typed (#197): an
address kept, a site given https, anything else searched for."""

from __future__ import annotations

from urllib.parse import urlencode

#: Where words typed in the address line are searched for.
SEARCH = "https://duckduckgo.com/?"


def address(typed: str) -> str:
    text = typed.strip()
    if "://" in text:
        return text
    if " " not in text and text.startswith("localhost"):
        return f"http://{text}"
    if " " not in text and "." in text:
        return f"https://{text}"
    return SEARCH + urlencode({"q": text})
