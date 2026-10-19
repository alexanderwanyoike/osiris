"""Programs kept as git Projects in ~/Code and installed as a copy of one
commit (ADR 0017, docs/PROGRAMS.md).

The Harness creates, commits and checks; the person tries, installs and
uninstalls. Every git and build command goes through the runner as argv: git
with ``-C`` and builds with ``env -C``, since the runner has no working
directory of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from xml.etree import ElementTree

from osiris.model.names import slug
from osiris.platform import CommandRunner, FileSystem
from osiris.platform.process import CommandError
from osiris.programs.manifest import (
    APP_ID_PREFIX,
    MANIFEST_FILE,
    Manifest,
    ManifestError,
    desktop_entry,
    dump,
    parse,
)

CODE_DIR = "Code"
INSTALL_DIR = ".local/share/osiris/programs"
APPLICATIONS_DIR = ".local/share/applications"
#: Inside an installed copy: the commit it was made from.
COMMIT_FILE = ".osiris-commit"
#: Who the Harness's commits are by, so its changes are told from the person's.
HARNESS = ("Osiris Harness", "harness@osiris.invalid")

#: Folders that hold what git, builds and package managers keep, not source.
_NOT_SOURCE = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "target",
    "build",
}
#: How much of a failed build's output is worth showing.
_BUILD_TAIL = 30

AGENTS = """\
# {label}

{description}

This is an Osiris Program: the Osiris Harness made it, and any editor or coding
agent can carry it on.

- How it builds and runs is in `{manifest}` (`build` and `run`, each a list of
  words run in this folder). Keep them true when you change how it is built.
- Every change is one atomic commit: it does exactly one thing, and a refactor
  never shares a commit with a change in behaviour.
- Windows use GTK 4 and libadwaita, so the Program follows the Osiris Theme.
  Never write colours: style only with libadwaita's named colours
  (`@accent_bg_color`, `@window_bg_color`, `@card_bg_color` and the rest).
- A window follows the Theme live, without being restarted, by running this in
  the application's startup handler (Python; the same calls in any language):

```python
{follow_theme}```
"""

#: What keeps a running libadwaita window on the person's Theme. A theme switch
#: rewrites the palette file, which GTK reads only at startup, and changes the
#: GTK theme name, which unpins libadwaita's own "Adwaita-empty" and lets GTK's
#: theme take over; so the window reloads the one and puts the other back.
FOLLOW_THEME = """\
palette = Gtk.CssProvider()
path = os.path.expanduser("~/.config/gtk-4.0/gtk.css")
settings = Gtk.Settings.get_default()
pinned = settings.get_property("gtk-theme-name")  # "Adwaita-empty"

def follow(*_):
    if os.path.exists(path):
        palette.load_from_path(path)

def repin(*_):
    if settings.get_property("gtk-theme-name") != pinned:
        settings.set_property("gtk-theme-name", pinned)
        follow()

follow()
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(), palette, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
self.theme_monitor = Gio.File.new_for_path(path).monitor_file(
    Gio.FileMonitorFlags.NONE, None)
