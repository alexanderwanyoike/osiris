"""Answers parsed into blocks, each drawn by its own widget in the drawer.

Inline text becomes Pango markup. Everything from the model is escaped first,
so markup or HTML in an answer is shown as text, never interpreted, and only
web and mail links become clickable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

from markdown_it import MarkdownIt
from markdown_it.token import Token

LINK_SCHEMES = ("https://", "http://", "mailto:")
BULLETS = ("•", "◦", "▪")
# Thin spaces stand in for padding, which Pango spans do not have.
PAD = chr(0x2009)
# Characters a URL may carry as they are; anything else is percent-encoded,
# so nothing in a link can close the attribute it sits in.
URL_SAFE = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    ":/?#[]@!$&'()*+,;=%-._~"
)


@dataclass(frozen=True)
class InlineStyle:
    """Colours Pango needs inline; everything else is the Skin's CSS."""

    code_foreground: str
    code_background: str


@dataclass(frozen=True)
class Heading:
    level: int
    markup: str


@dataclass(frozen=True)
class Paragraph:
    markup: str


@dataclass(frozen=True)
class Code:
    language: str | None
    source: str


@dataclass(frozen=True)
class ListItem:
    depth: int
    marker: str
    markup: str


@dataclass(frozen=True)
class ListBlock:
    items: tuple[ListItem, ...]


@dataclass(frozen=True)
class Quote:
    markup: str


@dataclass(frozen=True)
class Table:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Rule:
    pass


Block = Heading | Paragraph | Code | ListBlock | Quote | Table | Rule

_PARSER = (
    MarkdownIt("commonmark", {"html": False}).enable("table").enable("strikethrough")
)

_OPEN = {"strong_open": "<b>", "em_open": "<i>", "s_open": "<s>"}
_CLOSE = {"strong_close": "</b>", "em_close": "</i>", "s_close": "</s>"}


def _quote(url: str) -> str:
    return "".join(
        chr(byte) if chr(byte) in URL_SAFE else f"%{byte:02X}" for byte in url.encode()
    )


#: CommonMark: a line break in the source is a space, the drawer rewrapping the
#: paragraph to its own width; only an explicit break starts a new line.
_BREAKS = {"softbreak": " ", "hardbreak": "\n"}


def _inline(tokens: Sequence[Token], style: InlineStyle) -> str:
    out: list[str] = []
    linking: list[bool] = []
    for token in tokens:
        if token.type in ("text", "html_inline"):
            out.append(escape(token.content, quote=False))
        elif token.type in _BREAKS:
            out.append(_BREAKS[token.type])
        elif token.type == "code_inline":
            out.append(
                f'<span font_family="monospace" '
                f'foreground="{style.code_foreground}" '
                f'background="{style.code_background}">'
                f"{PAD}{escape(token.content, quote=False)}{PAD}</span>"
            )
        elif token.type in _OPEN:
            out.append(_OPEN[token.type])
        elif token.type in _CLOSE:
            out.append(_CLOSE[token.type])
        elif token.type == "link_open":
            href = str(token.attrs.get("href", ""))
            allowed = href.startswith(LINK_SCHEMES)
            linking.append(allowed)
            if allowed:
                out.append(f'<a href="{escape(_quote(href))}">')
        elif token.type == "link_close" and linking.pop():
            out.append("</a>")
    return "".join(out)


def _markup(token: Token, style: InlineStyle) -> str:
    return _inline(token.children or [], style)


def parse(text: str, style: InlineStyle) -> list[Block]:  # noqa: C901
    tokens = _PARSER.parse(text)
    blocks: list[Block] = []
    lists: list[list[int]] = []
    items: list[ListItem] = []
    quoting = 0
    quote_parts: list[str] = []
    row: list[str] = []
    header: tuple[str, ...] = ()
    rows: list[tuple[str, ...]] = []
    in_head = False

    for index, token in enumerate(tokens):
        kind = token.type
        if kind == "heading_open":
            level = int(token.tag[1])
            blocks.append(Heading(level, _markup(tokens[index + 1], style)))
        elif kind in ("fence", "code_block"):
            language = token.info.strip().split(" ")[0] or None
            blocks.append(Code(language, token.content.rstrip("\n")))
        elif kind == "hr":
            blocks.append(Rule())
        elif kind == "blockquote_open":
            quoting += 1
        elif kind == "blockquote_close":
            quoting -= 1
            if quoting == 0:
                blocks.append(Quote("\n".join(quote_parts)))
                quote_parts = []
        elif kind in ("bullet_list_open", "ordered_list_open"):
            start = int(token.attrs.get("start", 1)) if token.attrs else 1
            lists.append([0 if kind == "bullet_list_open" else 1, start])
        elif kind in ("bullet_list_close", "ordered_list_close"):
            lists.pop()
            if not lists:
                blocks.append(ListBlock(tuple(items)))
                items = []
        elif kind == "list_item_open":
            depth = len(lists) - 1
            ordered, number = lists[-1]
            marker = f"{number}." if ordered else BULLETS[min(depth, 2)]
            if ordered:
                lists[-1][1] += 1
            items.append(ListItem(depth, marker, ""))
        elif kind == "thead_open":
            in_head = True
        elif kind == "thead_close":
            in_head = False
        elif kind == "tr_close":
            if in_head:
                header = tuple(row)
            else:
                rows.append(tuple(row))
            row = []
        elif kind in ("th_open", "td_open"):
            row.append(_markup(tokens[index + 1], style))
        elif kind == "table_close":
            blocks.append(Table(header, tuple(rows)))
            header, rows = (), []
        elif kind == "inline" and tokens[index - 1].type == "paragraph_open":
            markup = _markup(token, style)
            if lists and items and not items[-1].markup:
                items[-1] = ListItem(items[-1].depth, items[-1].marker, markup)
            elif quoting:
                quote_parts.append(markup)
            elif not lists:
                blocks.append(Paragraph(markup))
    return blocks


def unchanged_prefix(before: Sequence[Block], after: Sequence[Block]) -> int:
    """How many leading blocks a redraw can keep as they are."""
    count = 0
    for old, new in zip(before, after, strict=False):
        if old != new:
            break
        count += 1
    return count
