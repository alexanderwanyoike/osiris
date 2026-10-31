# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues on
`alexanderwanyoike/osiris`. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Osiris conventions

- **The repo is public and shown on YouTube.** Nothing from `.notes/` goes in
  an issue or a comment. Explain a decision in product terms.
- **Planned work belongs to a Unit, and a Unit is a milestone.** Create its
  issues with `--milestone "<title>"`. List the Units with
  `gh api repos/alexanderwanyoike/osiris/milestones --jq '.[].title'`. The
  roadmap ([docs/ROADMAP.md](../ROADMAP.md)) links each Unit to its milestone.
- **Every issue carries one `area:` label.** `gh label list` shows them.
- **Use CONTEXT.md's words** in titles and bodies. No emojis.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
