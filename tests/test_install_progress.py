"""How far the install has got, read from what archinstall prints.

Every line fed in here is one archinstall 4.5 or pacman 7.1 really prints,
taken from their source or captured from pacman running under archinstall's
own pty, as the installer runs it.
"""

from __future__ import annotations

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
