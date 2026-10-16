# Osiris

An opinionated Arch distribution: a Cinnamon desktop whose every surface follows
one choice of colours and one choice of shapes, installed from a live medium.
Consistency is what Osiris has over other opinionated desktops: every surface,
the AI included, looks and behaves as one system.

## Language

### Appearance

**Theme**:
The colours of the desktop and nothing else: a palette whose colours complement
one another.
_Avoid_: meta theme, colour scheme

**Skin**:
The shape of one surface, with no colours of its own: layout, geometry, styling,
and the base it is built on (GTK base theme, panel layout, dock geometry,
launcher layout, **Harness** placement, fonts, icon set, cursor).
_Avoid_: style, theme (for shapes)

**Skin set**:
A curated bundle of one **Skin** per surface, chosen as a whole; any surface in it
can then be swapped on its own, making it a modified **Skin set**.
_Avoid_: preset, layout

**Theme intent**:
What a **Theme** is asked to be - a seed colour or a **Wallpaper**, a harmony,
light or dark, and a mood - from which its colours are derived.
_Avoid_: prompt (for this), seeds

**Harmony**:
The rule relating a **Theme**'s colours to one another: analogous,
complementary, split-complementary, triadic or monochrome.

**User theme**:
A **Theme** someone made on the machine, which is not held to complementing
colours but is helped towards them.
_Avoid_: custom theme

**Shipped theme**:
A **Theme** that comes with Osiris, whose colours always complement each other.

**Wallpaper**:
The desktop background image, a concept in its own right, which comes from the
user, from a model, or is procedurally generated.
_Avoid_: background (for the image)

**Generated wallpaper**:
A **Wallpaper** made procedurally from a **Theme**'s colours.

**Boot screens**:
The surfaces drawn before anyone logs in: the GRUB menu, the Plymouth splash and
the login greeter.
_Avoid_: boot theme

**System theme**:
The one **Theme** the **Boot screens** use, chosen per machine rather than per
user.

### Harness

**Harness**:
The AI built into Osiris that a person talks to: what it can do, what it is
allowed to do, how it shows its work, what it builds and remembers, and where it
appears.
_Avoid_: assistant, agent, copilot

**Engine**:
What the **Harness** rents for model access and the agent loop, replaceable
without changing the **Harness**; opencode first.
_Avoid_: backend, provider

**Provider**:
A company or service whose models the **Engine** can reach with an account the
person already has: ChatGPT, OpenCode Go, and whatever else the **Engine**
supports.
_Avoid_: subscription (for the company), backend

**Default model** / **Fallback model**:
The **Provider** and model the **Harness** uses unless told otherwise, and the
one it moves to when the default cannot answer.

**Usage**:
How much of a **Provider**'s allowance has been spent and when it resets.
_Avoid_: quota, credits

**Entry point**:
A place in Osiris that opens the **Harness** with what the person is looking at
already attached: a key, the panel, a file, selected text, the terminal, a
setting.
_Avoid_: trigger, integration

**Action tier**:
How far an action of the **Harness** reaches, which decides whether it asks
first: a look, an undoable change, or a change that cannot be undone or is not
the person's own.
_Avoid_: permission level

**Harness log**:
The kept record of everything the **Harness** sent to a model and every action
it took, with its result.
_Avoid_: history (for this), audit trail

**Harness memory**:
What the **Harness** has learned about the person, kept as readable lines they
can edit or delete.
_Avoid_: context, profile

**Program**:
Anything the **Harness** makes that is kept, installed and shared as one thing:
an app with a window, an automation, a new capability for the **Harness**, or a
website.
_Avoid_: app (for all of these), skill, plugin

**Program manifest**:
What a **Program** is, what it may touch, and how it runs, read before it is
installed.
_Avoid_: metadata

## Relationships

- A **Theme** never carries shape; a **Skin** never carries colour.
- Switching **Theme** keeps every **Skin**; switching a **Skin** keeps the **Theme**.
- Choosing a **Skin set** replaces every **Skin**; a modified **Skin set** is kept
  so it can be chosen again.
