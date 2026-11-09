"""The model menu under the message box (#222): a search over the models the
person's accounts reach, each with its maker's icon, the Providers pinned
below. What it lists, in what order, and whose icon each wears is decided in
osiris/harness/model_menu.py; this draws it."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from osiris.harness.accounts import ModelInfo  # noqa: E402
from osiris.harness.engine import ModelRef  # noqa: E402
from osiris.harness.model_menu import in_menu_order, narrowed  # noqa: E402

#: Rows shown before the list scrolls.
ROWS = 8


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
        self.append(self.search)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.list.add_css_class("navigation-sidebar")
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
            row = Gtk.ListBoxRow(child=Gtk.Label(label=info.name, xalign=0))
            row.model = info
            self.list.append(row)
        first = self.list.get_row_at_index(0)
        if first is not None:
            # As tall as the Skin draws a row, so it is rows that show.
            one = first.measure(Gtk.Orientation.VERTICAL, -1)[1]
            self.card.set_max_content_height(ROWS * one)
