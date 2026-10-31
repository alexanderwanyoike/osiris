# Contributing to Osiris

Thanks for wanting to help. This page covers how changes reach the code: the
branches, the checks, and the rules a pull request is held to.

## Branches

| Branch | What it is |
|---|---|
| `main` | What is released. Changes reach it only from `dev`. |
| `dev` | Where finished work comes together. Every pull request targets `dev`. |
| `feature/<name>`, `fix/<name>`, `docs/<name>` | One piece of work, branched from `dev`. |

1. Branch from the latest `dev`:

   ```bash
   git switch -c feature/<name> origin/dev
   ```

2. Open a pull request into `dev`. CI has to pass, and a maintainer merges it
   with a merge commit.
3. When `dev` is ready to release, a maintainer opens a pull request from `dev`
   into `main`.

Work that builds on a pull request still in review can be stacked: branch from
that pull request's branch and target it. Once the lower one merges, retarget
yours to `dev`.

## Before you open a pull request

Read [CONTEXT.md](CONTEXT.md) for the project's language, and the part of
[docs/](docs) your change touches. [DEVELOPMENT.md](docs/DEVELOPMENT.md) has
the development loop and the traps that have each cost someone a day; read it
before touching a user's home directory, a disk or a GTK widget.

Every check CI runs has to pass:

```bash
ruff check .
```

```bash
ruff format --check .
```

```bash
mypy
```

```bash
lint-imports
```

```bash
vulture
```

```bash
pytest
```

A change that needs an exception to any of them says why in the pull request.

## How changes are made

- **Test first.** One behaviour per cycle: write the smallest test that fails
  for the right reason, make it pass with the least code, then refactor. This
  includes the GTK apps, which are tested headless under Xvfb. A bug gets a
  failing test before its fix.
- **Atomic commits.** A commit does one thing: a failing test, the code that
  passes it, a refactor, a rename and a formatting change are separate commits.
  The commit message says why.
- **Ports and adapters.** Everything outside the process (files, commands, the
  network) goes through a Protocol in `osiris.platform` and is passed in, so
  the logic is testable with fakes. GTK code draws; the logic it shows lives in
  `osiris/`, where it is tested.
- **No bash that we author.** Python only, and every process is spawned as an
  argv list: no `shell=True`, no `bash -c`.
- **Orchestrate, do not implement.** If a feature seems to need a GTK theme, an
  icon set or a desktop component of our own, the answer is almost always to
  configure what upstream already ships. Anything that could erase a disk or
  leave a machine unbootable is done by Arch's own tools.
- **No emojis** in code, docs, commit messages or pull requests.

## Pull request description

Every pull request uses this structure:

```
## Background
What the change is for, and the context a reviewer needs.
## Tasks
- [x] A checklist of what the change does
## Tested
What tests were written, and what was checked by hand (on a VM, for example).

Tech Debt (optional): what this leaves to do later.
```

## Reporting a problem or an idea

[Open an issue](https://github.com/alexanderwanyoike/osiris/issues/new/choose)
and pick a form: **Something is broken** or **An idea**. Write it in your own
words; you do not need to know how Osiris works inside. Questions go to
[Discussions](https://github.com/alexanderwanyoike/osiris/discussions) instead.

For a problem on an installed system, it also helps to include the Osiris
version (`pacman -Q osiris`) and the output of `journalctl --user -b` around
the time it happened.

### What happens next

A maintainer reads every new issue (`needs-triage`) and moves it on: asks you
for more (`needs-info`), marks it ready to build (`ready-for-agent` or
`ready-for-human`), or explains why it will not be done (`wontfix`). An `area:`
label says which part of Osiris it touches. Work that is planned sits in a
[milestone](https://github.com/alexanderwanyoike/osiris/milestones), one per
piece of the [roadmap](docs/ROADMAP.md). Issues marked `good first issue` are a
good place to start contributing.
