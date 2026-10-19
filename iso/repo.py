"""Build the `osiris` package and the repository the installer reads it from.

    python3 iso/repo.py                 # writes build/repo
    python3 iso/repo.py --out /var/tmp/osiris

Run as a normal user: makepkg refuses to run as root. The ISO build
(iso/profile.py, as root) copies build/repo onto the medium, where archinstall
installs from it. What goes into the package is described in
osiris/iso/package.py; this only stages the files and hands them to the
standard tools - makepkg to build, repo-add to index.

The repository also carries the packages `package.BUNDLED` names, built from
their pinned PKGBUILDs in iso/bundled/. Those are compiled for real, so their
`depends` and `makedepends` must be installed on the build machine first;
makepkg says which are missing.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "provision"))
sys.path.insert(0, REPO)

import osiris  # noqa: E402
from osiris.iso import package  # noqa: E402
from run import run, stream  # noqa: E402

#: The package's version is the code's, which each home is brought up to.
VERSION = osiris.__version__


def stage(directory: str) -> None:
    """Lay out the package's files under directory/root, and its PKGBUILD."""
    if os.path.isdir(directory):
        shutil.rmtree(directory)
    root = os.path.join(directory, "root")
    source = os.path.join(root, package.SOURCE_DIR.lstrip("/"))
    for relative in package.PAYLOAD:
        shutil.copytree(
            os.path.join(REPO, relative),
            os.path.join(source, relative),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    launcher = os.path.join(root, package.SETUP.lstrip("/"))
    os.makedirs(os.path.dirname(launcher))
    with open(launcher, "w") as fh:
        fh.write(package.SETUP_LAUNCHER)
    os.chmod(launcher, 0o755)
    hook = os.path.join(root, package.HOOK_PATH.lstrip("/"))
    os.makedirs(os.path.dirname(hook))
    with open(hook, "w") as fh:
        fh.write(package.HOOK)
    keyrings = os.path.join(root, package.KEYRING_DIR.lstrip("/"))
    os.makedirs(keyrings)
    shutil.copy(os.path.join(REPO, package.KEYRING_SOURCE),
                os.path.join(keyrings, f"{package.NAME}.gpg"))
    with open(os.path.join(keyrings, f"{package.NAME}-trusted"), "w") as fh:
        fh.write(package.trusted())
    with open(os.path.join(directory, "PKGBUILD"), "w") as fh:
        fh.write(package.pkgbuild(VERSION))


def build(out: str) -> str:
    """Build the package into out/repo and index it. Returns that directory."""
    if os.geteuid() == 0:
        sys.exit("makepkg refuses to run as root; run this as a normal user")
    staging = os.path.join(out, "package")
    repository = os.path.join(out, "repo")
    stage(staging)
    if os.path.isdir(repository):
        shutil.rmtree(repository)
    os.makedirs(repository)

    os.environ["PKGDEST"] = repository
    os.chdir(staging)
    # --nodeps: the build host need not have Cinnamon installed to package
    # something that depends on it.
    stream("makepkg", "--force", "--nodeps", "--cleanbuild", "--noconfirm")

    built = [name for name in os.listdir(repository) if ".pkg.tar" in name]
    if len(built) != 1:
        sys.exit(f"expected one package in {repository}, found {built}")

    for name in package.BUNDLED:
        recipe = os.path.join(out, "bundled", name)
        if os.path.isdir(recipe):
            shutil.rmtree(recipe)
        shutil.copytree(os.path.join(HERE, "bundled", name), recipe)
        os.chdir(recipe)
        stream("makepkg", "--force", "--cleanbuild", "--noconfirm")

    # makepkg also splits out debug symbols, as Arch's makepkg.conf asks;
    # nothing installs them, so they stay off the medium.
    for name in os.listdir(repository):
        if "-debug-" in name:
            os.remove(os.path.join(repository, name))
    packages = sorted(name for name in os.listdir(repository)
                      if ".pkg.tar" in name and not name.endswith(".sig"))
    run("repo-add", os.path.join(repository, f"{package.NAME}.db.tar.gz"),
        *(os.path.join(repository, name) for name in packages))
    return repository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(REPO, "build"),
                        help="build directory (default: <repo>/build)")
    args = parser.parse_args()
    repository = build(os.path.abspath(args.out))
    for name in sorted(os.listdir(repository)):
        print(f"  {os.path.join(repository, name)}")
    print("REPO_BUILT")


if __name__ == "__main__":
    main()
