"""Answers parsed into blocks the drawer draws, with inline text as Pango markup."""

from __future__ import annotations

import pytest

from osiris.harness.markdown import (
    PAD,
    Code,
    Heading,
    InlineStyle,
    ListBlock,
    ListItem,
    Paragraph,
    Quote,
    Rule,
    Table,
    parse,
    unchanged_prefix,
)

STYLE = InlineStyle(code_foreground="#e8e8e8", code_background="#2a2a2f")
CODE = '<span font_family="monospace" foreground="#e8e8e8" background="#2a2a2f">'


def only(text: str) -> object:
    (block,) = parse(text, STYLE)
    return block


class TestInline:
    def test_emphasis_becomes_pango_markup(self) -> None:
        assert only("a **b** *c* ~~d~~") == Paragraph("a <b>b</b> <i>c</i> <s>d</s>")

    def test_inline_code_is_monospace_on_its_own_background(self) -> None:
        assert only("run `ls -la` now") == Paragraph(
            f"run {CODE}{PAD}ls -la{PAD}</span> now"
        )

    def test_text_is_escaped_so_markup_in_an_answer_cannot_break_the_view(
        self,
    ) -> None:
        assert only("1 < 2 & 3 > 0") == Paragraph("1 &lt; 2 &amp; 3 &gt; 0")

    def test_html_in_an_answer_is_shown_not_interpreted(self) -> None:
        assert only("<b>loud</b>") == Paragraph("&lt;b&gt;loud&lt;/b&gt;")

    def test_a_line_break_inside_a_paragraph_is_a_space(self) -> None:
        assert only("one line\nand the next") == Paragraph("one line and the next")

    @pytest.mark.parametrize("ending", ["  \n", "\\\n"])
    def test_a_hard_break_stays_a_new_line(self, ending: str) -> None:
        assert only(f"one line{ending}and the next") == Paragraph(
            "one line\nand the next"
        )

    def test_code_is_escaped_too(self) -> None:
        assert only("`a<b>`") == Paragraph(f"{CODE}{PAD}a&lt;b&gt;{PAD}</span>")

    def test_web_links_are_links(self) -> None:
        assert only("[docs](https://wiki.archlinux.org/)") == Paragraph(
            '<a href="https://wiki.archlinux.org/">docs</a>'
        )

    @pytest.mark.parametrize(
        "target", ["file:///etc/shadow", "javascript:alert(1)", "/etc/passwd"]
    )
    def test_links_that_are_not_web_or_mail_are_only_text(self, target: str) -> None:
        block = only(f"[here]({target})")
        assert isinstance(block, Paragraph)
        assert "<a" not in block.markup
        assert "here" in block.markup

    def test_a_quote_in_a_link_cannot_escape_its_attribute(self) -> None:
        assert only('[x](https://a.org/"onclick)') == Paragraph(
            '<a href="https://a.org/%22onclick">x</a>'
        )


class TestBlocks:
    def test_headings_keep_their_level(self) -> None:
        assert parse("# One\n\n### Three", STYLE) == [
            Heading(1, "One"),
            Heading(3, "Three"),
        ]

    def test_a_fenced_block_is_code_with_its_language(self) -> None:
        assert only("```bash\nls -la\necho hi\n```") == Code("bash", "ls -la\necho hi")

    def test_a_fence_without_a_language_is_plain_code(self) -> None:
        assert only("```\nplain\n```") == Code(None, "plain")

    def test_an_unclosed_fence_is_code_so_far_while_it_streams(self) -> None:
        assert only("```python\nprint(") == Code("python", "print(")

    def test_bullets_and_numbers(self) -> None:
        assert only("- a\n- **b**") == ListBlock(
            (ListItem(0, "•", "a"), ListItem(0, "•", "<b>b</b>"))
        )
        assert only("3. c\n4. d") == ListBlock(
            (ListItem(0, "3.", "c"), ListItem(0, "4.", "d"))
        )

    def test_nested_lists_are_indented(self) -> None:
        assert only("- a\n  - b\n- c") == ListBlock(
            (ListItem(0, "•", "a"), ListItem(1, "◦", "b"), ListItem(0, "•", "c"))
        )

    def test_a_quote(self) -> None:
        assert only("> careful *now*") == Quote("careful <i>now</i>")

    def test_a_table(self) -> None:
        assert only("| Package | Size |\n|---|---:|\n| gimp | 210 MB |") == Table(
            ("Package", "Size"), (("gimp", "210 MB"),)
        )

    def test_a_rule(self) -> None:
        assert parse("a\n\n---\n\nb", STYLE) == [Paragraph("a"), Rule(), Paragraph("b")]


class TestStreaming:
    def test_finished_blocks_are_kept_and_only_the_growing_one_redrawn(self) -> None:
        before = parse("# Title\n\nFirst para", STYLE)
        after = parse("# Title\n\nFirst paragraph is longer", STYLE)
        assert unchanged_prefix(before, after) == 1

    def test_identical_answers_need_nothing_redrawn(self) -> None:
        blocks = parse("a\n\nb", STYLE)
        assert unchanged_prefix(blocks, list(blocks)) == 2
