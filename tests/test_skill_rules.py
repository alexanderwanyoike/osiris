"""Skills (#154): each skill on, off or asked about first, as a rule in the
Engine's own config."""

from __future__ import annotations

from osiris.harness.skill_rules import choice_of, chosen

CAREFUL = [
    {"action": "*", "resource": "*", "effect": "ask"},
    {"action": "skill", "resource": "*", "effect": "allow"},
]


def test_a_skill_with_no_rule_of_its_own_is_on() -> None:
    assert choice_of({"permissions": CAREFUL}, "review") == "on"


def test_turning_a_skill_off_adds_a_deny_after_the_rules_it_overrides() -> None:
    config = chosen({"permissions": list(CAREFUL)}, "review", "off")
    assert config["permissions"][-1] == {
        "action": "skill",
        "resource": "review",
        "effect": "deny",
    }
    assert choice_of(config, "review") == "off"


def test_a_new_choice_replaces_the_old_rather_than_piling_up() -> None:
    config = chosen({"permissions": list(CAREFUL)}, "review", "off")
    config = chosen(config, "review", "ask")
    rules = [r for r in config["permissions"] if r["resource"] == "review"]
    assert rules == [{"action": "skill", "resource": "review", "effect": "ask"}]
    assert choice_of(config, "review") == "ask"


def test_turning_a_skill_back_on_leaves_no_rule_of_its_own() -> None:
    config = chosen({"permissions": list(CAREFUL)}, "review", "off")
    config = chosen(config, "review", "on")
    assert config["permissions"] == CAREFUL
