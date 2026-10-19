#!/usr/bin/env python3
"""Osiris theme switcher - Super+T, browse with the arrows, Enter applies.

A full-screen carousel over a blurred backdrop of the focused theme's
wallpaper: the focused theme large in the middle, its neighbours smaller and
fainter either side, sliding as you browse. Nothing is applied until Enter, so
browsing is free; Escape, or a click outside the cards, leaves things as they
were. The order is the library's (osiris/themes/library.py): favourites first,
then colour families round the wheel.

The app stays resident so the overlay opens at once. It is started at login,
or by D-Bus on first use, with --gapplication-service, and Super+T runs
`gapplication action dev.osiris.Switcher show`, which costs no Python start.
"""
import math
import os
import sys
import threading
import time
from collections import OrderedDict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("PangoCairo", "1.0")
import cairo  # noqa: E402
from gi.repository import (  # noqa: E402
    Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango, PangoCairo)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in (os.path.join(REPO, "shell", "themes"),
                  "/usr/share/osiris/themes"):
    if os.path.isdir(candidate):
        sys.path.insert(0, candidate)
        break
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

import engine  # noqa: E402

from osiris.platform import RealFileSystem  # noqa: E402
from osiris.provision.upgrade import Upgrade  # noqa: E402
from osiris.themes.carousel import offset, sequence, slot  # noqa: E402
from osiris.themes.library import arrange, family_of  # noqa: E402

APP_ID = "dev.osiris.Switcher"

# Wallpapers are decoded at this size: sharp on the centre card at 1440p, and
# a sixth of the memory of the full file. Only the cards near the focus are
# kept, so a large library does not mean a large resident app.
CARD_IMAGE = (1280, 720)
KEEP = 16
PREFETCH = 3

SLIDE_MS = 300
FADE_MS = 180
SWATCHES = ("background", "surface", "accent", "accentMuted",
            "success", "warning", "danger")

CSS = b"window.switcher { background: transparent; }"


