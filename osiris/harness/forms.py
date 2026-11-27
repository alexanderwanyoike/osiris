"""The reply to a form, from what the person picked and typed on its card."""

from __future__ import annotations

from collections.abc import Mapping

from osiris.harness.engine import FormAnswer, FormAsked


def reply(
    form: FormAsked,
    picked: Mapping[str, tuple[str, ...]],
    typed: Mapping[str, str],
) -> dict[str, FormAnswer]:
    """Each question's answer, by its key. What was typed wins over what was
    picked; a question left unanswered is left out, which opencode tells the
    model as unanswered."""
    answers: dict[str, FormAnswer] = {}
    for field in form.fields:
        text = typed.get(field.key, "").strip()
        chosen = picked.get(field.key, ())
        answer = (
            (text or chosen) if field.multiple else (text or next(iter(chosen), ""))
        )
        if answer:
            answers[field.key] = answer
    return answers
