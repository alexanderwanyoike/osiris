"""GTK tests run headless under Xvfb, and skip where there is no GTK 4.

CI has no GTK yet; build/gtktest.py runs these in the Arch container.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

gi = pytest.importorskip("gi")
try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("GtkSource", "5")
    from gi.repository import Gtk
except ValueError, ImportError:
    pytest.skip("GTK 4 is not available", allow_module_level=True)
if not Gtk.init_check():
    pytest.skip("no display to draw on", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "harness"))


def widgets(root: Gtk.Widget) -> Iterator[Gtk.Widget]:
    """Every widget under root, depth first."""
    yield root
    child = root.get_first_child()
    while child is not None:
        yield from widgets(child)
        child = child.get_next_sibling()


def texts(root: Gtk.Widget) -> list[str]:
    return [w.get_text() for w in widgets(root) if isinstance(w, Gtk.Label)]


def now(work: Callable[[], object], done: Callable[[object], None]) -> None:
    """Background work run on the spot, so tests need no main loop."""
    done(work())


def find(root: Gtk.Widget, kind: type, text: str | None = None) -> Gtk.Widget:
    """The first widget of a kind, with a label if one is given."""
    for widget in widgets(root):
        if not isinstance(widget, kind):
            continue
        if text is None or text in (getattr(widget, "get_label", lambda: None)(),):
            return widget
    raise LookupError(f"no {kind.__name__} {text or ''} under {root}")


def shown(root: Gtk.Widget) -> list[str]:
    """Label texts a person can see: hidden widgets and everything in them skipped."""
    if not root.get_visible():
        return []
    found = [root.get_text()] if isinstance(root, Gtk.Label) else []
    child = root.get_first_child()
    while child is not None:
        found += shown(child)
        child = child.get_next_sibling()
    return found
