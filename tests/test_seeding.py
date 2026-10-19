"""Files a person keeps in their home: Osiris writes each one once and then
leaves it to them."""

from __future__ import annotations

from osiris.provision.seeding import may_write


def test_a_file_that_is_not_there_yet_is_seeded() -> None:
    assert may_write(None)


def test_a_file_the_person_has_is_left_alone() -> None:
    assert not may_write("font-size = 14\n")
