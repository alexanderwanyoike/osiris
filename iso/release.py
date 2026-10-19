"""Build an Osiris release and publish it, inside an Arch container.

    python3 iso/release.py v0.1.0 --bucket osiris-releases

Run as root in archlinux:latest by .github/workflows/release.yml, with this
repository mounted read-only at /src and scratch space at /work. The ISO and
its checksum go to osiris/<version>/ in the bucket, through rclone configured
by the RCLONE_CONFIG_R2_* variables the workflow passes in. The packages are
signed with the key in PACKAGE_SIGNING_KEY and published, with their
signatures, to repo/x86_64/, the repository installed systems update from. What a tag must say, the checksum's
form and the upload order are decided in osiris/iso/release.py.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

import osiris  # noqa: E402
from osiris.iso import package  # noqa: E402
from osiris.iso.release import (  # noqa: E402
    ReleaseError,
    checksum_line,
    publish_order,
    version_from_tag,
)

# archiso and what iso/repo.py and iso/profile.py need, and what
# iso/bundled/plank-reloaded needs to compile.
BUILD_DEPENDS = (
    "archiso", "base-devel", "grub", "git", "rclone",
    "freetype2", "noto-fonts", "ttf-firacode-nerd", "python-pillow", "python-numpy",
    "gnome-common", "intltool", "vala", "meson", "ninja", "bamf", "libgee",
    "libwnck3", "libdbusmenu-gtk3", "libdbusmenu-glib", "gnome-menus",
    "libcanberra", "gtk3", "at-spi2-core", "libxfixes", "libxi",
)
# Larger parts mean fewer R2 operations for a 2.5 GB ISO.
CHUNK = "64M"


def run(*argv: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(argv), flush=True)
    subprocess.run(argv, check=True, env=env)


def sign(repository: str, key: str) -> None:
    """Sign every package. pacman fetches each package's .sig beside it;
    repo-add leaves signatures out of the database unless asked."""
    env = {**os.environ, "GNUPGHOME": tempfile.mkdtemp()}
    subprocess.run(["gpg", "--batch", "--import"], input=key.encode(), env=env,
                   check=True)
    packages = sorted(os.path.join(repository, name)
                      for name in os.listdir(repository)
                      if name.endswith(".pkg.tar.zst"))
    for path in packages:
        run("gpg", "--batch", "--yes", "--detach-sign", "--no-armor",
            "--local-user", package.SIGNING_KEY, path, env=env)


def publish(repository: str, destination: str) -> None:
    packages, databases = publish_order(os.listdir(repository))
    for name in packages + databases:
        # The databases are symlinks to their archives; upload what they name.
        run("rclone", "copy", "--copy-links", "--s3-chunk-size", CHUNK,
            os.path.join(repository, name), destination)


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--work", default="/work")
    args = parser.parse_args()
    try:
        version = version_from_tag(args.tag, code_version=osiris.__version__)
    except ReleaseError as error:
        sys.exit(str(error))

    run("pacman", "-Syu", "--noconfirm", "--needed", *BUILD_DEPENDS)
    if subprocess.run(["id", "builder"], capture_output=True).returncode != 0:
        run("useradd", "-m", "builder")

    tree = os.path.join(args.work, "src")
    out = os.path.join(args.work, "out")
    shutil.rmtree(tree, ignore_errors=True)
    shutil.copytree(REPO, tree, symlinks=True)
    os.makedirs(out, exist_ok=True)
    run("chown", "-R", "builder:builder", tree, out)
    # makepkg refuses to run as root; mkarchiso must.
    run("runuser", "-u", "builder", "--", "python3",
        os.path.join(tree, "iso", "repo.py"), "--out", out)
    repository = os.path.join(out, "repo")
    sign(repository, os.environ["PACKAGE_SIGNING_KEY"])
    run("python3", os.path.join(tree, "iso", "profile.py"),
        "--out", out, "--version", version)

    name = f"osiris-{version}-x86_64.iso"
    iso = os.path.join(out, "out", name)
    checksum = f"{iso}.sha256"
    with open(checksum, "w") as fh:
        fh.write(checksum_line(name, sha256(iso)))

    destination = f"r2:{args.bucket}/osiris/{version}/"
    for path in (iso, checksum):
        run("rclone", "copy", "--s3-chunk-size", CHUNK, path, destination)
    publish(repository, f"r2:{args.bucket}/repo/x86_64/")
    print(f"RELEASED {name} to {destination}, and the packages", flush=True)


if __name__ == "__main__":
    main()
