# The Expanded layout

What the **Harness** looks like **Expanded** (CONTEXT.md), settled with a
throwaway GTK prototype over three rounds in October 2026 and approved in its
third. The prototype answered the shape; polish is owed throughout, and the
real layout is built test-first from this page, not from the prototype's code.

## What was rejected

- **A workbench.** The first round's panels, toolbars and inner tab bars read
  as cluttered: few controls and a lot of quiet space were wanted instead.
  Partly reversed on 2026-11-01: the Canvas now has groups of tabs and a small
  toolbar (see below), kept quiet.
- **No tabs at all.** The second round showed one Canvas item at a time behind
  a menu; items became hard to find. Tabs stay, but few of them.
- **The Canvas as code only.** People research, write and plan as much as
  they code; a document, its sources or a chart is as much a Canvas item as a
  file.

## What was kept

**Three panes, filling the window.** A sidebar, the Conversation and the
Canvas, edge to edge, with nothing floating inside the surface.

**A thin top bar.** The sidebar toggle, New conversation, the Conversation's
title with its menu, and at the far end the Canvas toggle and a menu. Nothing
else.

**A quiet sidebar.** New conversation and Search, then Projects as folders with
their Conversations indented beneath, then the Conversations that have no
Project. No counts, badges or previews.

**Plain answers.** Answers are text in the Skin, centred at a readable width,
with the composer at the foot: a large text area, attach on the left, the model
menu, a microphone and send on the right.

**The Canvas takes the room.** Opening the Canvas folds the sidebar away;
closing it brings the sidebar back. The sidebar toggle still opens it at any
time.

**One flat Canvas.** The Canvas is a single surface in the Theme's sunken
colour, and what it shows sits flush against it: no boxes inside boxes, no
second background behind a file tree or a code view.

**Groups of tabs, tiled (#194).** Revised on 2026-11-01 after the bolt's VM
test: one tab strip over everything read as primitive, and closing every tab
left an empty Canvas with no way back to the files. Each kind of thing now has
a group of tabs of its own (a Program's files in the code group, a question's
changes in the Changes group, and terminals and web pages as they come), and
the groups share the Canvas side by side in the order they opened, the first
on the left and the rest stacked beside it, with a line between any two to
resize them. Closing a group's last tab gives its room to the others.

**A toolbar at the top right.** Files (a folder) opens the code group on what
the first Program runs, or brings its file tree forward; it stays when every
group is closed, so the files are always one click away. The toolbar is the
one place a kind of group is opened from.

**Code reads like code.** A path bar with the path and Open in Code; below it
the file in GtkSourceView with line numbers, in the Theme's colours, wrapping
only a line that cannot fit. The Programs' files sit beside the code group when
the Canvas is at least 900sp wide, each under its Program's name, and below
that slide over it (ADR 0016: reading here, editing in Code - OSS).

**Width decides.** Below 1100sp the Canvas folds into cards under the answer
that made them; below 760sp the surface is **Compact**, its sidebar collapsed.

**Everything follows the Theme live.** Text inputs and code views included,
which the first round missed.

## Still to build

- A setting choosing between this layout, three panes, and a Canvas-first one
  where the Canvas leads and the Conversation runs narrow beside it.
- The polish the prototype skipped: spacing, motion, empty states, and every
  Canvas item type drawn properly.
