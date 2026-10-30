"""The switcher's overlay: a ring of cards over a blurred backdrop.

What the cards are, and what choosing one does, is the deck's
(osiris/apps/decks.py); this draws them and takes the keys.
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
    Adw, Gdk, GdkPixbuf, GLib, Gtk, Pango, PangoCairo)

from osiris.apps.decks import Card  # noqa: E402
from osiris.themes.carousel import offset, slot  # noqa: E402

# Wallpapers are decoded at this size: sharp on the centre card at 1440p, and
# a sixth of the memory of the full file. Only the cards near the focus are
# kept, so a large library does not mean a large resident app.
CARD_IMAGE = (1280, 720)
KEEP = 16
PREFETCH = 3

SLIDE_MS = 300
FADE_MS = 180


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
    """Card and backdrop images, decoded on demand.

    A card names its images best first. The first is decoded at card size
    one per idle tick, nearest the focus first, and the least recently wanted
    are dropped past KEEP; until then a later, smaller one stands in, so a
    card is never blank for want of a wallpaper.
    """

    def __init__(self, on_loaded):
        self.on_loaded = on_loaded
        self.previews: dict[str, tuple] = {}
        self.large: OrderedDict[str, tuple] = OrderedDict()
        self.queue: list[str] = []
        self.loading = False

    @staticmethod
    def _load(path: str, size: tuple[int, int]):
        if not os.path.exists(path):
            return None
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path, size[0], size[1], True)
        except GLib.Error:
            return None
        return (os.path.getmtime(path), surface_of(pixbuf), blurred(pixbuf))

    @staticmethod
    def _fresh(cache, path: str) -> tuple | None:
        entry = cache.get(path)
        if entry is None or not os.path.exists(path):
            return None
        return entry if entry[0] == os.path.getmtime(path) else None

    def get(self, paths: tuple[str, ...]) -> tuple | None:
        """(card, backdrop) surfaces, or None if there is nothing to show."""
        if not paths:
            return None
        entry = self._fresh(self.large, paths[0])
        if entry is not None:
            self.large.move_to_end(paths[0])
            return entry[1], entry[2]
        for path in paths[1:]:
            entry = self._fresh(self.previews, path)
            if entry is None:
                entry = self._load(path, (400, 250))
                if entry is None:
                    continue
                self.previews[path] = entry
            return entry[1], entry[2]
        return None

    def want(self, wanted: list[tuple[str, ...]]) -> None:
        """Load the best of each, in this order, when the app is idle."""
        self.queue = [path for path in dict.fromkeys(p[0] for p in wanted if p)
                      if self._fresh(self.large, path) is None]
        if self.queue and not self.loading:
            self.loading = True
            GLib.idle_add(self._next, priority=GLib.PRIORITY_LOW)

    def _next(self) -> bool:
        if not self.queue:
            self.loading = False
            return False
        path = self.queue.pop(0)
        entry = self._load(path, CARD_IMAGE)
        if entry is not None:
            self.large[path] = entry
            self.large.move_to_end(path)
            while len(self.large) > KEEP:
                self.large.popitem(last=False)
            self.on_loaded()
        return True


class Carousel(Gtk.DrawingArea):
    """The whole overlay, drawn in one pass so every frame is consistent."""

    def __init__(self, window, deck):
        super().__init__(hexpand=True, vexpand=True, focusable=True)
        self.window = window
        self.deck = deck
        self.items: list[Card] = []
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
        """Read the deck afresh; what it holds may have changed."""
        self.items = self.deck.cards()
        self.active = self.deck.active()
        start = next((i for i, card in enumerate(self.items)
                      if card.name == self.active), 0)
        self.slide.pause()
        self.position = self.target = float(start)
        self.note = None
        self._prefetch()

    def index(self) -> int:
        return round(self.target) % len(self.items) if self.items else 0

    def focused(self) -> Card | None:
        return self.items[self.index()] if self.items else None

    def _prefetch(self) -> None:
        if not self.items:
            return
        n, here = len(self.items), self.index()
        order = [here]
        for d in range(1, PREFETCH + 1):
            order += [(here + d) % n, (here - d) % n]
        seen: set[int] = set()
        wanted = [self.items[i].pictures for i in order
                  if not (i in seen or seen.add(i))]
        self.images.want([self.items[here].backdrop, *wanted])

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
        card = self.focused()
        if card is None:
            return
        refused = self.deck.refused(card)
        if refused:
            self.say(refused)
            return
        if card.name != self.active:
            self.pending = card.name
        self.close()

    def _apply(self, name: str) -> None:
        try:
            self.deck.choose(name)
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-switcher: {name}: {error}", file=sys.stderr)

    # -- input -------------------------------------------------------------

    def _layout(self) -> tuple[float, float, float, float]:
        """Centre-card width and height, and its centre, for this size."""
        w, h = self.get_width(), self.get_height()
        aspect = self.deck.aspect
        cw = min(w * 0.44, h * 0.5 * aspect)
        return cw, cw / aspect, w / 2, h * 0.45

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
            images = self.images.get(self.items[index % n].backdrop)
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

    def _card(self, cr, card: Card, x: float, y: float, w: float, h: float,
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
        images = self.images.get(card.pictures)
        if images is not None:
            cover(cr, images[0], x, y, w, h)
        else:
            cr.set_source_rgb(*rgb(card.fill))
            cr.paint()
        # Neighbours dim as well as fade, so they recede rather than wash out.
        cr.set_source_rgba(0, 0, 0, (1 - opacity) * 0.45)
        cr.paint()
        cr.restore()

        rounded(cr, x + 0.5, y + 0.5, w - 1, h - 1, radius)
        cr.set_source_rgba(1, 1, 1, 0.14)
        cr.set_line_width(1)
        cr.stroke()

        if card.swatches:
            self._swatches(cr, card.swatches, x, y, w, h, scale)
        if card.name == self.active:
            self._chip(cr, "Current", x + 16 * scale, y + 16 * scale, scale)

        cr.pop_group_to_source()
        cr.paint_with_alpha(min(1.0, opacity * 1.6))
        cr.restore()

    def _swatches(self, cr, colours: tuple[str, ...], x: float, y: float,
                  w: float, h: float, scale: float) -> None:
        r = 9 * scale
        gap = 8 * scale
        pad = 10 * scale
        width = len(colours) * 2 * r + (len(colours) - 1) * gap + 2 * pad
        px, py = x + 16 * scale, y + h - 16 * scale - 2 * r - 2 * pad
        rounded(cr, px, py, width, 2 * r + 2 * pad, r + pad)
        cr.set_source_rgba(0, 0, 0, 0.38)
        cr.fill()
        for i, colour in enumerate(colours):
            cx = px + pad + r + i * (2 * r + gap)
            cy = py + pad + r
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.set_source_rgb(*rgb(colour))
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
            self._text(cr, "Nothing to choose from", 28, Pango.Weight.BOLD,
                       0.9, cx, cy)
            return

        visible = []
        for i in range(n):
            d = offset(i, self.position, n)
            if abs(d) < 3:
                visible.append((abs(d), i))
        for _, i in sorted(visible, reverse=True):
            bx, by, bw, bh, d = self._bounds(i)
            place = slot(d)
            self._card(cr, self.items[i], bx, by, bw, bh,
                       place.opacity, place.scale)

        # Labels belong to the nearest card and fade out as it slides away.
        nearest = round(self.position)
        alpha = max(0.0, 1 - abs(self.position - nearest) * 2.5)
        card = self.items[nearest % n]
        top = cy - ch / 2 - 44
        self._text(cr, card.section.upper(), 12, Pango.Weight.BOLD,
                   0.6 * alpha, cx, top, spacing=2.4)
        y = cy + ch / 2 + 30
        y += self._text(cr, card.label, 30, Pango.Weight.BOLD, alpha,
                        cx, y) + 6
        if self.note:
            self._text(cr, self.note[0], 14, Pango.Weight.SEMIBOLD, 1, cx, y,
                       colour=rgb(card.warning))
        else:
            detail = f"{card.detail}  ·  {nearest % n + 1} of {n}"
            self._text(cr, detail, 14, Pango.Weight.NORMAL, 0.62 * alpha,
                       cx, y)
        self._hints(cr, w, h)

    def _hints(self, cr, w: int, h: int) -> None:
        hints = (("← →", "browse"), ("Enter", self.deck.verb),
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
    def __init__(self, app, deck):
        super().__init__(application=app, title="Themes", decorated=False)
        self.add_css_class("switcher")
        self.carousel = Carousel(self, deck)
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
