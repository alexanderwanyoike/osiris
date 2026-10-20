"""The slides the install page shows while archinstall runs.

What the slides are is data, in slides/slides.json (ADR 0004); this only
draws them.
"""
import json
import os

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

SLIDES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slides")


class Slideshow(Gtk.Stack):
    """Each slide in slides.json: its picture over its sentence."""

    def __init__(self, folder=SLIDES):
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE,
                         transition_duration=800)
        with open(os.path.join(folder, "slides.json")) as fh:
            for slide in json.load(fh):
                self.add_child(self.slide(folder, slide))

    def advance(self) -> None:
        """The next slide, or the first after the last."""
        following = self.get_visible_child().get_next_sibling()
        self.set_visible_child(following or self.get_first_child())

    @staticmethod
    def slide(folder, slide) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        picture = Gtk.Picture.new_for_filename(
            os.path.join(folder, slide["image"]))
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        picture.set_overflow(Gtk.Overflow.HIDDEN)
        picture.add_css_class("slide")
        box.append(picture)
        caption = Gtk.Label(label=slide["caption"], wrap=True,
                            justify=Gtk.Justification.CENTER)
        caption.add_css_class("title-4")
        box.append(caption)
        return box
