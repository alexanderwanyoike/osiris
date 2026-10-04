# 3. Ports and adapters around the operating system

**Status:** Accepted

## Context

Every interesting function in the original code reached straight for
`subprocess.run`, `open()` and `/etc`. The consequence was that **nothing could
be tested without a virtual machine**. Verifying a change to the install flow
meant a 40-minute pacstrap; verifying the theme engine meant a running Cinnamon
session; verifying an error path meant arranging for a real failure.

In practice that meant the code was not tested at all, and defects were found
by running the installer and watching. Several shipped:

- `~/.config` created as root on every fresh install, so the user could never
  write their own configuration directory. Invisible in development, because
  the development account had already logged in.
- A race where `partprobe` returned before the device nodes existed, so `mount`
  failed intermittently.
- An install that reported failure after succeeding, because the final
  `umount` hit a lingering gpg-agent.

Each is a few lines to assert against a fake. None was expressible at all
against the real thing.

## Decision

Everything outside the process - running a command, touching the filesystem,
asking who the user is - sits behind a Protocol in `osiris.platform`. The rest
of the codebase depends on the protocol and is handed an implementation.

```
CommandRunner   SubprocessRunner   FakeRunner
FileSystem      RealFileSystem     FakeFileSystem
Identity        SystemIdentity     FakeIdentity
```

Dependencies are passed to constructors. There is no service locator, no
framework, and no global state: the composition happens in `__main__` and in
tests, and nowhere else.

`.importlinter` enforces that only `osiris.platform.process` may import
`subprocess`, that the domain model imports neither it nor anything above it,
and that GTK appears only in the application layer.

## Consequences

The install flow becomes testable without a disk: "given pacstrap fails on the
third call, assert the target is unmounted and the error names the command".

Fakes must behave like the real implementations or the tests are worse than
useless. `tests/test_filesystem.py` therefore runs the same assertions against
both, parameterised.

The cost is indirection. A function that wants to run a command takes a runner
rather than calling one, and the constructor signatures grow. In exchange, the
thing that was previously impossible - knowing the code works without booting a
machine - becomes routine.

Not everything gets a port. A port is justified when the real implementation is
slow, destructive, or unavailable in CI. Pure computation - colour derivation,
palette maths, wallpaper generation - is tested directly, because it has no
dependencies to invert.
