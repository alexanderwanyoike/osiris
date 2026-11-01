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
- **The Engine's rules decide what asks** (ADR 0020). opencode's permission
  rules, in its own config where the person can read and change them, allow,
  ask about or deny each action; the last matching rule wins, and they hold for
  every client of the Engine. Sessions are opened with no rules of their own,
  since those would override the person's. See [Permission rules](#permission-rules).
- **What the rules ask about is asked in the Conversation.** The request is
  held and shown as a card: the action and its exact input, with Allow once,
  Always allow here, Deny, and a box to reply instead. Always allow here is
  answered `always`: opencode saves the rule it suggests (`ls *` for
  `ls /etc`) for the whole Project and stops asking there until the rule is
  removed, which the button's tooltip says. A reply refuses the action and
  reaches the model as guidance; Deny tells the model the person said no and
  not to try it another way unasked. A card waits without holding up any other
  Conversation, goes when its answer ends, and every answer is logged
  (`replied`).
- **Unless the person turns on auto mode.** A switch on the Providers page
  (`osiris.harness.trust`) has the Harness answer every request once without a
  card, logged as `allowed` by `auto mode`, and restarts the tool server so the
  model is told. A deny rule still refuses, since the Engine never asks about
  it, and a command using sudo still asks for the password. It is off until
  the person turns it on; a person who had allow everything on is in auto mode.
