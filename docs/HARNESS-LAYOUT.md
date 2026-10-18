# The Expanded layout

What the **Harness** looks like **Expanded** (CONTEXT.md), settled with a
throwaway GTK prototype over three rounds in October 2026 and approved in its
third. The prototype answered the shape; polish is owed throughout, and the
real layout is built test-first from this page, not from the prototype's code.

## What was rejected

- **A workbench.** The first round's panels, toolbars and inner tab bars read
  as cluttered. The model is Claude's desktop app and Codex: few controls, a
  lot of quiet space.
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

**A slim tab strip.** One tab per item the Conversation has made or opened. A
full strip scrolls, and a list button at its end names every item. The Canvas
adds no tabs of its own: no Files, Terminal or Preview tabs.

**Code reads like code.** A path bar with a Files toggle, the path and Open in
Code; below it the file in GtkSourceView with line numbers, in the Theme's
colours, wrapping only a line that cannot fit. The file tree sits beside the
code when the Canvas is at least 900sp wide, and below that slides over it from
the Files toggle (ADR 0016: reading here, editing in Code - OSS).

**Width decides.** Below 1100sp the Canvas folds into cards under the answer
that made them; below 760sp the surface is **Compact**, its sidebar collapsed.

**Everything follows the Theme live.** Text inputs and code views included,
which the first round missed.

## Still to build

- A setting choosing between this layout, three panes, and a Canvas-first one
  where the Canvas leads and the Conversation runs narrow beside it.
- The polish the prototype skipped: spacing, motion, empty states, and every
  Canvas item type drawn properly.
