# 15. The harness owns its tools and surfaces and rents its engine

**Status:** Accepted

## Context

Osiris wants an AI **Harness** built into the operating system that works with
the subscriptions people already pay for: ChatGPT Plus or Pro, OpenCode Go, and
others. A harness is six layers: model access, the agent loop, tools, policy
(permissions and transparency), programs and memory, and the surfaces people
use.

Model access and the agent loop are the hard, commodity, fast-moving layers.
The ChatGPT subscription is reachable only through the Codex OAuth flow, which
OpenAI can change at any time. opencode already does both layers well, supports
these subscriptions, runs headless, and is an official Arch package
(`extra/opencode`), so Arch maintains and updates it.

The other four layers are where Osiris differs from a coding agent: what the
harness may do on this machine, how it shows its work, what it builds and
remembers, and that it looks and behaves like the rest of Osiris.

## Decision

Osiris owns tools, policy, programs and memory, and surfaces, written in Python
like the rest of the project (ADR 0002). Model access and the agent loop are an
**Engine** behind a port (ADR 0003). The first engine adapter is opencode,
run headless.

## Considered options

- **Writing our own harness**, in Python or Rust: owns the hardest layer and the
  most fragile one, the ChatGPT login, with one maintainer.
- **Forking opencode**: everything owned, and a large TypeScript codebase to
  keep merging.
- **Wrapping opencode entirely**: fastest, but its permissions and its idea of
  programs would become Osiris's.
- **pi** as the engine: capable, but npm-only, so Osiris would have to package
  it. It remains a candidate for a later adapter.
- **Rust** for the harness: the wait is the model, and the heaviest process is
  the engine either way; a second language would cost more than it saves. A
  component that measurably needs it may be written in Rust behind its own
  interface.

## Consequences

- Every Osiris install carries opencode, about 200 MB, and with it the opencode
  terminal application.
- The engine port is shaped by what opencode exposes: sessions, tool calls,
  permission requests and streamed events. Another engine has to fit that shape.
