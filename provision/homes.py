"""Writing into users' home directories from root.

Provisioning runs as root, and on a fresh install it runs *before* anyone has
logged in. Every directory it creates under a home therefore belongs to root
unless it is explicitly handed back.

Getting this subtly wrong is easy and the consequences are not subtle. The
previous code called `os.makedirs(home/.config/ghostty)` and then chowned the
file and `.config/ghostty` - but not `.config`, which the same call had just
created. The result was a user who could not write to their own `~/.config`:
no theme could be applied, no terminal or launcher configuration could be
saved, and the failure surfaced much later as an unrelated permission error.

It never appeared in development because there the user had already logged in,
so `.config` existed and was theirs before any of this ran.

Hence this module. Create directories through `makedirs` and write through
`write` or `copy`, and ownership of everything they create is correct.
"""
import os
import pwd
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osiris.provision.seeding import may_write  # noqa: E402


def desktop_users() -> list[pwd.struct_passwd]:
    """Real human accounts with a home directory on disk."""
    return [p for p in pwd.getpwall()
            if 1000 <= p.pw_uid < 60000 and os.path.isdir(p.pw_dir)]


def owner_of(home: str) -> pwd.struct_passwd | None:
    """The account a home directory belongs to, by its stat owner.

    Looked up by uid rather than by the directory's name: those usually match
    and are not required to.
    """
    try:
        return pwd.getpwuid(os.stat(home).st_uid)
    except (OSError, KeyError):
        return None


def makedirs(path: str, owner: pwd.struct_passwd | None) -> None:
    """`mkdir -p`, giving every component this call creates to `owner`.

    Components that already existed are left alone - their ownership is not
    ours to change.
    """
    created = []
    probe = os.path.abspath(path)
    while not os.path.exists(probe):
        created.append(probe)
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent

    os.makedirs(path, exist_ok=True)
    if owner is None:
        return
    for directory in created:
        try:
            os.chown(directory, owner.pw_uid, owner.pw_gid)
        except OSError:
            pass


def write(path: str, text: str, owner: pwd.struct_passwd | None) -> None:
    makedirs(os.path.dirname(path), owner)
    with open(path, "w") as fh:
        fh.write(text)
    if owner is not None:
        os.chown(path, owner.pw_uid, owner.pw_gid)


def copy(source: str, destination: str,
         owner: pwd.struct_passwd | None) -> None:
    makedirs(os.path.dirname(destination), owner)
    shutil.copy(source, destination)
    if owner is not None:
        os.chown(destination, owner.pw_uid, owner.pw_gid)


def seed(source: str, destination: str,
         owner: pwd.struct_passwd | None) -> bool:
    """`copy`, unless the person already has a file there of their own."""
    try:
        with open(destination) as fh:
            existing: str | None = fh.read()
    except FileNotFoundError:
        existing = None
    if not may_write(existing):
        return False
    copy(source, destination, owner)
    return True


def chown_tree(path: str, owner: pwd.struct_passwd) -> None:
    """Give `path` and everything under it to `owner`.

    Note the root of the tree, which `os.walk` reports as a parent rather than
    as an entry - the reason an earlier version left one directory root-owned.
    """
    if not os.path.exists(path):
        return
    os.chown(path, owner.pw_uid, owner.pw_gid)
    for root, directories, files in os.walk(path):
        for entry in directories + files:
            try:
                os.chown(os.path.join(root, entry),
                         owner.pw_uid, owner.pw_gid)
            except OSError:
                pass