def rgb(value: str) -> tuple[float, float, float]:
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def surface_of(pixbuf: GdkPixbuf.Pixbuf) -> cairo.ImageSurface:
    """A cairo surface of the pixbuf, converted once rather than every frame."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 pixbuf.get_width(), pixbuf.get_height())
    cr = cairo.Context(surface)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
    cr.paint()
    return surface


def blurred(pixbuf: GdkPixbuf.Pixbuf) -> cairo.ImageSurface:
    # Down to a few dozen pixels and back up is a soft, even blur for the
    # price of two scales; the backdrop is dimmed, so nothing finer shows.
    tiny = pixbuf.scale_simple(48, 27, GdkPixbuf.InterpType.BILINEAR)
    return surface_of(tiny.scale_simple(384, 216,
                                        GdkPixbuf.InterpType.BILINEAR))


def rounded(cr, x: float, y: float, w: float, h: float, r: float) -> None:
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def cover(cr, image: cairo.ImageSurface, x: float, y: float,
          w: float, h: float) -> None:
    """Paint `image` scaled to fill the rectangle, cropping what overflows."""
    scale = max(w / image.get_width(), h / image.get_height())
    cr.save()
    cr.translate(x + (w - image.get_width() * scale) / 2,
                 y + (h - image.get_height() * scale) / 2)
    cr.scale(scale, scale)
    cr.set_source_surface(image, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()


class Images:
    """Card and backdrop images for each theme, decoded on demand.

    The preview thumbnail stands in until the wallpaper has loaded, so a card
    is never blank; wallpapers load one per idle tick, nearest the focus
    first, and the least recently wanted are dropped past KEEP.
    """

    def __init__(self, on_loaded):
        self.on_loaded = on_loaded
        self.previews: dict[str, tuple] = {}
        self.wallpapers: OrderedDict[str, tuple] = OrderedDict()
        self.queue: list[dict] = []
        self.loading = False

    @staticmethod
    def _load(path: str | None, size: tuple[int, int]):
        if not path or not os.path.exists(path):
            return None
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path, size[0], size[1], True)
        except GLib.Error:
            return None
        return (os.path.getmtime(path), surface_of(pixbuf), blurred(pixbuf))

    def _fresh(self, cache, name: str, path: str | None) -> tuple | None:
        entry = cache.get(name)
        if entry is None or not path or not os.path.exists(path):
            return None
        return entry if entry[0] == os.path.getmtime(path) else None

    def get(self, theme: dict) -> tuple | None:
        """(card, backdrop) surfaces, or None if there is nothing to show."""
        name = theme["name"]
        entry = self._fresh(self.wallpapers, name, engine.wallpaper_for(theme))
        if entry is not None:
            self.wallpapers.move_to_end(name)
            return entry[1], entry[2]
        entry = self._fresh(self.previews, name, theme.get("preview"))
        if entry is None:
            entry = self._load(theme.get("preview"), (400, 250))
            if entry is None:
                return None
            self.previews[name] = entry
        return entry[1], entry[2]

    def want(self, themes: list[dict]) -> None:
        """Load these wallpapers, in this order, when the app is idle."""
        self.queue = [t for t in themes if self._fresh(
            self.wallpapers, t["name"], engine.wallpaper_for(t)) is None]
        if self.queue and not self.loading:
            self.loading = True
            GLib.idle_add(self._next, priority=GLib.PRIORITY_LOW)

    def _next(self) -> bool:
        if not self.queue:
            self.loading = False
            return False
        theme = self.queue.pop(0)
        entry = self._load(engine.wallpaper_for(theme), CARD_IMAGE)
        if entry is not None:
            self.wallpapers[theme["name"]] = entry
            self.wallpapers.move_to_end(theme["name"])
            while len(self.wallpapers) > KEEP:
                self.wallpapers.popitem(last=False)
            self.on_loaded()
        return True


class Carousel(Gtk.DrawingArea):
    """The whole overlay, drawn in one pass so every frame is consistent."""

    def __init__(self, window):
        super().__init__(hexpand=True, vexpand=True, focusable=True)
        self.window = window
        self.items: list[tuple[str, dict]] = []
        self.active: str | None = None
        self.position = 0.0
        self.target = 0.0
        self.reveal = 0.0
        self.note: tuple[str, float] | None = None
        self.pending: str | None = None
        self.images = Images(self.queue_draw)
        self.slide = Adw.TimedAnimation.new(
            self, 0, 0, SLIDE_MS, Adw.CallbackAnimationTarget.new(self._slid))
        self.slide.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        self.fade = Adw.TimedAnimation.new(
            self, 0, 1, FADE_MS, Adw.CallbackAnimationTarget.new(self._faded))
        self.fade.set_easing(Adw.Easing.EASE_OUT_QUAD)
        self.fade.connect("done", self._fade_done)
        self.set_draw_func(self._draw)

        click = Gtk.GestureClick()
        click.connect("released", self._clicked)
        self.add_controller(click)
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.BOTH_AXES
            | Gtk.EventControllerScrollFlags.DISCRETE)
        scroll.connect("scroll", self._scrolled)
        self.add_controller(scroll)

    # -- state -------------------------------------------------------------

    def load(self) -> None:
        """Read the library afresh; themes and favourites may have changed."""
        sections = arrange(engine.all_themes(), favourites=engine.favourites())
        self.items = sequence(sections)
        self.active = engine.current()
        start = next((i for i, (_, t) in enumerate(self.items)
                      if t["name"] == self.active), 0)
        self.slide.pause()
        self.position = self.target = float(start)
        self.note = None
        self._prefetch()

    def index(self) -> int:
        return round(self.target) % len(self.items) if self.items else 0

    def focused(self) -> dict | None:
        return self.items[self.index()][1] if self.items else None

    def _prefetch(self) -> None:
        if not self.items:
            return
        n, here = len(self.items), self.index()
        order = [here]
        for d in range(1, PREFETCH + 1):
            order += [(here + d) % n, (here - d) % n]
        seen: set[int] = set()
        self.images.want([self.items[i][1] for i in order
                          if not (i in seen or seen.add(i))])

    def move(self, delta: int) -> None:
        if len(self.items) < 2 or delta == 0:
            return
        self.target += delta
        self.note = None
        self.slide.pause()
        self.slide.set_value_from(self.position)
        self.slide.set_value_to(self.target)
        self.slide.play()
        self._prefetch()

    def _slid(self, value: float) -> None:
        self.position = value
        self.queue_draw()

    # -- showing and hiding ------------------------------------------------

    def open(self) -> None:
        self.fade.pause()
        self.fade.set_value_from(self.reveal)
        self.fade.set_value_to(1)
        self.fade.play()

    def close(self) -> None:
        self.fade.pause()
        self.fade.set_value_from(self.reveal)
        self.fade.set_value_to(0)
        self.fade.play()

    def _faded(self, value: float) -> None:
        self.reveal = value
        self.set_opacity(value)
        self.queue_draw()

    def _fade_done(self, _animation) -> None:
        if self.reveal == 0:
            self.window.set_visible(False)
            if self.pending:
                # Once the overlay is off screen: the switch freezes a picture
                # of the desktop to fade from, and it must not be of this.
                name, self.pending = self.pending, None
                GLib.timeout_add(120, self._start_apply, name)

    def _start_apply(self, name: str) -> bool:
        # Off the main loop, which a switch would otherwise hold for a second.
        threading.Thread(target=self._apply, args=(name,), daemon=True).start()
        return GLib.SOURCE_REMOVE

    def say(self, text: str) -> None:
        self.note = (text, time.monotonic() + 4)
        self.queue_draw()
        GLib.timeout_add(4100, self._clear_note)

    def _clear_note(self) -> bool:
        if self.note and time.monotonic() >= self.note[1]:
            self.note = None
            self.queue_draw()
        return False

    def apply(self) -> None:
        theme = self.focused()
        if theme is None:
            return
        absent = engine.missing_packages(theme)
        if absent:
            self.say(f"{theme['label']} needs {', '.join(absent)}")
            return
        if theme["name"] != self.active:
            self.pending = theme["name"]
        self.close()

    @staticmethod
    def _apply(name: str) -> None:
        try:
            engine.apply(name)
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-switcher: {name}: {error}", file=sys.stderr)

    # -- input -------------------------------------------------------------

    def _layout(self) -> tuple[float, float, float, float]:
        """Centre-card width and height, and its centre, for this size."""
        w, h = self.get_width(), self.get_height()
        cw = min(w * 0.44, h * 0.5 * 16 / 9)
        return cw, cw * 9 / 16, w / 2, h * 0.45

    def _bounds(self, index: int) -> tuple[float, float, float, float, float]:
        cw, ch, cx, cy = self._layout()
        d = offset(index, self.position, len(self.items))
        place = slot(d)
        lift = 0.94 + 0.06 * self.reveal
        w, h = cw * place.scale * lift, ch * place.scale * lift
        return cx + place.x * cw - w / 2, cy - h / 2, w, h, d

    def _clicked(self, _gesture, _n, x: float, y: float) -> None:
        hits = []
        for i in range(len(self.items)):
            bx, by, bw, bh, d = self._bounds(i)
            if abs(d) < 3 and bx <= x <= bx + bw and by <= y <= by + bh:
                hits.append(d)
        if not hits:
            self.close()
            return
        nearest = min(hits, key=abs)
        if abs(nearest) < 0.5:
            self.apply()
        else:
            self.move(round(nearest))

    def _scrolled(self, _controller, dx: float, dy: float) -> bool:
        step = dy if abs(dy) >= abs(dx) else dx
        self.move(1 if step > 0 else -1 if step < 0 else 0)
        return True

    def key(self, keyval: int) -> bool:
        name = Gdk.keyval_name(keyval) or ""
        if name in ("Right", "Down", "l", "j", "Tab", "Page_Down"):
            self.move(1)
        elif name in ("Left", "Up", "h", "k", "ISO_Left_Tab", "Page_Up"):
            self.move(-1)
        elif name == "Home" and self.items:
            self.move(-self.index())
        elif name == "End" and self.items:
            self.move(len(self.items) - 1 - self.index())
        elif name in ("Return", "KP_Enter", "space"):
            self.apply()
        elif name == "Escape":
            self.close()
        else:
            return False
        return True

    # -- drawing -----------------------------------------------------------

    def _text(self, cr, text: str, px: float, weight: Pango.Weight,
              alpha: float, cx: float, y: float, spacing: float = 0,
              colour: tuple[float, float, float] = (1, 1, 1)) -> float:
        """Centred text at `y`; returns its height."""
        layout = PangoCairo.create_layout(cr)
        desc = self.get_pango_context().get_font_description().copy()
        desc.set_absolute_size(px * Pango.SCALE)
        desc.set_weight(weight)
        layout.set_font_description(desc)
        if spacing:
            attrs = Pango.AttrList()
            attrs.insert(Pango.attr_letter_spacing_new(
                int(spacing * Pango.SCALE)))
            layout.set_attributes(attrs)
        layout.set_text(text, -1)
        width, height = layout.get_pixel_size()
        cr.move_to(cx - width / 2, y)
        cr.set_source_rgba(*colour, alpha)
        PangoCairo.show_layout(cr, layout)
        return height

    def _backdrop(self, cr, w: int, h: int) -> None:
        n = len(self.items)
        lower = math.floor(self.position)
        frac = self.position - lower
        for index, alpha in ((lower, 1.0), (lower + 1, frac)):
            if alpha <= 0 or not n:
                continue
            images = self.images.get(self.items[index % n][1])
            if images is None:
                continue
            cr.save()
            cr.push_group()
            cover(cr, images[1], 0, 0, w, h)
            cr.pop_group_to_source()
            cr.paint_with_alpha(alpha)
            cr.restore()
        cr.set_source_rgba(0.02, 0.02, 0.03, 0.52)
        cr.paint()
        vignette = cairo.RadialGradient(w / 2, h * 0.45, min(w, h) * 0.3,
                                        w / 2, h * 0.45, max(w, h) * 0.75)
        vignette.add_color_stop_rgba(0, 0, 0, 0, 0)
        vignette.add_color_stop_rgba(1, 0, 0, 0, 0.55)
        cr.set_source(vignette)
        cr.paint()

    def _card(self, cr, theme: dict, x: float, y: float, w: float, h: float,
              opacity: float, scale: float) -> None:
        radius = 18 * scale
        cr.save()
        cr.push_group()
        # A soft shadow from stacked translucent outlines; cairo has no blur.
        for i in range(8, 0, -1):
            spread = i * 3 * scale
            rounded(cr, x - spread, y - spread + 10 * scale,
                    w + spread * 2, h + spread * 2, radius + spread)
            cr.set_source_rgba(0, 0, 0, 0.035)
            cr.fill()

        cr.save()
        rounded(cr, x, y, w, h, radius)
        cr.clip()
        images = self.images.get(theme)
        if images is not None:
            cover(cr, images[0], x, y, w, h)
        else:
            cr.set_source_rgb(*rgb(theme["colors"]["background"]))
            cr.paint()
        # Neighbours dim as well as fade, so they recede rather than wash out.
        cr.set_source_rgba(0, 0, 0, (1 - opacity) * 0.45)
        cr.paint()
        cr.restore()

        rounded(cr, x + 0.5, y + 0.5, w - 1, h - 1, radius)
        cr.set_source_rgba(1, 1, 1, 0.14)
        cr.set_line_width(1)
        cr.stroke()

        self._swatches(cr, theme, x, y, w, h, scale)
        if theme["name"] == self.active:
            self._chip(cr, "Current", x + 16 * scale, y + 16 * scale, scale)

        cr.pop_group_to_source()
        cr.paint_with_alpha(min(1.0, opacity * 1.6))
        cr.restore()

    def _swatches(self, cr, theme: dict, x: float, y: float, w: float,
                  h: float, scale: float) -> None:
        colours = theme["colors"]
        r = 9 * scale
        gap = 8 * scale
        pad = 10 * scale
        width = len(SWATCHES) * 2 * r + (len(SWATCHES) - 1) * gap + 2 * pad
        px, py = x + 16 * scale, y + h - 16 * scale - 2 * r - 2 * pad
        rounded(cr, px, py, width, 2 * r + 2 * pad, r + pad)
        cr.set_source_rgba(0, 0, 0, 0.38)
        cr.fill()
        for i, key in enumerate(SWATCHES):
            cx = px + pad + r + i * (2 * r + gap)
            cy = py + pad + r
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.set_source_rgb(*rgb(colours[key]))
            cr.fill_preserve()
            cr.set_source_rgba(1, 1, 1, 0.28)
            cr.set_line_width(max(1, 1.2 * scale))
            cr.stroke()

    def _chip(self, cr, text: str, x: float, y: float, scale: float) -> None:
        layout = PangoCairo.create_layout(cr)
        desc = self.get_pango_context().get_font_description().copy()
        desc.set_absolute_size(13 * scale * Pango.SCALE)
        desc.set_weight(Pango.Weight.BOLD)
        layout.set_font_description(desc)
        layout.set_text(text, -1)
        tw, th = layout.get_pixel_size()
        padx, pady = 12 * scale, 5 * scale
        rounded(cr, x, y, tw + 2 * padx, th + 2 * pady, (th + 2 * pady) / 2)
        cr.set_source_rgba(1, 1, 1, 0.92)
        cr.fill()
        cr.move_to(x + padx, y + pady)
        cr.set_source_rgba(0.05, 0.05, 0.07, 1)
        PangoCairo.show_layout(cr, layout)

    def _draw(self, _area, cr, w: int, h: int) -> None:
        self._backdrop(cr, w, h)
        n = len(self.items)
        cw, ch, cx, cy = self._layout()
        if not n:
            self._text(cr, "No themes", 28, Pango.Weight.BOLD, 0.9, cx, cy)
            return

        visible = []
        for i in range(n):
            d = offset(i, self.position, n)
            if abs(d) < 3:
                visible.append((abs(d), i))
        for _, i in sorted(visible, reverse=True):
            bx, by, bw, bh, d = self._bounds(i)
            place = slot(d)
            self._card(cr, self.items[i][1], bx, by, bw, bh,
                       place.opacity, place.scale)

        # Labels belong to the nearest card and fade out as it slides away.
        nearest = round(self.position)
        alpha = max(0.0, 1 - abs(self.position - nearest) * 2.5)
        section, theme = self.items[nearest % n]
        top = cy - ch / 2 - 44
        self._text(cr, section.upper(), 12, Pango.Weight.BOLD, 0.6 * alpha,
                   cx, top, spacing=2.4)
        y = cy + ch / 2 + 30
        y += self._text(cr, theme["label"], 30, Pango.Weight.BOLD, alpha,
                        cx, y) + 6
        if self.note:
            self._text(cr, self.note[0], 14, Pango.Weight.SEMIBOLD, 1, cx, y,
                       colour=rgb(theme["colors"]["warning"]))
        else:
            mode = "Dark" if theme.get("dark", True) else "Light"
            detail = (f"{family_of(theme).value}  ·  {mode}  ·  "
                      f"{nearest % n + 1} of {n}")
            self._text(cr, detail, 14, Pango.Weight.NORMAL, 0.62 * alpha,
                       cx, y)
        self._hints(cr, w, h)

    def _hints(self, cr, w: int, h: int) -> None:
        hints = (("← →", "browse"), ("Enter", "apply"),
                 ("Esc", "close"))
        layouts = []
        for key, label in hints:
            parts = []
            for text, weight, px in ((key, Pango.Weight.BOLD, 12),
                                     (label, Pango.Weight.NORMAL, 13)):
                layout = PangoCairo.create_layout(cr)
                desc = self.get_pango_context().get_font_description().copy()
                desc.set_absolute_size(px * Pango.SCALE)
                desc.set_weight(weight)
                layout.set_font_description(desc)
                layout.set_text(text, -1)
                parts.append(layout)
            layouts.append(parts)
        pad, inner, between = 8, 8, 28
        total = sum(k.get_pixel_size()[0] + 2 * pad + inner
                    + v.get_pixel_size()[0] for k, v in layouts)
        total += between * (len(layouts) - 1)
        x, y = (w - total) / 2, h - 56
        for key, label in layouts:
            kw, kh = key.get_pixel_size()
            rounded(cr, x, y - 4, kw + 2 * pad, kh + 8, 6)
            cr.set_source_rgba(1, 1, 1, 0.12)
            cr.fill()
            cr.move_to(x + pad, y)
            cr.set_source_rgba(1, 1, 1, 0.85)
            PangoCairo.show_layout(cr, key)
            x += kw + 2 * pad + inner
            lw, lh = label.get_pixel_size()
            cr.move_to(x, y + (kh - lh) / 2)
            cr.set_source_rgba(1, 1, 1, 0.55)
            PangoCairo.show_layout(cr, label)
            x += lw + between


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Themes", decorated=False)
        self.add_css_class("switcher")
        self.carousel = Carousel(self)
        self.set_child(self.carousel)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed",
                     lambda _c, keyval, _code, _state: self.carousel.key(keyval))
        self.add_controller(keys)
        self.connect("close-request", self._close_request)

    def _close_request(self, _window) -> bool:
        self.carousel.close()
        return True

    def show_switcher(self) -> None:
        if self.get_visible() and self.carousel.reveal > 0:
            # Super+T again while open steps on, the way Alt+Tab does.
            self.carousel.move(1)
            return
        self.carousel.load()
        self.fullscreen()
        self.present()
        self.carousel.grab_focus()
        self.carousel.open()


#: Seconds between looks at whether Osiris was upgraded under the Switcher.
UPGRADE_POLL = 10


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window: Window | None = None
        self.upgrade = Upgrade(RealFileSystem())
        show = Gio.SimpleAction.new("show", None)
        show.connect("activate", lambda *_: self.show_switcher())
        self.add_action(show)

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Resident: closing the overlay hides it, and the process waits for
        # the next Super+T with its images already decoded.
        self.hold()
        display = Gdk.Display.get_default()
        if display is not None:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Window(self)
        # Warm the cards around the current theme before anyone asks.
        self.window.carousel.load()
        GLib.timeout_add_seconds(UPGRADE_POLL, self._restart_if_upgraded)

    def _restart_if_upgraded(self) -> bool:
        """Quit once Osiris is upgraded under it and the overlay is put away;
        D-Bus starts the new code on the next Super+T."""
        in_use = self.window is not None and self.window.get_visible()
        if not self.upgrade.restart_due(in_use=in_use):
            return GLib.SOURCE_CONTINUE
        self.quit()
        return GLib.SOURCE_REMOVE

    def do_activate(self):
        self.show_switcher()

    def show_switcher(self) -> None:
        if self.window is not None:
            self.window.show_switcher()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
