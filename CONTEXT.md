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
The look of the desktop apart from its colours: the shapes of the windows, the
panel and menus, the dock and the launcher, and the fonts, icons and cursor.
One **Skin** covers all of them.
_Avoid_: style, theme (for shapes), skin set

**Skinpack**:
What a **Skin** is made from and shared as: its label, its style sheets and
pictures with named gaps for the **Theme**'s colours, and its fonts, icons and
cursor. One file when shared; nothing in it runs.
_Avoid_: skin file, preset

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
appears. The person knows it as **Osiris**: everything they see names it Osiris
("Ask Osiris"), never the Harness, which is the project's own word for it.
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
already attached: a key, the panel button, a file, selected text, the terminal,
a setting.
_Avoid_: trigger, integration

**Compact** / **Expanded**:
The **Harness**'s one surface when narrow, showing the **Conversation** alone, and when wide enough to show its **Conversations** and the **Canvas** beside it.
_Avoid_: bar, drawer, panel (for the Harness)

**Canvas**:
The part of **Expanded** where the **Harness** shows whatever a **Conversation** is making or looking at: a document, an image, code, a change, a running **Program**, a **Theme**, anything.
_Avoid_: artifact, preview pane

**Action tier**:
How far an action of the **Harness** reaches, which decides whether it asks
first: a look, an undoable change, or a change that cannot be undone or is not
the person's own.
A person can **allow everything**: then the **Harness** refuses nothing, runs
commands and touches any file, and the model is told so. It is the person's
choice, off until they turn it on.
_Avoid_: permission level

**Admin password card**:
Where the **Harness** asks for the administrator password when a command it
runs uses sudo: the exact command, in the **Conversation** that ran it, with
Allow and Deny. Any other program's `sudo -A` gets a dialog of the same kind,
naming that program.
_Avoid_: sudo prompt, password popup

**Conversation**:
A run of questions and answers with the **Harness**, held by the **Engine** as one of its sessions; it continues until the person starts a new one.
_Avoid_: session, thread, chat

**Project**:
A folder the person works in, or the root of the git repository it sits in, as the **Engine** defines it; its instructions to the **Harness** are its AGENTS.md.
_Avoid_: workspace, group, folder (for this)

**Harness log**:
The kept record of everything the **Harness** sent to a model and every action
it took, with its result.
_Avoid_: history (for this), audit trail

**Harness memory**:
What the **Harness** has learned about the person, kept as readable lines they
can edit or delete.
_Avoid_: context, profile

**Program**:
Anything the **Harness** builds for the person to keep and use, installed and
shared as one thing: an app, a script, a command, a website, an automation, a
new tool for the **Harness**. Its **Program manifest** says how it runs.
_Avoid_: app (for all of these), skill, plugin

**Skill**:
How the **Harness** goes about a kind of task, written as instructions it
follows. A **Skill** changes how the **Harness** works; it is not a **Program**.
_Avoid_: program, prompt

**Program manifest**:
What a **Program** is, what it may touch, and how it runs, read before it is
installed.
_Avoid_: metadata

## Relationships

- A **Theme** never carries shape. A **Skin** takes its colours from the
  **Theme**, keeping only the few that make it recognisable.
- Switching **Theme** keeps the **Skin**; switching **Skin** keeps the **Theme**.
- A **Skin** is built from its **Skinpack** with the **Theme**'s colours filling
  its gaps, again on every **Theme** switch (ADR 0019).
- **Skins** that ship with Osiris improve with each upgrade. A **Skin** a person
  makes or opens is theirs, kept out of sight beside their **Themes**, and an
  upgrade never touches it. Sharing one exports its **Skinpack**.
- The **Boot screens** keep Osiris's own shape, and the **Wallpaper** belongs to
  the **Theme**.
- Osiris ships seven **Skins**: Osiris, Colloid, Graphite, Orchis, Qogir, Jasper
  and elementary. Osiris's own is adw-gtk3 recoloured; the others are built from
  their upstream sources.
- An upgrade of Osiris never overwrites a person's choice: their **Theme**,
  **Skins**, keybindings, dock and the files they edit. What Osiris keeps in a
  home is upgraded once, at the next login, and what runs in a session restarts
  onto the new version by itself.
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
- The **Harness** never splits a **Conversation** on its own; a new one starts only
  when the person asks. Branching a **Conversation** makes a new one that
  remembers where it came from.
- A **Conversation** belongs to at most one **Project**: the one it was started in.
  Osiris defines no project format of its own; a **Project** is what the
  **Engine** and the shared AGENTS.md convention already make it.
- A **Conversation** takes its **Project** from the **Entry point** that opened it
  (the terminal's folder, a file's folder), or from the person's choice before
  the first message; with neither, it has none. It never changes afterwards,
  with one exception: a **Conversation** with none takes the **Project** of the
  first **Program** it creates or changes.