- **It asks for the administrator password in the Conversation.** When a
  command it runs uses `sudo`, an admin password card appears under the
  answer: "Osiris needs your password to run:" and the exact command, a shell
  string shown whole and labelled, a script marked as not shown. The password
  typed there goes to sudo and nowhere else; Deny fails the command. See
  [Admin passwords](#admin-passwords).
- **It can be steered.** A message sent while Osiris answers waits in
  opencode's inbox, shown as pending above the composer with Edit and Remove,
  and reaches the model at its next step (opencode's default `steer`
  delivery); `session.inbox.delivered` turns it into the next question, and the
  answer it steered ends there. Edit and Remove withdraw it
  (`DELETE /api/session/{id}/inbox/{item}`), Edit putting its text back in the
  composer; Stop withdraws every waiting message and puts them back in the
  composer, so none is sent.
- **It can be cut into.** While Osiris answers, Send now beside Stop sends the
  message the same way and then interrupts with `resume=true`
  (`POST /api/session/{id}/interrupt?resume=true`): opencode stops the step
  under way and goes on at once with the steering input waiting, as its
  documentation for opencode 2.2.4 describes. The interruption ends the answer
  as stopped, keeping what it had said, and is logged (`cut-in`); the Harness
  keeps the session working through that stop, since opencode resumes it.
  With nothing working, Send now sends without cutting in.
- **Files and skills can be picked into a message.** `@` or `/` at the start
  of a word opens a card docked over the message box, as wide as it: `@` lists
  the Project's files, `/` the skills a session in that folder can load
  (`GET /api/skill`, asked afresh each time the card opens, since an Engine
  still loading a folder offers only its own two at first). Typing filters,
  names that start with what is typed first; the arrow keys or the pointer
  choose, Tab or Enter puts the entry in, Escape closes. A picked entry shows
  as a token in the Theme's accent, and goes with the message as an attachment
  (`files` with a `file://` URI, or `skills` by id), each with where it is
  mentioned. Tokens are found again when the message is sent, so one edited
  or deleted since is not sent.
- **It shows its work.** While Osiris answers, a row under the answer pulses
  in the Theme's accent, says in plain words what it is doing ("Thinking",
  "Editing pomodoro/main.py", "Making a theme") and counts the time since the
  question. Every step it took, allowed or refused, is kept under the answer,
  whether the person allowed it, auto mode did, or the Engine's rules ran it
  without asking (named by the tool's `session.tool.input.started`; an Osiris
  tool run from opencode's tool catalogue is read from the catalogue's code),
  folded away as "Used 4 tools", each in the past tense ("Edited
  pomodoro/main.py") or as "Not allowed to run ls /etc". Each step opens to
  what it asked for and what came back, drawn for its kind
  (`osiris/harness/detail.py`): a command's line, output and a failed exit
  status; an edit as a diff of the change the model asked for; what a read or
  search looked at and found; a web search's query or a fetch's address; any
  other tool's name and inputs in words. Output past twelve lines is folded
  until asked for, and a refused step says how the person answered.
- **It shows its plan.** For work in several steps the model keeps a task list
  with opencode's `todowrite` tool, and the answer shows it as it changes:
  each task marked to do, under way, done or dropped
  (`osiris/harness/tasks.py`), kept once the answer ends. Each call carries the
  whole list (`{"todos": [{"content", "status"}]}`, statuses `pending`,
  `in_progress`, `completed`, `cancelled`), so the latest is what is shown; a
  `todowrite` call is not listed as a step. The tool is behind opencode's
  `experimental.todo` switch, off by default in opencode 2.2.4, which the
  Harness switches on unless the person has switched it themselves; being
  experimental, it is one to watch when opencode is upgraded. A Conversation
  reopened from the Engine's history does not bring its task list back.
- **It can go back.** Once nothing is answering, a pencil beside a question,
  shown while the pointer is on it, and an arrow beside the latest answer's
  model and time each return to before that question: opencode's own snapshots
  put the Project's files back and the Conversation drops that question and
  those after it. The pencil puts the question in the composer to change; the
  arrow sends it again as it was. Only the latest answer has the arrow, since
  trying an earlier one again would drop every answer after it unasked. Both first say what will be lost (how many questions, and that
  their files go back) and wait for a yes. Osiris keeps no copies of its own
  (ADR 0005, ADR 0012). See [Going back](#going-back).
- **It shows what an answer changed.** Changes in the Canvas toolbar (its
  plus-minus icon, Osiris's own) opens the Changes group with a tab for each
  question that made commits to Programs, in the order asked with the newest
  on screen (#195): the commits the Harness log
  records with the question (the ones its Undo would revert), each read with
  `git show` (`Programs.patch`) and split into files named under their Program
  (`osiris/harness/changes.py`), each with its lines added and removed, opening
  to its diff, coloured by the Theme's code scheme. Because the log outlives
  the Engine's steps, a Conversation reopened from history offers them too, and
  a Program made from a plain Conversation, which opencode tracks no changes
  for outside a git Project, still has them. Lines picked in a diff and a
  comment typed under it are sent to Thoth as a question naming the file and
  its lines as they are now (`osiris/harness/review.py`), queued if Thoth is
  busy.
- **The Harness log** keeps everything: each question before it is sent, each
  answer with the model that gave it and its tokens, every tool call whether or
  not it asked, every answer to a card, everything auto mode allowed, every change with
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
apps/harness/skins/           Bubbles, Transcript and Studio
apps/harness/harness-drawer@osiris   Cinnamon extension: right edge, full height, slide
apps/harness/harness@osiris   Cinnamon applet: the panel button
osiris/harness/conversation   what the drawer shows, from the Engine's events
osiris/harness/activity       each step of an answer in plain words, and time spent
osiris/harness/markdown       answers as blocks, inline text as escaped Pango markup
osiris/harness/style          colour variables and code scheme from a Theme; Skin choice
osiris/harness/harness        its sessions: the log, and requests held for the person
osiris/harness/rules          the careful starting rules, written into the Engine's config
osiris/harness/unread         the Conversations with an answer not yet seen, kept
osiris/harness/notice         what the desktop is told when an answer ends unread
osiris/harness/tiers          Action tiers: a hint on each Osiris tool, a look or undoable
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
and checks each call as the action `osiris_<tool>`. The starting rules allow
`osiris_*`, since every tool only looks or has an Undo, so they run without a
card; the tier is a hint to the model, not a decision. The model never writes a
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
  variables. Three ship: **Bubbles** (the question in a tinted bubble, code in
  cards), **Transcript** (a flat document) and **Studio** (the sidebar, the
  Conversation and the Canvas as rounded panels on the glass, the accent kept
  for what acts). `tests/test_skins.py` fails any
  Skin that names a colour of its own or leaves part of the drawer unstyled.
- The Skin is chosen by name in `~/.config/osiris/harness/skin`; anything else
  means Studio. Choosing Skins in Appearance comes with Skin sets (P3.4).
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
its header (a chevron, ‹) asks the extension to maximise it, which Cinnamon
animates as it does any window; › brings it back. Expanded, it follows the
desktop's rules like any maximised window: it covers the dock, which hides
until the pointer reaches it (CONTEXT.md).

### The opencode Engine

opencode 2.0 runs as a background service per user. The adapter runs
`opencode service start` (idempotent), reads the URL and password from
`~/.local/state/opencode/service.json`, and talks to the API under `/api` with
HTTP basic auth. Events stream from `/api/event` as server-sent events.

Sessions are opened with no ruleset of their own: a session's rules come after
the config's and win even over its denies, so sending any would override the
person's. Whatever the rules ask about stops at a `permission.asked` event
and the Harness answers it with the person's card, or at once in auto mode.

A step's details come from the same stream, tied together by the call's id:
`session.tool.called` carries the call's input, `permission.asked` names the
call in `source.id`, and `session.tool.success` (its text output and, for a
command, `metadata.exit`) or `session.tool.failed` (its `error.message`)
reports how it ended. As observed with opencode 2.2.4.

The event stream carries every session on the service, including any opened
by opencode's own terminal app. The Harness acts only on its own sessions: the
one on screen, and any still working on a question. The person can move to
another Conversation while Osiris answers; the one left keeps being answered,
its file requests judged against its own folder, and the sidebar says
"Working" beside it until it ends.

### Permission rules

opencode 2's rules are a list of `{action, resource, effect}`, each `allow`,
`ask` or `deny`; the last match wins (opencode.ai/v2/docs/permissions). With no
config it allows everything but reading `.env` files, and does not ask before
paths outside the folder. So on every start the Harness adds careful starting
rules to each of two configs that has no `permissions` key
(`osiris/harness/rules.py`):

- `~/.config/opencode/opencode.json`: ask by default; allow reading, globbing
  and searching, web lookups, questions, skills, subagents, opencode's tool
  catalogue (`execute`), the task list (`todowrite`) and the Osiris tools
  (`osiris_*`); ask before `.env` files (but not `.env.example`) and anything
  outside the folder (`external_directory`). Commands, edits and other servers'
  tools fall to the default and ask.
- `~/Code/.opencode/opencode.json`: allow `edit`. Inside a Project opencode
  names an edit by its path from the Project, so a rule cannot name `~/Code` by
  path; opencode reads this config for every Project below `~/Code`, where each
  Program's changes are commits. Conversations with no Project, which run in
  home, still ask before editing.

The same start switches on opencode's task list (`experimental.todo`) unless
the config already says either way.

A config that already has `permissions`, even an empty list (opencode's own
defaults), is the person's and is never changed; nor is one that is not plain
JSON, or one kept as `opencode.jsonc`. opencode reloads its config when it
changes.

Checked against opencode 2.2.4: a saved `always` beats any `ask` and loses to a
config `deny`; it is listed at `GET /api/permission/saved` and removed with
`DELETE /api/permission/saved/{id}`, which Thoth does not offer yet.

### Going back

`Harness.go_back` stages opencode's revert to before the question's message
(`POST /api/session/{id}/revert/stage` with `files: true`), which puts the files
back at once and names each with its diff, then keeps it
(`POST .../revert/commit`), which drops the later questions from the
Conversation. Checked against opencode 2.2.4:

- A snapshot covers the session's folder inside a git worktree: tracked files
  and untracked ones up to 2 MiB. Ignored files, files outside the folder and
  git metadata are not covered. What was staged in git is left as it was.
- Outside a git repository opencode restores no files and stages no snapshot.
  Thoth then cancels the revert (`DELETE .../revert`) and says the files cannot
  be put back, rather than going back with the files still changed
  (`could-not-go-back` in the log).
- opencode refuses while the session runs, so Go back is offered only once
  nothing is answering.
- Snapshots live in opencode's own object store under its data folder; it
  documents no rule for pruning them (opencode.ai/v2/docs/snapshots), and
  `"snapshots": false` in its config stops new ones.
- Osiris's own changes, a Theme or a Skin, are not in the snapshot; each keeps
  its own Undo.

Each go back is logged as `went-back` with the message, the files put back and
how many questions were dropped, so a reopened Conversation matches the log's
changes to the answers still there.

### Unread and notifications

An answer that ends, finished or failed, while the person is not looking at
it leaves its Conversation unread: the drawer was put away, or another
Conversation was on screen. One the person stopped is not. Each row in the
sidebar says how its Conversation stands (`osiris/harness/status.py`):
"Waiting for you" while an approval or admin password card is open, "Working"
while it answers, "Done" with the title in bold while an answer is unread.
The desktop gets a notification, "Osiris replied" or "Osiris could not
finish", with the Conversation's title and the first line of the answer; a
Conversation that starts waiting while the person is not looking gets "Osiris
is waiting for you" with what it is asking. Working and Waiting come from the
running Harness and are not kept across a restart; Done is. Clicking it activates `app.open-conversation` with
the session, which brings the drawer in on that Conversation.

Opening a Conversation, or bringing the drawer back to it, marks it read and
withdraws its notification; so do archiving and deleting it. Each notification
is sent under its session, so a newer answer replaces the older one. Unread
sessions are kept one per line, so they survive a restart of the Harness:

```
~/.local/state/osiris/harness/unread
```

On Cinnamon, GLib sends the notification to `org.freedesktop.Notifications`
(nothing owns `org.gtk.Notifications` there) and routes the click back to the
running Harness itself, which is why the action works only while it runs; it
is resident, so it does.

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
