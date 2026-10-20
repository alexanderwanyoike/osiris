# 18. The agent's sudo asks in an admin password card

**Status:** Accepted

## Context

Once a person allows everything (CONTEXT.md), the **Harness** runs commands,
and some need root: `pacman -S`, `systemctl restart`. They run with no
terminal, so sudo has nowhere to ask for the password. ROADMAP P3.7 assumed
sudo would run the askpass helper named in `/etc/sudo.conf` by itself when it
has no terminal. Tested against sudo 1.9.17p2 on Arch, that is wrong:

- sudo runs a helper **only with `-A`**. With no terminal and no `-A`, neither
  `Path askpass` nor `SUDO_ASKPASS` is used; sudo fails "a password is
  required". With `-A` it runs the helper with the prompt as its argument and
  reads the password from the helper's standard output.
- A helper that exits non-zero with no output stops sudo at once ("no password
  was provided"); a wrong password is asked for again, three times in all, and
  counts towards pam_faillock as in a terminal.
- `sudo -k COMMAND` ignores any cached approval and keeps none (sudo(8), -k).
- Arch's sudoers sets `secure_path`, so a command named without a folder is a
  system program.

opencode's service inherits the environment of whoever runs `opencode service
start`, records its pid in `service.json`, and runs each command as `bash -c`,
a child of the service (checked with opencode 2.0.32).

The alternatives:

- **polkit and pkexec.** pkexec runs one program, by policy written per
  action, and its agent's dialog belongs to no Conversation. Agents call
  `sudo`; every command would need rewriting.
- **NOPASSWD in sudoers.** Root for anything the person runs, model or not,
  without asking: against "a change that is not the person's own always asks
  first".
- **Refusing root.** The person copies commands into a terminal; the Harness
  cannot install a package it needs.
- **One wrapper for every program**, replacing `/usr/bin/sudo` or put first on
  everyone's PATH. Osiris would own sudo's behaviour for every terminal, which
  ADR 0012 rules out.

## Decision

The agent's commands find `/usr/lib/osiris/agent-bin/sudo` first on PATH, which
runs `/usr/bin/sudo -k -A` with `SUDO_ASKPASS=/usr/lib/osiris/askpass`. The
Harness sets that PATH and `SUDO_ASKPASS` in its own environment before it
starts the Engine. The helper asks the Harness over D-Bus
(`dev.osiris.Harness.Admin.Ask`); the Harness shows an **admin password card**
in the Conversation that ran the command, and the password goes from the card
to the helper to sudo. Nothing is cached: every command asks.

The guards, all in `osiris/harness/admin.py`, with an attack test for each:

- The helper answers only if its parent is sudo running as root for the same
  person, and it is not root itself. sudo's executable is hidden from the
  person, so sudo is known by its name and effective user; of the set-uid
  programs, only sudo runs a helper before it has a password.
- The Harness takes the caller's pid from the bus, never from the caller, and
  answers only a process running the helper's exact command line under the
  system's Python (run with `-I`, so nothing in the person's environment loads
  into it), whose parent passes the same sudo check.
- The command on the card is read from sudo's own arguments, parsed as sudo
  parses them; a caller naming another command is refused. Shell strings are
  shown whole and labelled; a script says its contents are not shown.
- A card appears only for a sudo descending from the Engine's process, in the
  running Conversation whose latest allowed command runs sudo. Any other
  genuine sudo gets the helper's own dialog, naming the program that ran it.
- The password is not logged, shown or written anywhere; the Harness log
  records the command and whether it was allowed.

## Consequences

- An agent that runs sudo gets a password prompt it can work with, and the
  person sees the exact command in the Conversation that asked.
- A person in a terminal keeps sudo's own prompt; only `-A` and the agent's
  sudo reach the helper. Programs the Harness starts (Try, Code) inherit its
  PATH, so their sudo asks through the helper too.
- The agent's sudo exists only for an Engine the Harness started. A service
  started elsewhere first keeps its own environment, and the agent's sudo
  there fails for want of a terminal.
- The guards stop anything but a real root sudo's helper from raising a card,
  and keep the card truthful. They do not make the password safe from a
  program already running as the person and set on stealing it: one could
  forge the helper's command line, or replace sudo in the person's own shell.
- The agent's shell is an ancestor of the helper, and with the kernel's
  default `ptrace_scope` of 1 an ancestor running as the person may trace it
  and read the password from its memory. The Harness refuses a helper with a
  tracer (TracerPid in `/proc/<pid>/status`, which the person cannot hide),
  both when the request arrives and again just before the password leaves,
  after the person allows. What remains is a race: attaching in the
  milliseconds between that last check and the helper writing to sudo. The
  helper cannot make itself untraceable (non-dumpable) without hiding its
  executable from the Harness's check; a small set-gid launcher would make it
  untraceable from its first instruction and is the next step if this matters.
- `LD_PRELOAD`, `LD_LIBRARY_PATH` and `LD_AUDIT` do not reach the helper: the
  dynamic loader drops them from set-uid sudo's environment, which the helper
  inherits (checked with sudo 1.9.17 and glibc on Arch).
- A Python string cannot be wiped; the password is dropped once handed over.
- Every sudo asks, so a script calling sudo ten times asks ten times.
