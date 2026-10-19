"""Programs kept as git Projects in ~/Code and installed from a commit
(ADR 0017): what the Harness and the drawer do with them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.platform import FakeFileSystem, FakeRunner
from osiris.platform.process import CommandError, Result
from osiris.programs.manifest import MANIFEST_FILE, Manifest, parse
from osiris.programs.programs import HARNESS, Program, ProgramError, Programs, State

HOME = Path("/home/tester")
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
    '<circle cx="64" cy="64" r="56" fill="#e5484d"/></svg>'
)

SOURCE = HOME / "Code" / "pomodoro"
INSTALLED = HOME / ".local/share/osiris/programs/pomodoro"
ENTRY = HOME / ".local/share/applications/dev.osiris.programs.pomodoro.desktop"
GIT = ("git", "-C", str(SOURCE))
AS_HARNESS = ("-c", f"user.name={HARNESS[0]}", "-c", f"user.email={HARNESS[1]}")


def programs(
    files: FakeFileSystem | None = None, runner: FakeRunner | None = None
) -> tuple[Programs, FakeFileSystem, FakeRunner]:
    files, runner = files or FakeFileSystem(), runner or FakeRunner()
    return Programs(files, runner, HOME), files, runner


def made(**changes: object) -> FakeFileSystem:
    """A Program the Harness has already made."""
    fields = {
        "name": "pomodoro",
        "label": "Pomodoro",
        "description": "A focus timer.",
        "run": ["python3", "main.py"],
        **changes,
    }
    files = FakeFileSystem()
    files.write(SOURCE / MANIFEST_FILE, json.dumps(fields))
    return files


def calls(runner: FakeRunner) -> list[tuple[str, ...]]:
    return [call.argv for call in runner.calls]


def answer(stdout: str) -> Result:
    return Result((), 0, stdout)


class TestCreating:
    def test_a_program_starts_as_a_git_project_in_code(self) -> None:
        subject, files, runner = programs()
        manifest = subject.create(
            "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=ICON
        )
        assert manifest.name == "pomodoro"
        assert parse(files.read(SOURCE / MANIFEST_FILE)) == manifest
        assert files.exists(SOURCE / "README.md")
        assert calls(runner) == [
            (*GIT, "init", "-q"),
            (*GIT, "add", "-A"),
            (*GIT, *AS_HARNESS, "commit", "-q", "-m", "Start Pomodoro"),
        ]

    def test_its_agents_file_tells_any_agent_how_to_carry_on(self) -> None:
        subject, files, _ = programs()
        subject.create(
            "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=ICON
        )
        agents = files.read(SOURCE / "AGENTS.md")
        assert "atomic commit" in agents
        assert MANIFEST_FILE in agents

    def test_a_program_names_its_maker_as_the_person_knows_it(self) -> None:
        subject, files, _ = programs()
        subject.create(
            "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=ICON
        )
        assert "Harness" not in files.read(SOURCE / "AGENTS.md")
        assert "Harness" not in HARNESS[0]

    def test_every_program_starts_with_the_icon_drawn_for_it(self) -> None:
        subject, files, _ = programs()
        manifest = subject.create(
            "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=ICON
        )
        assert manifest.icon == "icon.svg"
        assert files.read(SOURCE / "icon.svg") == ICON

    @pytest.mark.parametrize(
        "icon",
        ["a red tomato", "<html><body/></html>", "<svg>" + "x" * 70000 + "</svg>"],
    )
    def test_an_icon_that_is_not_a_small_svg_is_refused(self, icon: str) -> None:
        subject, files, runner = programs()
        with pytest.raises(ProgramError, match="icon"):
            subject.create(
                "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=icon
            )
        assert runner.calls == []
        assert not files.exists(SOURCE)

    def test_its_agents_file_says_how_a_window_follows_the_theme_live(self) -> None:
        subject, files, _ = programs()
        subject.create(
            "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=ICON
        )
        agents = files.read(SOURCE / "AGENTS.md")
        assert "Adwaita-empty" in agents
        assert ".config/gtk-4.0/gtk.css" in agents

    def test_a_folder_that_exists_is_never_taken_over(self) -> None:
        files = FakeFileSystem()
        files.make_directory(SOURCE)
        subject, _, runner = programs(files)
        with pytest.raises(ProgramError, match="already a folder"):
            subject.create(
                "Pomodoro", "A focus timer.", run=["python3", "main.py"], icon_svg=ICON
            )
        assert runner.calls == []


class TestCommitting:
    def test_a_change_is_committed_as_the_harness_and_named(self) -> None:
        runner = FakeRunner(
            results={
                " ".join((*GIT, "status", "--porcelain")): answer(" M main.py\n"),
                " ".join((*GIT, "rev-parse", "HEAD")): answer("abc123\n"),
            }
        )
        subject, _, _ = programs(made(), runner)
        assert subject.commit("pomodoro", "Add a pause button") == "abc123"
        assert (*GIT, "add", "-A") in calls(runner)
        assert (
            *GIT,
            *AS_HARNESS,
            "commit",
            "-q",
            "-m",
            "Add a pause button",
        ) in calls(runner)

    def test_with_nothing_changed_there_is_nothing_to_commit(self) -> None:
        subject, _, _ = programs(made())
        with pytest.raises(ProgramError, match="Nothing has changed"):
            subject.commit("pomodoro", "Add a pause button")

    def test_an_unknown_program_is_refused(self) -> None:
        subject, _, _ = programs()
        with pytest.raises(ProgramError, match="no Program called pomodoro"):
            subject.commit("pomodoro", "Add a pause button")

    def test_reverting_undoes_one_commit_with_a_commit_of_its_own(self) -> None:
        subject, _, runner = programs(made())
        subject.revert("pomodoro", "abc123")
        assert calls(runner) == [(*GIT, *AS_HARNESS, "revert", "--no-edit", "abc123")]


class TestChecking:
    def test_python_that_does_not_compile_is_reported_with_its_line(self) -> None:
        files = made()
        files.write(SOURCE / "main.py", "print('ok')\ndef broken(:\n")
        subject, _, runner = programs(files)
        (problem,) = subject.check("pomodoro")
        assert problem.startswith("main.py:2:")
        assert runner.calls == []

    def test_python_that_compiles_has_no_problems(self) -> None:
        files = made()
        files.write(SOURCE / "app" / "main.py", "print('ok')\n")
        subject, _, _ = programs(files)
        assert subject.check("pomodoro") == []

    def test_what_git_and_builds_keep_is_not_checked(self) -> None:
        files = made()
        files.write(SOURCE / ".git" / "hooks" / "x.py", "def (:\n")
        files.write(SOURCE / ".venv" / "lib" / "y.py", "def (:\n")
        subject, _, _ = programs(files)
        assert subject.check("pomodoro") == []


class TestListing:
    def test_every_folder_in_code_with_a_manifest_is_a_program(self) -> None:
        files = made()
        files.make_directory(HOME / "Code" / "notes")
        files.write(INSTALLED / ".osiris-commit", "abc123\n")
        runner = FakeRunner(
            results={" ".join((*GIT, "rev-parse", "HEAD")): answer("def456\n")}
        )
        subject, _, _ = programs(files, runner)
        (program,) = subject.programs()
        assert program == Program(
            manifest=Manifest(
                name="pomodoro",
                label="Pomodoro",
                description="A focus timer.",
                icon=None,
                build=None,
                run=("python3", "main.py"),
            ),
            source=SOURCE,
            head="def456",
            installed="abc123",
        )

    def test_with_no_code_folder_there_are_no_programs(self) -> None:
        subject, _, _ = programs()
        assert subject.programs() == []


class TestInstalling:
    def test_installing_copies_the_commit_builds_it_and_adds_it_to_the_menu(
        self,
    ) -> None:
        files = made(build=["cargo", "build", "--release"])
        files.write(INSTALLED / "stale", "old copy")
        runner = FakeRunner(
            results={" ".join((*GIT, "rev-parse", "HEAD")): answer("abc123\n")}
        )
        subject, _, _ = programs(files, runner)
        assert subject.install("pomodoro") == "abc123"
        assert not files.exists(INSTALLED / "stale")
        assert (
            "git",
            f"--work-tree={INSTALLED}",
            "-C",
            str(SOURCE),
            "checkout",
            "abc123",
            "--",
            ".",
        ) in calls(runner)
        assert ("env", "-C", str(INSTALLED), "cargo", "build", "--release") in calls(
            runner
        )
        assert f"Path={INSTALLED}" in files.read(ENTRY)
        assert files.read(INSTALLED / ".osiris-commit") == "abc123\n"

    def test_uncommitted_changes_must_be_committed_first(self) -> None:
        runner = FakeRunner(
            results={" ".join((*GIT, "status", "--porcelain")): answer(" M main.py\n")}
        )
        subject, files, _ = programs(made(), runner)
        with pytest.raises(ProgramError, match="Commit"):
            subject.install("pomodoro")
        assert not files.exists(ENTRY)

    def test_a_failed_build_says_why_and_installs_nothing(self) -> None:
        runner = FakeRunner(
            results={
                "env": CommandError(("cargo",), 101, "error[E0425]: cannot find x")
            }
        )
        subject, files, _ = programs(made(build=["cargo", "build"]), runner)
        with pytest.raises(ProgramError, match="cannot find x"):
            subject.install("pomodoro")
        assert not files.exists(ENTRY)
        assert not files.exists(INSTALLED)

    def test_uninstalling_keeps_the_source(self) -> None:
        files = made()
        files.write(INSTALLED / "main.py", "print('ok')\n")
        files.write(ENTRY, "[Desktop Entry]\n")
        subject, _, _ = programs(files)
        subject.uninstall("pomodoro")
        assert not files.exists(INSTALLED)
        assert not files.exists(ENTRY)
        assert files.exists(SOURCE / MANIFEST_FILE)


class TestTrying:
    def test_trying_builds_the_source_and_says_how_to_run_it(self) -> None:
        subject, _, runner = programs(made(build=["meson", "compile"], run=["./timer"]))
        argv, folder = subject.prepare_try("pomodoro")
        assert calls(runner) == [("env", "-C", str(SOURCE), "meson", "compile")]
        assert argv == [str(SOURCE / "timer")]
        assert folder == SOURCE

    def test_a_program_with_nothing_to_build_runs_straight_away(self) -> None:
        subject, _, runner = programs(made())
        argv, _ = subject.prepare_try("pomodoro")
        assert runner.calls == []
        assert argv == ["python3", "main.py"]


class TestTrashing:
    def test_a_program_is_moved_to_the_trash_never_deleted(self) -> None:
        subject, _, runner = programs(made())
        subject.trash("pomodoro")
        assert calls(runner) == [("gio", "trash", str(SOURCE))]


class TestHolding:
    @pytest.mark.parametrize(
        "path",
        [SOURCE, SOURCE / "main.py", SOURCE / "ui" / "window.py"],
    )
    def test_a_path_inside_a_programs_source_is_held_by_it(self, path: Path) -> None:
        subject, _, _ = programs(made())
        assert subject.holds(path)

    @pytest.mark.parametrize(
        "path",
        [
            HOME / ".ssh" / "id_ed25519",
            HOME / "Code",
            HOME / "Code" / "notes" / "todo.md",
            HOME / "Code" / "pomodoro-evil" / "main.py",
            INSTALLED / "main.py",
        ],
    )
    def test_anywhere_else_is_not(self, path: Path) -> None:
        files = made()
        files.write(HOME / "Code" / "notes" / "todo.md", "x")
        subject, _, _ = programs(files)
        assert not subject.holds(path)


class TestState:
    def program(self, head: str, installed: str | None) -> Program:
        return Program(
            manifest=parse(
                '{"name": "pomodoro", "label": "Pomodoro", "description": "A timer.",'
                ' "run": ["python3", "main.py"]}'
            ),
            source=SOURCE,
            head=head,
            installed=installed,
        )

    def test_a_program_never_installed_can_be_installed(self) -> None:
        assert self.program("abc", None).state is State.NOT_INSTALLED

    def test_a_program_whose_source_moved_on_can_be_updated(self) -> None:
        assert self.program("def", "abc").state is State.OUT_OF_DATE

    def test_a_program_installed_from_its_latest_commit_is_up_to_date(self) -> None:
        assert self.program("abc", "abc").state is State.UP_TO_DATE


class TestFiles:
    def test_a_programs_files_are_its_source_without_what_tools_keep(self) -> None:
        files = made()
        files.write(SOURCE / "main.py", "x")
        files.write(SOURCE / "ui" / "window.py", "x")
        files.write(SOURCE / ".git" / "HEAD", "x")
        files.write(SOURCE / "target" / "debug" / "pomodoro", "x")
        subject, _, _ = programs(files)
        assert subject.files("pomodoro") == [
            Path("main.py"),
            Path(MANIFEST_FILE),
            Path("ui/window.py"),
        ]
