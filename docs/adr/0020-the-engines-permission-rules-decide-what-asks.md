# 20. The Engine's permission rules decide what asks

**Status:** Accepted. Amends 0015.

## Context

ADR 0015 kept policy in the **Harness**: every session was opened with every
action set to ask, and the Harness answered each request by its own **Action
tiers**, rejecting the rest. That made Osiris's policy a second permission
system beside the Engine's own, which the person could neither see nor change,
and which every other client of the same Engine ignored.

opencode 2 already has a complete one. Checked against opencode 2.2.4:

- Rules are a list of `{action, resource, effect}`, each `allow`, `ask` or
  `deny`, the last match winning. They live in its config, where the person can
  read and change them, and apply to every client of the Engine.
- A rule list sent with a session is applied after the config's and wins, even
  over a config `deny`.
- A request the rules ask about is answered `once`, `always` or `reject`.
  `always` saves an allow rule for the Project, kept until removed; a saved rule
  beats any `ask` and loses to a config `deny`.
- Auto mode is the client's: it answers every request it is asked. Deny rules
  never reach the client, so they still hold.
- Inside a Project an edit is named by its path relative to the Project, so a
  rule cannot name `~/Code` by path; a config in `~/Code/.opencode/` applies to
  every Project below it.
- With no config, everything is allowed except reading `.env` files, and paths
  outside the folder are not asked about.

## Decision

The Engine's rules decide what runs, what asks and what is refused. The Harness
sends no rules with a session. What it keeps is the person's side: the
approval card for every request the Engine asks about, the Harness log, and the
admin password card for sudo.

- The card answers as the Engine does: Allow once, Always allow here (saved by
  the Engine for the Project), and Deny, with the box to reply instead.
- **Auto mode** replaces allow everything: the Harness answers every request
  once, without a card, and logs it.
- On first start the Harness writes **careful starting rules** where a config
  has no `permissions`: in the Engine's own config, reads, searches, web
  lookups, questions, skills, subagents, the task list and Osiris's own tools
  are allowed, `.env` files, commands, other tools and anything outside the
  folder ask; in `~/Code/.opencode/opencode.json`, edits inside a Project are
  allowed. A config that already has `permissions`, or is not plain JSON, is
  never touched, so no upgrade overwrites the person's rules.

Action tiers remain only as hints on Osiris's own tools: whether a tool only
looks.

## Consequences

- One set of rules holds wherever the Engine is used, and the person changes
  them in a file they own.
- "Always" outlives the Conversation; a way to list and remove saved approvals
  is still to come.
- Commands now ask instead of being refused: Thoth can run them with the
  person's yes, where before it needed allow everything.
- A sudo request is matched to its session by the commands the Engine reports,
  since the Harness no longer sees every allowed command.
