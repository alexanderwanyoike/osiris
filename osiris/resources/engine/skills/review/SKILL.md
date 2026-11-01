---
name: review
description: Review a change to a Program along three separate axes (Spec, Standards, Bugs) and answer pass, partial or fail. Use when asked to review a Program before it is called done.
license: Adapted from MIT and Apache-2.0 work; see NOTICE.md
---

# Review a change to a Program

You are given three things: the Program's folder, the person's own words for
what they asked, and the commit the change started from. If any is missing,
say so in your verdict line and review what you can.

## 1. Pin the change

Run git with the Program's folder as the working directory, never with
`git -C` or `cd`:

- `git log --oneline <start>..HEAD` for the commits in the change
- `git diff <start>` for the change itself
- `git status --short` for anything not yet committed

If the start commit does not resolve and nothing is uncommitted, there is no
change to review: answer `Verdict: fail - no change to review` and stop.

Read whole files where the diff alone cannot answer a question, and only then.

## 2. Review three axes, each on its own

A change can pass one axis and fail another: code that follows every rule but
builds the wrong thing, or code that does exactly what was asked but breaks the
Program's conventions. Review each axis separately and never let one excuse or
outweigh another.

### Spec: does it do what the person asked?

Report:

- what the person asked for that is missing or only partly done
- what the change does that nobody asked for
- what looks done but behaves wrongly

Quote the person's words for every finding.

### Standards: does it follow the Program's own rules?

Read the Program's `CODING_STANDARDS.md`, and its `AGENTS.md` and `CONTEXT.md`
if they exist. For each breach, cite the file and the rule. Skip anything a
linter or formatter checks.

On top of those rules, look for this fixed baseline of code smells. Each is a
judgement call, never a hard breach: name it as "possible Feature Envy" and
quote the hunk. Where the Program's own rules allow what a smell would flag,
the rules win and the smell is not reported.

- **Mysterious Name**: a name that does not say what the thing does or holds.
- **Duplicated Code**: the same logic in more than one place in the change.
- **Feature Envy**: a function that uses another object's data more than its own.
- **Data Clumps**: the same few values always passed around together.
- **Primitive Obsession**: a string or number standing in for a concept that
  deserves its own small type.
- **Repeated Switches**: the same branching on the same kind of thing in
  several places.
- **Shotgun Surgery**: one change forcing scattered edits in many files.
- **Divergent Change**: one file edited for several unrelated reasons.
- **Speculative Generality**: abstraction or options nothing asked for yet.
- **Message Chains**: long `a.b().c().d()` walks the caller should not know about.
- **Middle Man**: a function or class that only passes calls on.
- **Refused Bequest**: a subclass that ignores most of what it inherits.

### Bugs: will the change misbehave?

Look only at the code the change introduces. Report only what you can show is
real:

- code that will not run: syntax errors, missing imports, undefined names
- logic that gives the wrong result whatever the input
- security holes in the new code

Score each finding from 0 to 100 for how sure you are it is real, and keep only
those scoring 80 or more. If you are unsure, read the code that would settle it;
if you are still unsure, drop the finding. A false alarm costs the person more
than a missed nitpick.

Never report as a bug: a problem that was there before the change, style or
quality concerns, something that only happens with input you cannot show,
anything a linter would catch, or a nitpick a senior engineer would not raise.

## 3. Decide the verdict

- **fail**: a bug scored 80 or more, or the main thing the person asked for is
  missing.
- **partial**: part of what the person asked for is missing or wrong, or a rule
  in `CODING_STANDARDS.md` is broken.
- **pass**: anything else. Smells alone never make a verdict worse than pass.

## 4. Report

Answer in exactly this shape, in under 400 words:

```
Verdict: pass - one sentence saying why

## Spec
Findings, each quoting the person's words, or "Nothing found."

## Standards
Findings, each citing its rule or naming its smell, or "Nothing found."

## Bugs
Findings, each with its score, or "Nothing found."
```

The verdict line comes first and stands alone, because Osiris shows the person
that line and keeps the rest for when they ask.

Adapted from two published review skills; see NOTICE.md.
