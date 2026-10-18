# 16. The Canvas shows code; the code editor edits it

**Status:** Accepted

## Context

The **Harness**'s **Canvas** (CONTEXT.md) shows whatever a Conversation is
making or looking at, and for work in a **Project** that is often its code.
People expect what agents in VS Code and the desktop AI apps offer: the whole
project to browse, files to read, and changes to review, without leaving the
Harness. The question was how much of an editor that implies.

Three ways were open:

- **Embed VS Code.** GTK 4 has no way to host another application's window,
  so "embedding" means running openvscode-server or code-server and showing it
  in a WebKitGTK view. Neither server is in Arch's repositories, so Osiris
  would build and ship it itself, as it does Plank Reloaded: several hundred
  megabytes with Node and WebKit, and a fast-moving upstream to follow.
- **Monaco in a web view.** An editor component without extensions, a
  terminal or Git: an imitation of an editor people already have.
- **Show code natively, and hand editing to the editor.** GtkSourceView,
  already used for code in answers, draws the files, a tree to navigate and
  diffs, in the **Theme**'s colours. Code - OSS (`code`, Arch `extra`) ships
  with Osiris and opens the file or the Project when the person wants to edit.

## Decision

The Canvas shows code natively, read-only: the Project's tree to browse, files
highlighted in the Theme's colours, changes as diffs. Editing happens in Code -
OSS, opened from the Canvas at the file or the Project. The Harness contains
no editor.

This is ADR 0005 (orchestrate, do not implement) applied to code: Osiris shows
and connects; the editor edits.

## Consequences

- No WebKit, Node or VS Code build to ship or maintain for code.
- Reading and reviewing stay in the Harness; editing is one click away in a
  full editor with its extensions, which can sit beside the Expanded Harness.
- The Canvas will likely need a web view for other content (web pages, HTML
  documents). That is its own decision, and not a reason to rebuild an editor.
