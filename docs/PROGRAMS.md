# Programs

What the **Harness** builds for the person to keep and use (the terms are in
[CONTEXT.md](../CONTEXT.md); where they live and how they install is
[ADR 0017](adr/0017-a-program-is-a-git-project-installed-from-a-commit.md)).
This page is the design for the first version, settled in a design session on
2026-10-18; nothing here is built yet.

## Programs v0

The Harness builds a Program and makes it available like any other
application: in Cinnamon's menu, in rofi, and keepable in Plank.

1. **The Harness builds** in `~/Code/<Program>`, a git repository, one atomic
   commit per change. A Conversation with no Project moves into the new
   Program's Project.
2. **The answer ends with a card**: Try and Install, later Update. Undo reverts
   the answer's commits, newest first.
3. **Try** builds the source if it needs building and runs it. **Install**
   copies one commit into place, builds it, and writes the menu entry.
   **Update** shows the commits since the installed one, then moves the
   installed copy forward. **Uninstall** removes the copy and keeps the source.
4. **Programs are not confined in v0.** A Program runs as the person, and the
   Install confirmation says so in those words.

Building runs code, so builds happen on Try and Install, the person's actions,
never on the Harness's own initiative. A failed build lands back in the
Conversation for the Harness to fix.

## Languages and look

Python, C and C++, Rust, Go and JavaScript are first-class: Osiris ships their
toolchains, and the Harness writes in one of them unless the person asks for
another language. JavaScript runs on Node.js's Active LTS line, packaged by Arch
as `nodejs-lts-<codename>` (Krypton, Node 24, in October 2026), and Osiris
moves to each new LTS line as Arch packages it. A Program with a window uses
GTK 4 and libadwaita in whichever of those languages, through GJS for
JavaScript, so it follows the Theme and the light or dark choice like
every other application; Osiris adds nothing to make that so. It looks like
Osiris unless the person asks otherwise.

## The source

An ordinary project that any editor or coding agent can carry on: the
language's standard build files (`pyproject.toml`, `meson.build` or
`CMakeLists.txt`, `Cargo.toml`, `go.mod`, `package.json`), a README, and an
AGENTS.md saying what the Program is and how it is built and changed, atomic
commits included.
Someone who started a Program in the Harness can open it in Code - OSS, Claude
Code, opencode or Codex and keep going.

The one file that is Osiris's own is the **Program manifest**:

```json
{
  "name": "pomodoro",
  "label": "Pomodoro",
  "description": "A focus timer: 25 minutes on, 5 off.",
  "icon": "icon.svg",
  "build": ["cargo", "build", "--release"],
  "run": ["target/release/pomodoro"],
  "terminal": false
}
```

- `name`: the folder and identifier, made from the label as theme names are.
- `label`, `description`, `icon`: what the menu, rofi and Plank show; the icon
  is a file in the Program, with a generic fallback.
- `build`: optional; the argv that builds it, run in the Program's folder.
- `run`: the argv that starts it, relative to the Program's folder (ADR 0002).
- `terminal`: true for a script or command, which then opens in ghostty from
  the menu.

The menu entry is generated from the manifest; the manifest is the truth.

## How the Harness works on one

- It edits code with the Engine's own file tools (read, write, edit), allowed
  only inside that Program's folder. Running shell commands stays refused.
- Osiris tools: `create_program` (the folder, git and the manifest; a change
  undone by removing them), `commit` (one atomic change; undoable),
  `check_program` (a look: Python's compile check; for compiled languages the
  build on Try is the check), and `list_programs` (a look: what is in `~/Code`,
  and which commit of each is installed).
- It knows its Programs only from `~/Code`; there is no other record.

## Not in v0

A sandbox (until then the manifest says nothing about what a Program may
touch), sharing as a single file, automations and loops, Harness tools and
**Skills**, websites, a local view of every repository, and a general
"asks first" prompt in the drawer.
