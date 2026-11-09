"""What the model menu lists, in what order, and whose icon each model wears
(#222). The menu in apps/harness only draws it."""

from __future__ import annotations

#: Each maker by the families of models it makes, as the Engine names them.
#: A family is a maker's when it is the prefix or starts with it and a dash.
MAKERS = {
    "gpt": "openai",
    "nemotron": "nvidia",
    "deepseek": "deepseek",
    "glm": "zhipu",
    "mimo": "xiaomi",
}


def maker_of(family: str) -> str | None:
    """The maker of a family of models, or None where it is not known."""
    return next(
        (
            maker
            for prefix, maker in MAKERS.items()
            if family == prefix or family.startswith(f"{prefix}-")
        ),
        None,
    )
