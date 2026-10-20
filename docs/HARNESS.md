# The Harness

The AI built into Osiris (the terms are in [CONTEXT.md](../CONTEXT.md); the
decision is [ADR 0015](adr/0015-harness-owns-tools-rents-engine.md)). Osiris owns
what the Harness may do, how it shows its work and what it keeps; model access
and the agent loop are rented from an **Engine**, opencode first.

## What exists today

The first slice of ROADMAP P3.5:

- **Super+A**, or the button at the far right of the top panel, slides the
  Harness in as a drawer on the right edge: the conversation above, the line to
  ask in at the bottom. It floats over windows, stays put while you work
  elsewhere, and Escape, Super+A or the button slide it away again with the
  conversation kept.
- The drawer always shows the model that last answered, the tokens spent in this
  conversation, and the **Provider**'s allowance as "not reported": opencode
  reports tokens and cost per answer but no allowance or reset time, and
  **Usage** is never estimated.
- **It makes and applies Themes.** Asked for "a calm theme for working late",
  the model describes a **Theme intent** (a seed colour, a **Harmony**, a mood,
  light or dark) through the Osiris tools, Osiris's own rules derive the
  palette, and the theme is kept with the person's own and applied. The answer
  ends with what changed and an **Undo**, which reverses it without the model:
  the previous theme comes back and the new one is deleted. See
  [The Osiris tools](#the-osiris-tools).
- **Everything else is refused.** Any other action the model reaches for
  (running a command, reading a file, editing anything) is rejected, and the
  model is told what it may use instead.
- **Unless the person allows everything.** A switch on the Providers page
  (`osiris.harness.trust`) lets the Harness allow any request, logged with the
  tier `anything`, and restarts the tool server so the model is told it may run
  commands and change any file. It is off until the person turns it on.
- **It asks for the administrator password in the Conversation.** When a
  command it runs uses `sudo`, an admin password card appears under the
  answer: "Osiris needs your password to run:" and the exact command, a shell
  string shown whole and labelled, a script marked as not shown. The password
  typed there goes to sudo and nowhere else; Deny fails the command. See
  [Admin passwords](#admin-passwords).
- **It shows its work.** While Osiris answers, a row under the answer pulses
  in the Theme's accent, says in plain words what it is doing ("Thinking",
  "Editing pomodoro/main.py", "Making a theme") and counts the time since the
  question. Every step it took, allowed or refused, is kept under the answer,
  folded away as "Used 4 tools", each in the past tense ("Edited
  pomodoro/main.py") or as "Not allowed to run ls /etc".
- **The Harness log** keeps everything: each question before it is sent, each
  answer with the model that gave it and its tokens, every tool call whether or
  not it asked, every action allowed and its **Action tier**, every change with
  the step that undoes it, every Undo, every rejection and every failure. It is append-only JSON lines,
  readable with any tool:

  ```
  ~/.local/share/osiris/harness/log.jsonl
  ```

- **Providers.** The model named in the drawer's header opens the Providers
  page: every Provider the Engine can reach, with "Sign in with ChatGPT" and
  other sign-in pages opened in the browser, or a field for an API key
  (OpenCode Go). It is also where the **Default model** is chosen, from the
  models the connected accounts can reach. The choice is plain text the
  person can edit:

  ```
  ~/.config/osiris/harness/models
  default = openai/gpt-5.5
  fallback = opencode-go/kimi-k2
  ```

  Choosing a model mid-conversation switches the conversation to it. Moving to
  the **Fallback model** when the Default cannot answer is still to come.

Next: a history of conversations in the drawer (the last one reopens after a
restart, any earlier one can be picked up again, and a new one started).

## How it fits together

```
apps/harness/main.py          the drawer: GTK only, draws the conversation
apps/harness/render.py        a widget per block of an answer, one view per turn
apps/harness/look.py          the Theme's colours and the chosen Skin, kept current
apps/harness/providers.py     the Providers page
apps/harness/skins/           Bubbles and Transcript
apps/harness/harness-drawer@osiris   Cinnamon extension: right edge, full height, slide
apps/harness/harness@osiris   Cinnamon applet: the panel button
osiris/harness/conversation   what the drawer shows, from the Engine's events
osiris/harness/activity       each step of an answer in plain words, and time spent
osiris/harness/markdown       answers as blocks, inline text as escaped Pango markup
osiris/harness/style          colour variables and code scheme from a Theme; Skin choice
osiris/harness/harness        its sessions: the log, and actions allowed by tier
osiris/harness/tiers          Action tiers: a look, an undoable change
osiris/harness/log            the Harness log
osiris/harness/engine         the Engine port and its events
osiris/harness/accounts       the Accounts port: Providers, signing in, models
osiris/harness/settings       the Default and Fallback models, as plain text
osiris/harness/opencode       the opencode 2.0 adapter
osiris/harness/admin          admin password requests: who may ask, for what, shown where
osiris/platform/processes     the Processes port: who a running process is, from /proc
apps/harness/admin_card.py    the admin password card
apps/harness/askpass.py       the askpass helper sudo runs, and its own dialog
osiris/platform/http          the HTTP port the adapter talks through
osiris/apps/tool_server       the Osiris tools as an MCP server, each with its tier
osiris/themes/actions         what the tools do with Themes, behind osiris/themes/store
apps/harness/tool_server.py   runs the tool server on stdio over the theme engine
apps/harness/theme_store.py   the theme engine as a ThemeStore, for acting and undoing
provision/harness.py          installs the drawer, extension, applet, D-Bus activation, autostart,
                              the askpass helper and the agent's sudo
```

The drawer is resident, like the theme switcher: started at login, or by D-Bus
on first use. Super+A and the panel button both run
`gapplication action dev.osiris.Harness show`, which toggles it.

### The Osiris tools

What the model may do on this machine is offered by Osiris as an MCP server
(`osiris`), built on the official SDK (Arch's `python-mcp`). The drawer attaches
it to the Engine when it connects, with opencode's runtime MCP API, so nothing
is written into the person's own opencode configuration.

| Tool | Action tier | What it does | Undo |
|---|---|---|---|
| `list_themes` | a look | the themes, light or dark, and which is applied | |
| `create_theme` | an undoable change | a User theme from a Theme intent; never replaces one | deletes it |
| `apply_theme` | an undoable change | applies a theme to the whole desktop | applies the one it replaced |

opencode runs MCP tools from its code mode (`tools.osiris.apply_theme(...)`),
and every call still raises a permission request named `osiris_<tool>`. The
Harness answers it by the tool's tier: a look or an undoable change is allowed
and logged; anything without a tier is rejected. The model never writes a
colour: the seed is a hex colour whose hue alone counts, and harmony and mood
are fixed choices.

Each change the tool server makes is written to the Harness log with the step
that reverses it. When an answer finishes, the drawer reads the changes logged
since the question and shows them with one Undo, which runs those steps newest
first; the theme that is applied is never deleted.

### Admin passwords

The decision and its guards are [ADR 0018](adr/0018-the-agents-sudo-asks-in-an-admin-password-card.md).
sudo asks a helper for the password only when run with `-A`, so the agent's
commands find a sudo of Osiris's first on their PATH:

```
/usr/lib/osiris/agent-bin/sudo    runs /usr/bin/sudo -k -A, every command asking
/usr/lib/osiris/askpass           the helper sudo runs (apps/harness/askpass.py)
```

The Harness puts `agent-bin` first on PATH and sets `SUDO_ASKPASS` before it
starts the Engine, which inherits both. The helper refuses unless a root sudo
started it, reads the command from that sudo's arguments, and calls
`Ask(command, prompt)` on `dev.osiris.Harness.Admin` at
`/dev/osiris/Harness/Admin`. The Harness checks the caller from the bus's own
record of its pid, finds the sudo descending from the Engine's process (the
`pid` opencode records in `service.json`) and the running Conversation whose
latest allowed command runs sudo, and shows the card there. Allow answers
with the password and empties the entry. Deny answers refused, and so does a
card left unanswered, just before the helper's five-minute wait ends, or one
whose answer ends first. The Harness
log records the command and the decision, never the password.

A genuine sudo that is not the agent's, or any sudo when the Harness is not
running, gets the helper's own dialog instead, naming the program that ran
it. Only `sudo -A` reaches the helper; in a terminal sudo asks as it always
has.

### How answers are drawn

Answers are Markdown. `osiris/harness/markdown.py` parses them with
markdown-it-py (CommonMark with tables and strikethrough, raw HTML off) into
blocks: headings, paragraphs, lists, quotes, tables, rules and fenced code.
Inline text becomes Pango markup with everything from the model escaped, so
markup or HTML in an answer is shown, never interpreted, and only web and mail
links are clickable. Each block is drawn by its own widget (`render.py`):
labels and grids for text and tables, GtkSourceView for code, with its
language and a Copy button. While an answer streams only the block still
growing is redrawn.

### Theme and Skin

The drawer follows the split CONTEXT.md draws: the **Theme** is colour, the
**Skin** is shape.

- From the current Theme, `osiris/harness/style.py` produces the colour
  variables a Skin may use (`@harness_bg`, `@harness_accent` and the rest) and
  a GtkSourceView scheme, `osiris`, with syntax in the palette's terminal
  colours so code looks as it will in ghostty. It is written to
  `~/.local/share/gtksourceview-5/styles/osiris.xml`.
- A Skin is a stylesheet in `apps/harness/skins/` that refers only to those
  variables. Two ship: **Bubbles** (the question in a tinted bubble, code in
  cards) and **Transcript** (a flat document). `tests/test_skins.py` fails any
  Skin that names a colour of its own or leaves part of the drawer unstyled.
- The Skin is chosen by name in `~/.config/osiris/harness/skin`; anything else
  means Bubbles. Choosing Skins in Appearance comes with Skin sets (P3.4).
- The drawer watches the theme engine's current-theme file and the Skin file,
  so switching either retints or reshapes it while it is open.

### Where conversations are kept

The conversations themselves are the Engine's: opencode keeps every session's
messages in `~/.local/share/opencode/opencode.db`. Osiris keeps the record of
them, the Harness log, in which every entry names its session. The drawer's
history will be built from that log, so changing the Engine never loses the
record. Today the drawer holds only its current session in memory, and a
restart starts a new one.

### Placement

GTK4 on X11 gives an application no way to place its own window, so the
`harness-drawer@osiris` extension does it: it finds the window by its GTK
application id, sizes it to the full height of the monitor's work area at the
right edge, keeps it above other windows on every workspace, and slides it in
when it appears or is unminimised. Closing goes through the extension over
D-Bus (`dev.osiris.HarnessDrawer.Close`) so the drawer can slide out before it
is minimised; without the extension the drawer minimises directly. Where the
Harness sits will become the **Skin**'s choice.

The drawer can be dragged wider from its left edge, and the Expand button in
its header fills the work area. Expanded, it follows the desktop's rules like
any maximised window: it covers the dock, which hides until the pointer
reaches it (CONTEXT.md).

### The opencode Engine

opencode 2.0 runs as a background service per user. The adapter runs
`opencode service start` (idempotent), reads the URL and password from
`~/.local/state/opencode/service.json`, and talks to the API under `/api` with
HTTP basic auth. Events stream from `/api/event` as server-sent events.

Every session is opened with a ruleset that sets every action to `ask`, so each
tool that touches the machine stops at a `permission.asked` event and the
Harness answers it. Denying everything instead would strip the tools from the
request, and opencode's free tier refuses such requests outright.

The event stream carries every session on the service, including any opened
by opencode's own terminal app. The Harness acts only on its own sessions: the
one on screen, and any still working on a question. The person can move to
another Conversation while Osiris answers; the one left keeps being answered,
its file requests judged against its own folder, and the sidebar shows a
spinner beside it until it ends.

## Trying it in development

The adapter and the Harness run anywhere Python 3.14 and opencode 2.0 do. The
pieces are tested against events recorded from opencode 2.0.32
(`tests/test_opencode.py`). The GTK pages have tests in `tests/gtk/`, which run
headless under Xvfb and skip where GTK 4 is missing, as in CI today. On a
machine with GTK 4, GtkSourceView 5 and Xvfb (an Arch install has them all):

```
xvfb-run -a python3 -m pytest tests/gtk
```

The Cinnamon extension is checked on an installed system.
