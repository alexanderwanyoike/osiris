"""FAL in the real Settings page, down to the file the tool server reads."""

from __future__ import annotations

from osiris.harness.media.key import fal_key
from osiris.harness.media.limit_setting import daily_limit
from tests.gtk.conftest import now, texts
from tests.gtk.test_providers_page import FakeAccounts
from tests.test_harness import HOME

from .test_drawer import drawer
from .test_side_by_side import app


def test_the_app_keeps_the_key_where_the_tool_server_reads_it() -> None:
    stand_in, _engine = app()

    stand_in.save_fal_key("a-key")

    assert stand_in.fal_connected()
    assert fal_key(stand_in.files, HOME) == "a-key"

    stand_in.remove_fal_key()

    assert not stand_in.fal_connected()


def test_the_app_keeps_the_limit_where_the_tool_server_reads_it() -> None:
    stand_in, _engine = app()
    assert stand_in.picture_limit() is None

    stand_in.set_picture_limit(30)
    assert daily_limit(stand_in.files, HOME) == 30

    stand_in.set_picture_limit(None)
    assert daily_limit(stand_in.files, HOME) is None


def test_settings_shows_the_media_section() -> None:
    window, _ = drawer()
    settings = window.app
    settings.accounts = FakeAccounts()
    settings.background = now
    settings.open_page = lambda _url: None
    settings.choose_model = lambda _model: None
    settings.set_auto_mode = lambda _on: None

    window.show_providers()

    assert "FAL" in texts(window)
