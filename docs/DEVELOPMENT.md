# Developing Osiris

How to work on this, and the things that have already cost a day each.

## The loop

Everything is tested against a libvirt VM called `osiris-dev`, provisioned from
this repository. There is no container path and no "run it on your host"
path - the desktop, the theme engine and the installer all act on a real
system, and a VM is the only honest place to watch them do it.

Install it from the ISO (see below), then add the repository share to the
guest's `/etc/fstab`:

```
osiris /home/<user>/osiris virtiofs rw,nofail 0 0
```

The repository is shared into the guest over virtiofs, mounted at
`/home/<user>/osiris`. Editing on the host and re-running a provisioner in the
guest is the iteration loop; nothing has to be copied.

Reinstalling the theme system after an edit:

```
python3 /home/<user>/osiris/provision/themes.py --repo /home/<user>/osiris
```

### Guest networking

The VM uses passt user-mode networking with a port forward from host 2222 to
guest 22:

```xml
<interface type='user'>
  <portForward proto='tcp'><range start='2222' to='22'/></portForward>
  <backend type='passt'/>
</interface>
```

**If the guest has no network, check ufw before anything else.** A host ufw
policy of `drop` on INPUT and FORWARD breaks guest traffic in a way that looks
exactly like a broken guest: DHCP succeeds, DNS resolves, and nothing connects.
This cost a long detour once, during which libvirt's nftables backend and
checksum offload were both blamed and neither was at fault.

## Building the ISO

```
python3 iso/repo.py
sudo python3 iso/profile.py
```

The first builds the `osiris` package as a normal user (makepkg refuses root).
It also compiles the packages Osiris bundles because no official repository
has them - today only Plank Reloaded, from `iso/bundled/plank-reloaded` - so
their PKGBUILDs' `depends` and `makedepends` must be installed first; makepkg
names any that are missing.
The second needs root, because mkarchiso mounts and chroots, and these packages
on the build host: `archiso`, plus `grub`, `freetype2`, `noto-fonts` and
`ttf-firacode-nerd`, from which the medium's boot menu fonts are made, and
`git` with a network connection, to clone oh-my-zsh for the live session.
Budget around 12GB of scratch space and half an hour: the live desktop roughly
doubles what squashfs has to compress. Writes
`build/out/osiris-<version>-x86_64.iso` and leaves the generated profile at
`build/iso-profile` for inspection.

`--generate-only` writes the profile without building, which is the fast way to
check what will go onto the medium.

See [INSTALLER.md](INSTALLER.md) for how to boot and test it.

## How much bash is in here

The project rule is "no bash that we author". The current accounting, which is
worth stating precisely rather than claiming zero:

| | |
|---|---|
| `.sh` files in the repository | **none** |
| `shell=True`, `bash -c`, `sh -c`, `os.system` | **none** |
| Shell used as build, install or hook glue | **none** |

Every process is spawned as an argv array through `provision/run.py`, which
hands it straight to `execve`. Redirection is done in Python. Nothing is
interpolated into a command line, so nothing can be quoted wrongly.

Three things are worth knowing, none of which is a loophole:

**Two generated files are bash.** archiso's `profiledef.sh` is upstream's
releng file with variable assignments appended by `iso/profile.py`, and the
`osiris` package's PKGBUILD is emitted by `osiris/iso/package.py`: assignments
and one `cp`. Neither carries logic of ours; the source is Python, the same
arrangement as a compiler emitting assembly. archinstall wraps `osiris-setup`
in a one-line script of its own when it runs it, which is archinstall's bash,
not ours. Services are enabled with symlinks into `*.target.wants/`.

**22 lines of zsh ship as `/etc/skel/.zshrc`,** authored in
`provision/apps.py`. That is the user's interactive shell configuration, which
is shell by definition. The rule covers what we automate with, not what we
configure.

**systemd `ExecStart=` lines are argv, not shell.** systemd does not involve a
shell unless asked to, and none of ours asks.

Python totals about 5,600 lines across 27 files.

## Things that will bite you

**Writing into a user's home as root.** Use `provision/homes.py`. Provisioning
runs before anyone has logged in, so every directory it creates belongs to root
unless handed back explicitly - and chowning the file you wrote while missing
the `.config` the same call created leaves the user unable to write to their own
configuration directory, forever. That shipped once. It never appeared in
development because the development account had already logged in.

**`os.path.expanduser("~")` is wrong here.** It trusts `$HOME`, which is still
root's under `su <user> -c`. Use `shell/themes/paths.py:home()`, which asks the
process's own identity.

**`partprobe` returns before the device nodes exist.** On a disk that already
held a filesystem, `/dev/vdb2` appeared 1.7 seconds after the partition table
was re-read, and the `mount` in between failed intermittently.
`install.wait_for_devices()` exists for this.

**A `Gtk.Button` takes the pointer across its whole area.** A `Gtk.MenuButton`
nested inside one renders, highlights on hover, and never fires. Wrap the
button in a `Gtk.Overlay` and put the menu in the overlay.

**`pkill -f <pattern>` over SSH matches its own command line.** The remote shell
is running a command string that contains the pattern, so it kills itself and
whatever you chained after it silently never runs. Write the pattern so it
cannot match itself, e.g. `osiris-appear[a]nce`.

**`Adw.Application` is single-instance.** Launching it again just re-activates
the running window, so an app you think you restarted is still the old build.
Check the process start time if a change seems not to have landed.

**pacman block-buffers when its output is a pipe.** It prints "Retrieving
packages..." and then nothing for fifteen minutes. `run.stream()` gives long
commands a pseudo-terminal for exactly this reason.

## Testing by screenshot

The VM is driven with `virsh screenshot` and `virsh send-key`. Two cautions,
both learned the hard way:

- **Judge from crops, not from the downscaled whole.** Deciding whether a panel
  rendered from a thumbnail of a 1280x800 screen produced two confident wrong
  answers in one session. Crop and zoom, or sample the pixel.
- **Confirm the process you are looking at is the one you just changed.**

## Regenerating assets

```
python3 branding/scripts/make-logo-mask.py      # branding/logo-mask.png
python3 branding/scripts/make-terminal-logo.py  # branding/logo.txt
python3 shell/themes/wallpaper.py               # all theme wallpapers
python3 shell/themes/preview.py                 # all picker thumbnails
```

The first two need `rsvg-convert`, ImageMagick and `chafa`, and are run on a
development machine; their outputs are checked in and shipped so the target
needs no SVG stack. The last two need numpy and Pillow, which are installed on
the target too - that is what lets a theme written on the machine generate its
own artwork.

Bump `preview.RENDERER_VERSION` when changing what the wallpaper or preview
renderers draw, or cached user assets will keep the old artwork.
