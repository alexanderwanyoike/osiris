# The Harness

The AI built into Osiris (the terms are in [CONTEXT.md](../CONTEXT.md); the
decision is [ADR 0015](adr/0015-harness-owns-tools-rents-engine.md)). Osiris owns
what the Harness may do, how it shows its work and what it keeps; model access
and the agent loop are rented from an **Engine**, opencode first.

## What exists today

The first slice of ROADMAP P3.5:

- **Super+A** opens the bar: one line to ask in, the answer streaming below it.
  Escape hides it and keeps the conversation.
- The bar always shows the model that last answered, the tokens spent in this
  conversation, and the **Provider**'s allowance as "not reported": opencode
  reports tokens and cost per answer but no allowance or reset time, and
  **Usage** is never estimated.
- **It only talks.** Every action the model reaches for (running a command,
  reading a file outside its working directory, editing anything) is rejected,
  and the model is told to answer in words. The bar shows what was refused.
  Allowing actions waits for **Action tiers**.
- **The Harness log** keeps everything: each question before it is sent, each
  answer with the model that gave it and its tokens, every tool call whether or
  not it asked, every rejection and every failure. It is append-only JSON lines,
  readable with any tool:

  ```
  ~/.local/share/osiris/harness/log.jsonl
  ```

Connecting a ChatGPT or OpenCode Go account, and choosing the **Default model**,
come next, on a Providers page in the Harness. Until then the Engine's own
default answers, which only works while opencode's free tier accepts the
request.

## How it fits together

```
apps/harness/main.py          the bar: GTK only, draws the conversation
osiris/harness/conversation   what the bar shows, from the Engine's events
osiris/harness/harness        one conversation: the log and the talk-only policy
osiris/harness/log            the Harness log
osiris/harness/engine         the Engine port and its events
osiris/harness/opencode       the opencode 2.0 adapter
osiris/platform/http          the HTTP port the adapter talks through
provision/harness.py          installs the bar, its D-Bus activation, autostart
```

The bar is resident, like the theme switcher: started at login, or by D-Bus on
first use, and Super+A runs `gapplication action dev.osiris.Harness show`.

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
(`tests/test_opencode.py`); the bar itself is checked on an installed system,
because it is GTK.
