"""What the model menu lists, in what order, and whose icon each model wears
(#222). The menu in apps/harness only draws it."""

from __future__ import annotations

from osiris.harness.accounts import FEATURED, ModelInfo
from osiris.harness.engine import ModelRef

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


def in_menu_order(models: list[ModelInfo], in_use: ModelRef | None) -> list[ModelInfo]:
    """The model in use first, then the featured Providers' models, then the
    rest, each in the Engine's order."""
    rank = {provider: index for index, provider in enumerate(FEATURED)}
    return sorted(
        models,
        key=lambda m: (m.ref != in_use, rank.get(m.ref.provider, len(FEATURED))),
    )


def narrowed(
    models: list[ModelInfo], query: str, providers: dict[str, str]
) -> list[ModelInfo]:
    """Those whose name, family or Provider starts with ``query``, then those
    containing it, as the composer picker narrows; ``providers`` names each
    Provider by its id."""
    wanted = query.lower()

    def words(m: ModelInfo) -> list[str]:
        provider = providers.get(m.ref.provider, m.ref.provider)
        return [m.name.lower(), m.family.lower(), provider.lower()]

    starts = [m for m in models if any(w.startswith(wanted) for w in words(m))]
    contains = [
        m for m in models if m not in starts and any(wanted in w for w in words(m))
    ]
    return starts + contains
