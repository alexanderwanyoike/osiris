"""The model menu under the message box (#222): a search over the models the
person's accounts reach, each with its maker's icon, the Providers pinned
below. What it lists, in what order, and whose icon each wears is decided in
osiris/harness/model_menu.py; this draws it."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk, Pango  # noqa: E402
from badge import badge  # noqa: E402
from list_moves import move  # noqa: E402

from osiris.harness.accounts import ModelInfo  # noqa: E402
from osiris.harness.engine import ModelRef  # noqa: E402
from osiris.harness.model_menu import in_menu_order, maker_of, narrowed  # noqa: E402

#: Rows shown before the list scrolls.
ROWS = 8
MOVES = {Gdk.KEY_Down: 1, Gdk.KEY_Up: -1}
CHOOSES = (Gdk.KEY_Return, Gdk.KEY_KP_Enter)
#: The makers' icons Osiris ships (apps/harness/logos, NOTICE there). Xiaomi's
#: only mark in lobe-icons is a wordmark, unreadable at this size, so MiMo
#: gets a monogram.
ICONS = {
    "openai": "osiris-provider-openai-symbolic",
    "nvidia": "osiris-maker-nvidia-symbolic",
    "deepseek": "osiris-maker-deepseek-symbolic",
    "zhipu": "osiris-maker-zhipu-symbolic",
}


def _lead(info: ModelInfo) -> Gtk.Widget:
    return badge(ICONS.get(maker_of(info.family) or ""), info.name, 16)


class ModelMenu(Gtk.Box):
    def __init__(self, *, on_chosen: Callable[[ModelRef], None],
                 on_providers: Callable[[], None], on_close: Callable[[], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._on_chosen = on_chosen
        self._on_providers = on_providers
        self._on_close = on_close
        self._models: list[ModelInfo] = []
        self._providers: dict[str, str] = {}
        self.search = Gtk.SearchEntry(placeholder_text="Search models")
        self.search.connect("changed", lambda _e: self._narrow())
        # Captured before the search's own Escape, which only clears it.
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.key)
        self.search.add_controller(keys)
        self.append(self.search)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.list.add_css_class("navigation-sidebar")
        self.list.connect("row-activated", lambda _l, row: self._on_chosen(row.model.ref))
        # The chosen row follows the pointer, so only one row is ever lit.
        pointer = Gtk.EventControllerMotion()
        pointer.connect("motion", self._pointed)
        self.list.add_controller(pointer)
        self.card = Gtk.ScrolledWindow(child=self.list, propagate_natural_height=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(self.card)
        self.providers = Gtk.Button(
            child=Gtk.Label(label="Providers and accounts…", xalign=0))
        self.providers.add_css_class("flat")
        self.providers.connect("clicked", lambda _b: self._on_providers())
        self.append(self.providers)

    def show_models(self, models: list[ModelInfo], in_use: ModelRef | None,
                    providers: dict[str, str]) -> None:
        """The models in the menu's order; ``providers`` names each by id."""
        self._models = in_menu_order(models, in_use)
        self._providers = providers
        self._narrow()

    def _narrow(self) -> None:
        self.list.remove_all()
        for info in narrowed(self._models, self.search.get_text(), self._providers):
            row = Gtk.ListBoxRow(child=self._row(info))
            row.model = info
            self.list.append(row)
        first = self.list.get_row_at_index(0)
        self.list.select_row(first)
        if first is not None:
            # As tall as the Skin draws a row, so it is rows that show.
            one = first.measure(Gtk.Orientation.VERTICAL, -1)[1]
            self.card.set_max_content_height(ROWS * one)

    def _row(self, info: ModelInfo) -> Gtk.Widget:
        box = Gtk.Box(spacing=8)
        box.append(_lead(info))
        box.append(Gtk.Label(label=info.name, xalign=0, hexpand=True,
                             ellipsize=Pango.EllipsizeMode.END))
        provider = Gtk.Label(
            label=self._providers.get(info.ref.provider, info.ref.provider))
        provider.add_css_class("dim-label")
        box.append(provider)
        return box

    def key(self, _controller, keyval, _code, _state) -> bool:
        row = self.list.get_selected_row()
        if keyval in MOVES and row is not None:
            move(self.list, self.card, MOVES[keyval])
            return True
        if keyval in CHOOSES and row is not None:
            self._on_chosen(row.model.ref)
            return True
        if keyval == Gdk.KEY_Escape:
            self._on_close()
            return True
        return False

    def _pointed(self, _controller, _x: float, y: float) -> None:
        row = self.list.get_row_at_y(int(y))
        if row is not None and row is not self.list.get_selected_row():
            self.list.select_row(row)