- A GTK **Skin** is a base that can be recoloured plus a shape layer (ADR 0013).
- Every **Theme** has a **Generated wallpaper**.
- A **Wallpaper** comes from a model only when the **Engine** itself can make
  images; Osiris adds no image model of its own. Further providers may supply
  that later.
- When a **Theme** is created from a **Wallpaper**, its colours are derived from
  that **Wallpaper**; changing the **Wallpaper** of an existing **Theme** does not
  recolour it.
- Every derived **Theme** is produced from a **Theme intent** by Osiris's own
  colour rules, which guarantee its **Harmony** and legibility. A user may then
  override any colour; a model never writes colours, only a **Theme intent**.
- The **Harness** runs on exactly one **Engine** at a time; Osiris owns the
  **Harness** and never the **Engine** (ADR 0015).
- There is one **Harness**; every **Entry point** opens it, with one history and
  one set of permissions. No application has a **Harness** of its own.
- The **Harness** is one surface: it opens as a bar and grows into a panel when a
  task needs room, keeping the conversation. Where it sits and how it grows
  belong to the **Skin**; its colours to the **Theme**.
- The **Harness** acts only when asked. It is reachable everywhere and watches
  nothing.
- Nothing reaches a model that the person cannot see first; further reading
  happens only through actions in the **Harness log**.
- A look just happens; an undoable change happens with an Undo; a change that
  cannot be undone, or is not the person's own, always asks first. Moving files
  to the Trash is undoable; the **Harness** never empties or bypasses the Trash.
- Every **Program** carries a **Program manifest**; installing one is a change
  that asks first, showing what the manifest allows.
- A **Program** with a face is built from Osiris's own parts, so it follows the
  **Theme** and **Skin** like everything else.
- A **Program** is shared as a single file; whoever receives it reads its
  **Program manifest** before installing. Putting anything online uses the
  person's own accounts and always asks first. Osiris runs no servers.
- Everything that shapes how the **Harness** behaves - its instructions,
  **Harness memory**, permissions, models and **Entry points** - is plain text
  the person can read and edit; there is no hidden state. Changing it, whether
  by hand, in Settings or by the **Harness**, is a change that asks first when
  the **Harness** does it.
- **Providers** are not a fixed list in Osiris: whatever the **Engine** can
  reach can be connected, and the **Default model** and **Fallback model** are
  settings, never code.
- The **Harness** moves to the **Fallback model** only when the **Default model**
  cannot answer, and says so; nothing else chooses a model behind the person's
  back.
- The **Provider**, model and **Usage** in play are visible at all times, and
  every request in the **Harness log** records which model answered it.
- **Usage** is shown exactly as the **Provider** reports it, or as not reported;
  never estimated. A limit a **Provider** does not report is learned when it is
  hit and shown until it lifts.
- A machine has exactly one **System theme**; it defaults to the first user's
  **Theme**, and changing it needs an administrator.
- **Boot screens** take colours from the **System theme** but no **Skin**; the
  Osiris mark stays on them. The live medium keeps the Osiris Obsidian **Theme**.

## Example dialogue

> **Dev:** "Nord ships with FiraCode and Papirus - are those part of the **Theme**?"
> **Domain expert:** "No. Fonts and icons are **Skin**. Nord is only its colours; switch to Rose Pine and your font stays."
> **Dev:** "So when someone asks the **Harness** for 'a moody theme from my car photo', does the model pick the colours?"
> **Domain expert:** "No. The model only turns the sentence into a **Theme intent** - the photo, a **Harmony**, dark, moody. Osiris's own rules make the colours. And the photo is attached in the bar before anything is sent."
> **Dev:** "And if ChatGPT's limit runs out halfway?"
> **Domain expert:** "It moves to the **Fallback model**, says so, and the panel shows the new **Provider** and its **Usage**. Nothing switches silently."

## Flagged ambiguities

- Today's theme manifest (`shell/themes/*.json`) carries `ui.gtk`, `ui.icons`,
  `ui.cursor` and `ui.font` beside its colours: what is called a theme there
  bundles a **Theme** with parts of several **Skins**. Resolved: those fields
  belong to **Skins**.