self.theme_monitor.connect("changed", follow)
settings.connect("notify::gtk-theme-name", repin)
"""


class ProgramError(RuntimeError):
    pass


#: Every Program is made with an icon the Harness draws for it.
ICON_FILE = "icon.svg"
#: An icon is a drawing, not a document; anything larger is not an icon.
ICON_LIMIT = 64 * 1024


def _check_icon(svg: str) -> None:
    if len(svg.encode()) > ICON_LIMIT:
        raise ProgramError(f"The icon must be a small SVG, under {ICON_LIMIT} bytes")
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as error:
        raise ProgramError(f"The icon is not an SVG: {error}") from error
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ProgramError("The icon must be an SVG drawing, with <svg> at its root")


class State(Enum):
    NOT_INSTALLED = "not installed"
    OUT_OF_DATE = "out of date"
    UP_TO_DATE = "up to date"


@dataclass(frozen=True)
class Program:
    manifest: Manifest
    source: Path
    head: str
    installed: str | None

    @property
    def state(self) -> State:
        if self.installed is None:
            return State.NOT_INSTALLED
        return State.UP_TO_DATE if self.installed == self.head else State.OUT_OF_DATE


class Programs:
    def __init__(self, files: FileSystem, runner: CommandRunner, home: Path) -> None:
        self._files = files
        self._runner = runner
        self._home = home

    # ---- where things are ---------------------------------------------------

    def source(self, name: str) -> Path:
        return self._home / CODE_DIR / name

    def _installed(self, name: str) -> Path:
        return self._home / INSTALL_DIR / name

    def _entry(self, name: str) -> Path:
        return self._home / APPLICATIONS_DIR / f"{APP_ID_PREFIX}{name}.desktop"

    def manifest(self, name: str) -> Manifest:
        path = self.source(name) / MANIFEST_FILE
        if not self._files.exists(path):
            raise ProgramError(f"There is no Program called {name}")
        try:
            return parse(self._files.read(path))
        except ManifestError as error:
            raise ProgramError(f"{name}'s manifest: {error}") from error

    def _git(self, name: str, *args: str, harness: bool = False) -> str:
        identity = (
            ("-c", f"user.name={HARNESS[0]}", "-c", f"user.email={HARNESS[1]}")
            if harness
            else ()
        )
        return self._runner.capture(
            "git", "-C", str(self.source(name)), *identity, *args
        )

    def _build(self, folder: Path, manifest: Manifest) -> None:
        if manifest.build is None:
            return
        try:
            self._runner.run("env", "-C", str(folder), *manifest.build, quiet=True)
        except CommandError as error:
            tail = "\n".join(str(error).splitlines()[-_BUILD_TAIL:])
            raise ProgramError(f"{manifest.label} did not build:\n{tail}") from error

    # ---- what the Harness does ---------------------------------------------

    def create(
        self,
        label: str,
        description: str,
        *,
        run: list[str],
        build: list[str] | None = None,
        terminal: bool = False,
        icon_svg: str,
    ) -> Manifest:
        """Start a Program: its folder, manifest, README and AGENTS.md, and a
        first commit."""
        name = slug(label)
        source = self.source(name)
        if self._files.exists(source):
            raise ProgramError(
                f"There is already a folder called {name} in ~/{CODE_DIR}; "
                "choose another label"
            )
        try:
            manifest = parse(
                dump(
                    Manifest(
                        name=name,
                        label=label,
                        description=description,
                        icon=ICON_FILE,
                        build=tuple(build) if build else None,
                        run=tuple(run),
                        terminal=terminal,
                    )
                )
            )
        except ManifestError as error:
            raise ProgramError(str(error)) from error
        _check_icon(icon_svg)
        self._files.write(source / MANIFEST_FILE, dump(manifest))
        self._files.write(source / ICON_FILE, icon_svg)
        self._files.write(source / "README.md", f"# {label}\n\n{description}\n")
        self._files.write(
            source / "AGENTS.md",
            AGENTS.format(
                label=label,
                description=description,
                manifest=MANIFEST_FILE,
                follow_theme=FOLLOW_THEME,
            ),
        )
        self._git(name, "init", "-q")
        self._git(name, "add", "-A")
        self._git(name, "commit", "-q", "-m", f"Start {label}", harness=True)
        return manifest

    def commit(self, name: str, message: str) -> str:
        """Commit everything changed as one atomic change. Returns its commit."""
        self.manifest(name)
        self._git(name, "add", "-A")
        if not self._git(name, "status", "--porcelain"):
            raise ProgramError(f"Nothing has changed in {name} since its last commit")
        self._git(name, "commit", "-q", "-m", message, harness=True)
        return self._git(name, "rev-parse", "HEAD")

    def revert(self, name: str, commit: str) -> None:
        """Undo one commit with a commit of its own, so history only grows."""
        self._git(name, "revert", "--no-edit", commit, harness=True)

    def check(self, name: str) -> list[str]:
        """Problems found without running anything: Python that does not compile."""
        self.manifest(name)
        source = self.source(name)
        problems = []
        for path in self._python(source):
            try:
                compile(self._files.read(path), str(path), "exec")
            except SyntaxError as error:
                where = path.relative_to(source)
                problems.append(f"{where}:{error.lineno}: {error.msg}")
        return problems

    def _python(self, folder: Path) -> list[Path]:
        found = []
        for child in self._files.list_directory(folder):
            if child.name in _NOT_SOURCE:
                continue
            if child.suffix == ".py":
                found.append(child)
            elif not child.suffix:
                found.extend(self._python(child))
        return found

    def files(self, name: str) -> list[Path]:
        """A Program's source files, relative to its folder, for reading."""
        self.manifest(name)
        source = self.source(name)
        return sorted(path.relative_to(source) for path in self._walk(source))

    def _walk(self, folder: Path) -> list[Path]:
        found = []
        for child in self._files.list_directory(folder):
            if child.name in _NOT_SOURCE:
                continue
            inside = self._files.list_directory(child)
            found.extend(self._walk(child) if inside else [child])
        return found

    def programs(self) -> list[Program]:
        """Every Program in ~/Code, and the commit of it that is installed."""
        code = self._home / CODE_DIR
        if not self._files.exists(code):
            return []
        found = []
        for folder in self._files.list_directory(code):
            if not self._files.exists(folder / MANIFEST_FILE):
                continue
            name = folder.name
            commit_file = self._installed(name) / COMMIT_FILE
            installed = (
                self._files.read(commit_file).strip()
                if self._files.exists(commit_file)
                else None
            )
            found.append(
                Program(
                    manifest=self.manifest(name),
                    source=folder,
                    head=self._git(name, "rev-parse", "HEAD"),
                    installed=installed,
                )
            )
        return found

    def holds(self, path: Path) -> bool:
        """Whether ``path`` is inside a Program's source: the only files the
        Harness may read or edit."""
        code = self._home / CODE_DIR
        if code not in path.parents:
            return False
        source = code / path.relative_to(code).parts[0]
        return self._files.exists(source / MANIFEST_FILE)

    # ---- what the person does ----------------------------------------------

    def prepare_try(self, name: str) -> tuple[list[str], Path]:
        """Build the source if it needs it; the argv and folder to run it in."""
        manifest = self.manifest(name)
        source = self.source(name)
        self._build(source, manifest)
        first, *rest = manifest.run
        program = str(source / first) if "/" in first else first
        return [program, *rest], source

    def install(self, name: str) -> str:
        """Copy the latest commit into place, build it, and add it to the menu.
        Returns the commit installed."""
        manifest = self.manifest(name)
        if self._git(name, "status", "--porcelain"):
            raise ProgramError(
                f"{manifest.label} has changes that are not committed. "
                "Commit them first: an installed Program is always a commit."
            )
        commit = self._git(name, "rev-parse", "HEAD")
        installed = self._installed(name)
        self._files.remove_tree(installed)
        self._files.make_directory(installed)
        self._runner.run(
            "git",
            f"--work-tree={installed}",
            "-C",
            str(self.source(name)),
            "checkout",
            commit,
            "--",
            ".",
            quiet=True,
        )
        try:
            self._build(installed, manifest)
        except ProgramError:
            self._files.remove_tree(installed)
            raise
        self._files.write(installed / COMMIT_FILE, commit + "\n")
        entry = self._entry(name)
        self._files.write(entry, desktop_entry(manifest, installed, entry))
        return commit

    def uninstall(self, name: str) -> None:
        """Take the Program out of the menu and remove its copy; the source stays."""
        self._files.remove(self._entry(name))
        self._files.remove_tree(self._installed(name))

    def trash(self, name: str) -> None:
        """Move a Program's source to the Trash, where it can be restored."""
        self.manifest(name)
        self._runner.run("gio", "trash", str(self.source(name)), quiet=True)
