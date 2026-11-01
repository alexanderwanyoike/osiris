# Notice

This skill is adapted from two published review skills, merged into one and
rewritten for reviewing a Program that Osiris built.

- **code-review** from mattpocock/skills, by Matt Pocock, under the MIT
  License (LICENSE-MIT): https://github.com/mattpocock/skills
  (`skills/engineering/code-review/SKILL.md`, at commit
  7739eaed7f8f3915437a8def198a6d0d7206dbc7). The Spec and Standards axes,
  reviewing them separately, and the baseline of code smells come from it.

- **code-review** from anthropics/claude-plugins-official, by Anthropic, under
  the Apache License 2.0 (LICENSE-APACHE):
  https://github.com/anthropics/claude-plugins-official
  (`plugins/code-review/commands/code-review.md`, at commit
  9780cf407f5593727b668bae95a0c4ae2e0de1ae). The Bugs axis comes from it:
  looking only at the change, scoring each finding for confidence, keeping only
  the ones above a threshold, and the list of false alarms not to raise.

Changes from both: their steps for spawning several agents, reading issue
trackers and posting to pull requests were removed; one reviewer reports all
three axes under a single pass, partial or fail verdict, and Standards is
judged against the Program's own CODING_STANDARDS.md.