- The **Harness** is one surface, **Compact** or **Expanded**, showing the same
  **Conversation**, history and permissions in both. Which it is follows its
  width, as the person drags it; expanding takes it to the widest and back.
  Its colours belong to the **Theme**.
- Only the person resizes the **Harness**. Something that wants room appears as a
  card in **Compact**, and opening it expands the surface to the **Canvas**.
- What a **Conversation** shows in the **Canvas** belongs to that **Conversation**
  and is there again when it is reopened. The **Canvas** is not limited to any
  kind of content.
- The **Canvas** shows a **Project**'s code for reading: the whole tree, to browse,
  in the **Theme**'s colours. Editing happens in the code editor Osiris ships,
  opened from the **Canvas**; the **Harness** contains no editor (ADR 0016).
- Archiving a **Conversation** keeps it, out of the way; deleting one erases it
  from the **Engine** and from the **Harness log**, and asks first because it
  cannot be undone. Deleting erases the talk, not what it did: a **Theme**
  applied or a **Program** installed stays.
- The **Harness** follows the desktop's rules like any window: **Expanded**, it
  covers the dock, which hides until the pointer reaches it.
- The **Harness** acts only when asked. It is reachable everywhere and watches
  nothing.
- Nothing reaches a model that the person cannot see first; further reading
  happens only through actions in the **Harness log**.
- The password typed in an **admin password card** goes to sudo and nowhere
  else: not to a model, the **Harness log** or any file. Nothing is
  remembered; every command that needs it asks again.
- A look just happens; an undoable change happens with an Undo; a change that
  cannot be undone, or is not the person's own, always asks first. Moving files
  to the Trash is undoable; the **Harness** never empties or bypasses the Trash.
- Every **Program** carries a **Program manifest**; installing one is a change
  that asks first, showing what the manifest allows.
- A **Program** with a face is built from Osiris's own parts, so it follows the
  **Theme** and **Skin** like everything else.
- A **Program**'s source is a **Project** of its own, in `~/Code`, kept in git.
  Every change to it, by the **Harness** or the person, is one atomic commit;
  undoing what an answer changed reverts its commits.
- **Programs** are written in Python, C or C++, Rust, Go or JavaScript, whose
  toolchains Osiris ships, unless the person asks for another language. They look like the
  rest of Osiris unless the person asks otherwise.
- A **Program**'s source is an ordinary project that any editor or coding agent
  can carry on: standard build files and an AGENTS.md. Only its **Program
  manifest** is Osiris's own.
- The **Harness** knows the **Programs** it has built from their sources in
  `~/Code`; there is no other record of them.
- An installed **Program** is a copy of one commit of its source, there like any
  other application: in the applications menu and the launcher, and it can be
  kept in the dock. Changing the source changes nothing installed until the
  person updates it; uninstalling keeps the source and its history.
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
> **Domain expert:** "No. The model only turns the sentence into a **Theme intent** - the photo, a **Harmony**, dark, moody. Osiris's own rules make the colours. And the photo is attached in the **Harness** before anything is sent."
> **Dev:** "And if ChatGPT's limit runs out halfway?"
> **Domain expert:** "It moves to the **Fallback model**, says so, and the **Harness** shows the new **Provider** and its **Usage**. Nothing switches silently."

> **Dev:** "I'm in ghostty in my repo and open the **Harness**. Which **Project** is it in?"
> **Domain expert:** "That folder's, so it reads the repo's AGENTS.md. From the panel button it would have none, unless you picked a folder before your first message."
> **Dev:** "It just made me a **Theme**. Does it open on the right?"
> **Domain expert:** "Not by itself. In **Compact** it's a card; open it and the surface goes **Expanded**, with the **Theme** in the **Canvas** beside the **Conversation**. The **Canvas** shows whatever the **Conversation** is working on, its code included, which you edit in Code."

## Flagged ambiguities

- Today's theme manifest (`shell/themes/*.json`) carries `ui.gtk`, `ui.icons`,
  `ui.cursor` and `ui.font` beside its colours: what is called a theme there
  bundles a **Theme** with parts of several **Skins**. Resolved: those fields
  belong to **Skins**.
- "session" and "thread" were used for one exchange with the **Harness**:
  resolved, it is a **Conversation**; "session" stays the **Engine**'s word.
- "artifact" was used for what the expanded **Harness** shows: resolved, the
  place is the **Canvas** and it holds anything, a **Program** being one case.
- "bar", "drawer" and "panel" were used for the **Harness**'s surface: resolved,
  it is **Compact** or **Expanded**; "panel" is Cinnamon's.
