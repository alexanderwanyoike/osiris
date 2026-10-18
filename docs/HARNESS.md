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
- **It only talks.** Every action the model reaches for (running a command,
  reading a file outside its working directory, editing anything) is rejected,
  and the model is told to answer in words. The drawer shows what was refused.
  Allowing actions waits for **Action tiers**.
- **The Harness log** keeps everything: each question before it is sent, each
  answer with the model that gave it and its tokens, every tool call whether or
  not it asked, every rejection and every failure. It is append-only JSON lines,
  readable with any tool:

  ```
  ~/.local/share/osiris/harness/log.jsonl
  ```

Next: a history of conversations in the drawer (the last one reopens after a
restart, any earlier one can be picked up again, and a new one started), then
connecting a ChatGPT or OpenCode Go account and choosing the **Default model**
on a Providers page in the Harness. Until then the Engine's own
default answers, which only works while opencode's free tier accepts the
request.

## How it fits together

```
apps/harness/main.py          the drawer: GTK only, draws the conversation
apps/harness/harness-drawer@osiris   Cinnamon extension: right edge, full height, slide
apps/harness/harness@osiris   Cinnamon applet: the panel button
osiris/harness/conversation   what the drawer shows, from the Engine's events
osiris/harness/harness        one conversation: the log and the talk-only policy
osiris/harness/log            the Harness log
osiris/harness/engine         the Engine port and its events
osiris/harness/opencode       the opencode 2.0 adapter
osiris/platform/http          the HTTP port the adapter talks through
provision/harness.py          installs the drawer, extension, applet, D-Bus activation, autostart
```

The drawer is resident, like the theme switcher: started at login, or by D-Bus
on first use. Super+A and the panel button both run
`gapplication action dev.osiris.Harness show`, which toggles it.

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
by opencode's own terminal app. The Harness acts only on its own session.

## Trying it in development

The adapter and the Harness run anywhere Python 3.14 and opencode 2.0 do. The
pieces are tested against events recorded from opencode 2.0.32
(`tests/test_opencode.py`); the drawer itself is checked on an installed system,
because it is GTK and a Cinnamon extension.
