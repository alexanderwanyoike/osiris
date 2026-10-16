"""Where the running user's files live.

One function, in its own module, because getting it wrong is silent. Every
part of the theme system writes into the user's home, and more than one of
them is invoked through `su <user> -c` - from the installer, from a provisioning
script, from a shell that su did not reset. The answer has to come from the
process's own identity, not from the environment.
"""
import os
import pwd
import sys


def home() -> str:
    """The running user's home directory.

    Deliberately not `os.path.expanduser("~")`: that trusts $HOME, which is
    wrong whenever the process was started with `su <user> -c` - $HOME is still
    root's, and the previews, themes and configuration all land in /root where
    the user will never see them.
    """
    try:
        return pwd.getpwuid(os.getuid()).pw_dir
    except KeyError:
        return os.path.expanduser("~")


def use_osiris_package() -> None:
    """Put the tested `osiris` package on sys.path.

    It is installed beside these files on a target, and lives two directories
    up in a checkout.
    """
    for candidate in (
        "/usr/share/osiris/lib",
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ):
        if os.path.isdir(os.path.join(candidate, "osiris")):
            sys.path.insert(0, candidate)
            return
