"""Enumerate installable disks.

Split out because picking the wrong disk is the one unrecoverable mistake this
installer can make, and the filtering deserves to be read on its own.
"""
import json
import subprocess

# Enough room for the base system, a desktop and somewhere to put files. The
# ESP alone takes 1G; below this the install succeeds and the machine is
# unusable, which is worse than refusing.
MINIMUM_BYTES = 16 * 1000 ** 3


def human(size: int) -> str:
    """Disk sizes, in the units the manufacturer printed on the box."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1000 or unit == "TB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") \
                else f"{size:.1f} {unit}"
        size /= 1000
    return f"{size:.1f} TB"


def _mounted(device: dict) -> bool:
    """Is this device, or anything inside it, mounted right now?

    Recursive because a mountpoint can be several levels down - a partition
    holding an LVM physical volume, say.
    """
    if any(m for m in device.get("mountpoints") or []):
        return True
    return any(_mounted(child) for child in device.get("children") or [])


def available() -> list[dict]:
    """Disks that can be installed onto, largest first.

    Excluded: anything that is not a whole disk, read-only devices, zram, and
    the medium currently being booted from - installing over the running live
    ISO fails halfway through with an unhelpful I/O error.
    """
    # Deliberately not --nodeps: a disk itself is never mounted, its partitions
    # are. Without the children the booted USB stick looks idle, and it is the
    # one device that must not be offered.
    try:
        output = subprocess.run(
            ["lsblk", "--json", "--bytes",
             "--output", "NAME,PATH,SIZE,MODEL,TYPE,RO,TRAN,MOUNTPOINTS"],
            check=True, text=True, capture_output=True).stdout
        devices = json.loads(output).get("blockdevices", [])
    except (OSError, subprocess.CalledProcessError, ValueError):
        return []

    disks = []
    for device in devices:
        if device.get("type") != "disk" or device.get("ro"):
            continue
        if device.get("name", "").startswith(("zram", "loop", "sr")):
            continue
        size = device.get("size") or 0
        disks.append({
            "path": device.get("path") or f"/dev/{device['name']}",
            "size": size,
            "label": (device.get("model") or "Disk").strip(),
            "transport": (device.get("tran") or "").upper(),
            "too_small": size < MINIMUM_BYTES,
            "in_use": _mounted(device),
        })
    return sorted(disks, key=lambda d: -d["size"])
