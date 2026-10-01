"""Running the steps, and reporting how far through they are."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from osiris.model.request import InstallRequest
from osiris.platform.filesystem import FileSystem
from osiris.platform.process import CommandRunner
from osiris.provision.layout import DiskLayout
from osiris.provision.steps import Context, Step

#: fraction completed, what is starting now
Progress = Callable[[float, str], None]


class Installer:
    """Turns a request into an installed system.

    Everything it touches is handed to it: the runner, the filesystem, and the
    steps. There is no construction inside, which is what makes the whole flow
    assertable against fakes - "given pacstrap fails, was the target
    unmounted?" is a test rather than a disk.
    """

    def __init__(
        self,
        runner: CommandRunner,
        files: FileSystem,
        steps: Sequence[Step],
        cleanup: Step | None = None,
    ) -> None:
        self._runner = runner
        self._files = files
        self._steps = list(steps)
        self._cleanup = cleanup

    def install(
        self, request: InstallRequest, progress: Progress | None = None
    ) -> None:
        """Run every step. Raises on failure; never calls sys.exit.

        The target is unmounted whether this succeeds or fails, so a second
        attempt starts from a known state rather than from whatever the first
        one left behind.
        """
        request.validate()
        context = Context(
            request=request,
            runner=self._runner,
            files=self._files,
            layout=DiskLayout.for_filesystem(request.filesystem, self._runner),
        )

        total = sum(step.weight for step in self._steps) or 1.0
        done = 0.0
        try:
            for step in self._steps:
                if progress is not None:
                    progress(done / total, step.label)
                step.run(context)
                done += step.weight
        finally:
            if self._cleanup is not None:
                self._cleanup.run(context)
        if progress is not None:
            progress(1.0, "Done")
