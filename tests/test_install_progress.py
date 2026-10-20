"""How far the install has got, read from what archinstall prints.

Every line fed in here is one archinstall 4.5 or pacman 7.1 really prints,
taken from their source or captured from pacman running under archinstall's
own pty, as the installer runs it.
"""

from __future__ import annotations

import pytest

from osiris.provision.install_progress import Status, Tracker


def test_an_install_starts_by_preparing_the_disk() -> None:
    assert Tracker().status == Status("Preparing your disk", 1, 7, 0.0)


#: The line archinstall prints as it starts each stage after the first, in
#: the order it prints them (archinstall/lib/installer.py, scripts/guided.py).
STARTS = [
    (
        "Installing packages: ['base', 'sudo', 'linux-firmware', 'mkinitcpio',"
        " 'linux', 'btrfs-progs', 'intel-ucode']",
        "Installing the base system",
    ),
    ("Adding bootloader grub to /dev/vda1", "Setting up the bootloader"),
    ("Creating user alex", "Installing drivers and sound"),
    ("Installing packages: ['osiris']", "Installing the desktop"),
    ('Executing custom command "osiris-setup" ...', "Applying Osiris"),
    ("Updating /mnt/etc/fstab", "Finishing"),
]


def test_each_stage_starts_at_the_line_archinstall_prints_for_it() -> None:
    tracker = Tracker()
    seen = []
    for line, _ in STARTS:
        status = tracker.feed(line)
        assert status is not None
        seen.append((status.title, status.step))
    assert seen == [(title, step) for step, (_, title) in enumerate(STARTS, 2)]


def test_the_package_installs_take_most_of_the_bar() -> None:
    tracker = Tracker()
    starts = [tracker.status.fraction]
    for line, _ in STARTS:
        status = tracker.feed(line)
        assert status is not None
        starts.append(status.fraction)
    shares = [
        end - start for start, end in zip(starts, [*starts[1:], 1.0], strict=True)
    ]
    assert all(share > 0 for share in shares)
    titles = ["Preparing your disk"] + [title for _, title in STARTS]
    largest = sorted(zip(shares, titles, strict=True), reverse=True)[:2]
    assert {title for _, title in largest} == {
        "Installing the desktop",
        "Installing the base system",
    }


def test_an_earlier_stages_line_never_takes_the_install_back() -> None:
    tracker = Tracker()
    tracker.feed("Installing packages: ['osiris']")
    before = tracker.status
    assert tracker.feed("Creating user alex") is None
    assert tracker.status == before


BASE = STARTS[0][0]
BOOTLOADER = STARTS[1][0]
SYNC = ":: Synchronizing package databases..."


def fractions(tracker: Tracker, lines: list[str]) -> list[float]:
    """The fraction after each line, whether or not it changed."""
    found = []
    for line in lines:
        tracker.feed(line)
        found.append(tracker.status.fraction)
    return found


def bounds_of_the_base_stage() -> tuple[float, float]:
    tracker = Tracker()
    start = tracker.feed(BASE)
    end = tracker.feed(BOOTLOADER)
    assert start is not None and end is not None
    return start.fraction, end.fraction


def test_pacmans_install_counts_move_the_bar_through_a_stage() -> None:
    start, end = bounds_of_the_base_stage()
    tracker = Tracker()
    moved = fractions(
        tracker,
        [
            BASE,
            SYNC,
            "( 1/20) installing iana-etc                        [----------]   0%",
            "(10/20) installing bash                            [##########] 100%",
            "(20/20) installing nano                            [##########] 100%",
        ],
    )
    assert moved[0] == moved[1] == start
    assert start < moved[2] < moved[3] < moved[4] < end


def test_pacmans_download_counts_move_the_bar_before_it_installs() -> None:
    start, _ = bounds_of_the_base_stage()
    moved = fractions(
        Tracker(),
        [
            BASE,
            SYNC,
            " Total ( 0/20)           0.0   B  0.00   B/s 00:00 [----------]   0%",
            " Total ( 4/20)           9.5 MiB  15.7 MiB/s 00:00 [####------]  43%",
            " Total (20/20)          21.6 MiB  43.3 MiB/s 00:01 [##########] 100%",
            "( 1/20) installing iana-etc                        [----------]   0%",
        ],
    )
    assert moved[2] == start
    assert start < moved[3] < moved[4] < moved[5]


def test_pacmans_hooks_finish_a_transaction_once_it_says_it_runs_them() -> None:
    _, end = bounds_of_the_base_stage()
    moved = fractions(
        Tracker(),
        [
            BASE,
            SYNC,
            " Total (20/20)          21.6 MiB  43.3 MiB/s 00:01 [##########] 100%",
            "(20/20) checking keys in keyring                   [##########] 100%",
            "(20/20) installing nano                            [##########] 100%",
            ":: Running post-transaction hooks...",
            "(1/3) Generating the configured locale...",
            "(3/3) Creating iconv module configuration cache...",
        ],
    )
    assert moved[3] == moved[2]
    assert moved[4] < moved[6] < moved[7] == pytest.approx(end)


def test_each_of_several_installs_in_a_stage_moves_the_bar_on() -> None:
    """archinstall installs the bootloader's packages a few at a time."""
    tracker = Tracker()
    tracker.feed(BOOTLOADER)
    end = Tracker()
    for line, _ in STARTS[:3]:
        end.feed(line)
    moved = fractions(
        tracker,
        [
            "Installing packages: ['plymouth']",
            SYNC,
            "(3/3) installing plymouth                          [##########] 100%",
            ":: Running post-transaction hooks...",
            "(2/2) Updating linux initcpios...",
            "Installing packages: ['grub', 'efibootmgr']",
            SYNC,
            "(2/2) checking keys in keyring                     [##########] 100%",
            "(1/2) installing grub                              [##########] 100%",
        ],
    )
    assert moved[4] == moved[7] < moved[8] < end.status.fraction
