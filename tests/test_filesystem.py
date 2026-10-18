"""The filesystem port, and the ownership rule that forced it into existence."""

from __future__ import annotations

from pathlib import Path

import pytest

from osiris.platform import FakeFileSystem, FakeIdentity, FileSystem, RealFileSystem


@pytest.fixture(params=["fake", "real"])
def filesystem(request: pytest.FixtureRequest, tmp_path: Path) -> FileSystem:
    """Every behaviour below is asserted against both implementations.

    A fake that does not behave like the real thing is worse than no fake: the
    tests pass and the system breaks.
    """
    return FakeFileSystem() if request.param == "fake" else RealFileSystem()


@pytest.fixture
def root(filesystem: FileSystem, tmp_path: Path) -> Path:
    return Path("/home/tester") if isinstance(filesystem, FakeFileSystem) else tmp_path


class TestFileSystem:
    def test_written_content_reads_back(
        self, filesystem: FileSystem, root: Path
    ) -> None:
        filesystem.write(root / "a" / "b.conf", "value\n")
        assert filesystem.read(root / "a" / "b.conf") == "value\n"

    def test_writing_creates_the_parent_directories(
        self, filesystem: FileSystem, root: Path
    ) -> None:
        filesystem.write(root / "deep" / "nested" / "file", "x")
        assert filesystem.exists(root / "deep" / "nested")

    def test_appending_adds_to_the_end_and_creates_the_file(
        self, filesystem: FileSystem, root: Path
    ) -> None:
        filesystem.append(root / "logs" / "a.log", "one\n")
        filesystem.append(root / "logs" / "a.log", "two\n")
        assert filesystem.read(root / "logs" / "a.log") == "one\ntwo\n"

    def test_missing_files_raise(self, filesystem: FileSystem, root: Path) -> None:
        with pytest.raises(FileNotFoundError):
            filesystem.read(root / "absent")

    def test_remove_tree_takes_the_children(
        self, filesystem: FileSystem, root: Path
    ) -> None:
        filesystem.write(root / "gone" / "child", "x")
        filesystem.remove_tree(root / "gone")
        assert not filesystem.exists(root / "gone" / "child")


class TestOwnership:
    """The bug this port was built to make impossible.

    Provisioning runs as root before the user has ever logged in. An earlier
    version created `~/.config/ghostty`, chowned the file and that directory,
    and missed `.config` itself - which the same call had just created. The
    user could then never write their own configuration directory.
    """

    def test_every_directory_created_is_handed_to_the_owner(self) -> None:
        filesystem = FakeFileSystem()
        user = FakeIdentity(uid=1000)
        home = Path("/home/tester")

        filesystem.write(home / ".config" / "ghostty" / "config", "x", owner=user)

        assert filesystem.owners[home / ".config"] == 1000, (
            ".config was created by this call and must belong to the user"
        )
        assert filesystem.owners[home / ".config" / "ghostty"] == 1000
        assert filesystem.owners[home / ".config" / "ghostty" / "config"] == 1000

    def test_directories_that_already_existed_are_left_alone(self) -> None:
        filesystem = FakeFileSystem()
        home = Path("/home/tester")
        filesystem.make_directory(home / ".config", owner=FakeIdentity(uid=0))

        filesystem.write(home / ".config" / "rofi" / "x", "y", owner=FakeIdentity(1000))

        assert filesystem.owners[home / ".config"] == 0, (
            "ownership of a pre-existing directory is not ours to change"
        )
        assert filesystem.owners[home / ".config" / "rofi"] == 1000

    def test_give_tree_includes_the_root_of_the_tree(self, tmp_path: Path) -> None:
        """os.walk reports the root as a parent, not an entry.

        Missing it was the other half of the same bug.
        """
        filesystem = FakeFileSystem()
        plank = Path("/home/tester/.config/plank")
        filesystem.write(plank / "dock1" / "item", "x")

        filesystem.give_tree(plank, FakeIdentity(uid=1000))

        assert filesystem.owners[plank] == 1000
        assert filesystem.owners[plank / "dock1"] == 1000
        assert filesystem.owners[plank / "dock1" / "item"] == 1000
