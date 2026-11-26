---
name: skin-review
description: Review a Skin by looking at the desktop wearing it, against the person's words, the brief and the whole desktop, and answer pass, partial or fail. Use when asked to review a Skin before it is called done.
---

# Review a Skin

You are given four things: the Skin's folder, the person's own words for what
they asked, the brief Osiris wrote for the look, and the path of a screenshot
of the desktop wearing the Skin. If any is missing, say so in your verdict line
and review what you can. If you cannot see images, answer
`Verdict: fail - cannot see the screenshot` and stop.

A Skin passes only when it redraws the whole desktop. Once it is worn, no
control should look as it did before, and the desktop should read as one
designed thing that anyone would recognise from the person's words.

## 1. Look

Read the screenshot first, before any style sheet, as the person will see it.
Then read the Skin's `sass/` and `files/` to learn what it styles that the
screenshot cannot show, such as menus, switches and pressed buttons.

## 2. Review three axes, each on its own

### Look: is it what was asked?

- Would someone who read only the person's words recognise this look?
- Does the screen show what the brief promised: its shapes and its signature
  details? Does it leave out what the brief said it would?

Quote the person's words or the brief for every finding.

### Every control: is the whole desktop redrawn?

Go through each part the Skin's `AGENTS.md` lists under "The whole look",
libadwaita apps, the panel, the dock and the launcher among them. For each, say
whether the Skin redraws it or leaves it as the Skin it started from drew it.
Recolouring alone is not a redraw, because the Theme already does that.
When the brief says the Skin is basic, judge only the parts the brief names,
and pass a basic Skin that does them well.

### Craft: does it look designed?

Report only what you can see in the screenshot:

- one small motif stamped again and again where a shape should carry the look
- outlines added around things in place of a shape of their own
- text hard to read against what is behind it
- parts that look as if they came from different Skins
- anything cut off, misaligned or broken

## 3. Decide the verdict

- **fail**: the look would not be recognised from the person's words, or most
  of the parts listed are as the Skin it started from drew them.
- **partial**: some listed parts are not redrawn, the brief is only partly
  on screen, or a craft problem is plain to see.
- **pass**: anything else.

## 4. Report

Answer in exactly this shape, in under 400 words:

```
Verdict: pass - one sentence saying why

## Look
Findings, each quoting the person's words or the brief, or "Nothing found."

## Every control
Each control not redrawn, or "All redrawn."

## Craft
Findings, or "Nothing found."
```

The verdict line comes first and stands alone, because Osiris shows the person
that line and keeps the rest for when they ask.
