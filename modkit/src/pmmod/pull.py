"""Pull a PokeMMO client's logs off a handheld: Android over adb, or a
PortMaster/Linux build over ssh.

Retroid ships in both shapes:
  * stock Android + the PokeMMO APK  -> adb, files under /sdcard
  * a Linux CFW (ROCKNIX/ArkOS/muOS) running the PortMaster port
    -> ssh, files under ~/roms/ports/pokemmo
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

WANTED = ["log/console.log", "log/mods.log", "config/main.properties",
          "revision.txt"]

DOWNLOADS = "/sdcard/Download"

# The Android client's package id is eu.pokemmo.client. It keeps the whole
# client tree in *internal* private storage (/data/data/<pkg>/), which adb
# cannot read on a non-rooted device -- the app is not debuggable, so run-as is
# refused too. These external paths are checked anyway because a side-loaded or
# older build may use them.
ANDROID_PACKAGE = "eu.pokemmo.client"
ANDROID_ROOTS = [
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files/pokemmo-client-live",
    f"/sdcard/Android/data/{ANDROID_PACKAGE}/files",
    f"/storage/emulated/0/Android/data/{ANDROID_PACKAGE}/files/pokemmo-client-live",
    "/sdcard/Android/data/com.pokeemu.android/files/pokemmo-client-live",
    "/sdcard/PokeMMO/pokemmo-client-live",
    "/sdcard/PokeMMO",
]

PORTMASTER_ROOTS = [
    "~/roms/ports/pokemmo/pokemmo-client-live",
    "~/roms/ports/pokemmo",
    "/roms/ports/pokemmo/pokemmo-client-live",
    "/roms/ports/pokemmo",
    "/userdata/roms/ports/pokemmo",
]


def adb_bin() -> str:
    found = shutil.which("adb")
    if found:
        return found
    guess = Path(os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"))
    if guess.is_file():
        return str(guess)
    raise SystemExit(
        "adb not found. Install platform-tools, or use --ssh for a "
        "PortMaster/Linux handheld.")


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


@dataclass
class Device:
    serial: str
    label: str


def adb_devices() -> list[Device]:
    out = _run([adb_bin(), "devices", "-l"])
    devs = []
    for line in out.stdout.splitlines()[1:]:
        line = line.strip()
        if not line or "\t" not in line and " " not in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devs.append(Device(parts[0], " ".join(parts[2:]) or parts[0]))
        elif len(parts) >= 2 and parts[1] == "unauthorized":
            raise SystemExit(
                f"Device {parts[0]} is connected but not authorised.\n"
                "On the handheld: accept the 'Allow USB debugging' prompt, "
                "then run this again.")
    return devs


def _adb(serial: str | None, args: list[str], timeout: int = 60):
    cmd = [adb_bin()]
    if serial:
        cmd += ["-s", serial]
    return _run(cmd + args, timeout=timeout)


def find_android_root(serial: str | None) -> str:
    for root in ANDROID_ROOTS:
        r = _adb(serial, ["shell", f"ls {root}/log/mods.log 2>/dev/null"])
        if r.returncode == 0 and "mods.log" in r.stdout:
            return root
    # last resort: search the user-visible storage
    r = _adb(serial, ["shell",
                      "find /sdcard -maxdepth 6 -name mods.log 2>/dev/null | head -5"],
             timeout=120)
    hits = [h.strip() for h in r.stdout.splitlines() if h.strip()]
    if hits:
        return str(Path(hits[0]).parent.parent)
    raise SystemExit(_android_private_storage_message(serial))


def _android_private_storage_message(serial: str | None) -> str:
    installed = _adb(serial, ["shell", f"pm path {ANDROID_PACKAGE}"]).stdout.strip()
    rooted = _adb(serial, ["shell", "su -c id"]).stdout.strip().startswith("uid=0")
    lines = ["No readable PokeMMO client tree on this device.",
             "Looked in:", *[f"  {r}" for r in ANDROID_ROOTS]]
    if installed:
        lines += [
            "",
            f"{ANDROID_PACKAGE} IS installed, so the client is keeping its files in",
            "internal private storage (/data/data/" + ANDROID_PACKAGE + "/).",
            "adb cannot read that on a stock device: the app is not debuggable",
            "(run-as refused) and " + ("root is available -- retry with --su."
                                       if rooted else "there is no root."),
            "",
            "Ways to get the log off anyway:",
            "  1. In game: Mod Management > 'Open Mods Log', then Copy. Paste it",
            "     into any app that can save a file to Downloads, and run",
            "     pmmod pull-logs --downloads",
            "  2. Reproduce it on the desktop client with the mobile theme:",
            "     PokeMMO.sh --theme-mobile   (logs are readable there)",
            "  3. adb backup -f pokemmo.ab " + ANDROID_PACKAGE + "  (needs a tap on",
            "     the device, and pulls the WHOLE app dir including saved",
            "     credentials -- only do this if you accept that).",
        ]
    else:
        lines += ["", f"{ANDROID_PACKAGE} is not installed on this device."]
    return "\n".join(lines)


def pull_adb(dest: Path, serial: str | None = None,
             remote_root: str | None = None) -> tuple[Path, list[str]]:
    root = remote_root or find_android_root(serial)
    dest.mkdir(parents=True, exist_ok=True)
    got: list[str] = []
    for rel in WANTED:
        target = dest / Path(rel).name
        r = _adb(serial, ["pull", f"{root}/{rel}", str(target)], timeout=180)
        if r.returncode == 0 and target.exists():
            got.append(rel)
            continue
        # Android 11+ blocks `adb pull` out of Android/data on some OEM builds
        # while `adb shell cat` still works. exec-out keeps the bytes clean.
        cmd = [adb_bin()] + (["-s", serial] if serial else []) + \
              ["exec-out", "cat", f"{root}/{rel}"]
        blob = subprocess.run(cmd, capture_output=True, timeout=180)
        if blob.returncode == 0 and blob.stdout:
            target.write_bytes(blob.stdout)
            got.append(rel + " (via exec-out)")
    listing = _adb(serial, ["shell", f"ls -la {root}/data/mods 2>/dev/null"])
    (dest / "mods-dir-listing.txt").write_text(listing.stdout or "(no data/mods)",
                                               encoding="utf-8")
    (dest / "SOURCE.txt").write_text(
        f"adb\nserial: {serial or 'default'}\nremote root: {root}\n",
        encoding="utf-8")
    return dest, got


def _ssh_base(target: str, port: int, key: str | None) -> list[str]:
    cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-p", str(port)]
    if key:
        cmd += ["-i", os.path.expanduser(key)]
    return cmd + [target]


def find_ssh_root(target: str, port: int, key: str | None) -> str:
    for root in PORTMASTER_ROOTS:
        r = _run(_ssh_base(target, port, key) +
                 [f"ls {root}/log/mods.log 2>/dev/null"], timeout=30)
        if r.returncode == 0 and "mods.log" in r.stdout:
            return root
    r = _run(_ssh_base(target, port, key) +
             ["find / -maxdepth 7 -name mods.log -path '*pokemmo*' 2>/dev/null | head -5"],
             timeout=180)
    hits = [h.strip() for h in r.stdout.splitlines() if h.strip()]
    if hits:
        return str(Path(hits[0]).parent.parent)
    raise SystemExit(
        "Could not find a PokeMMO client over ssh.\nLooked in:\n  "
        + "\n  ".join(PORTMASTER_ROOTS))


def pull_ssh(dest: Path, target: str, port: int = 22, key: str | None = None,
             remote_root: str | None = None) -> tuple[Path, list[str]]:
    root = remote_root or find_ssh_root(target, port, key)
    dest.mkdir(parents=True, exist_ok=True)
    got: list[str] = []
    scp = ["scp", "-P", str(port)]
    if key:
        scp += ["-i", os.path.expanduser(key)]
    for rel in WANTED:
        out = dest / Path(rel).name
        r = _run(scp + [f"{target}:{root}/{rel}", str(out)], timeout=180)
        if r.returncode == 0 and out.exists():
            got.append(rel)
    listing = _run(_ssh_base(target, port, key) +
                   [f"ls -la {root}/data/mods 2>/dev/null"], timeout=30)
    (dest / "mods-dir-listing.txt").write_text(listing.stdout or "(no data/mods)",
                                               encoding="utf-8")
    (dest / "SOURCE.txt").write_text(
        f"ssh\ntarget: {target}:{port}\nremote root: {root}\n", encoding="utf-8")
    return dest, got


def pull_logcat(dest: Path, serial: str | None = None) -> tuple[Path, list[str]]:
    """The Android client mirrors its own log to logcat under tags like
    `f.qh0`, `mod` and `f.i99`, so logcat is a usable substitute when the
    private client tree is unreachable. Includes the TWL layout-loop dump.
    """
    dest.mkdir(parents=True, exist_ok=True)
    pid = _adb(serial, ["shell", f"pidof {ANDROID_PACKAGE}"]).stdout.strip()
    got: list[str] = []

    full = _adb(serial, ["logcat", "-d", "-v", "threadtime"], timeout=180).stdout
    (dest / "logcat-full.txt").write_text(full, encoding="utf-8")
    got.append("logcat-full.txt")

    if pid:
        app = _adb(serial, ["logcat", "-d", "-v", "threadtime", f"--pid={pid}"],
                   timeout=180).stdout
        (dest / "logcat-pokemmo.log").write_text(app, encoding="utf-8")
        got.append(f"logcat-pokemmo.log (pid {pid})")
    else:
        # not running: keep only lines that look like the client's own tags
        keep = [ln for ln in full.splitlines()
                if " f." in ln or " mod " in ln or ANDROID_PACKAGE in ln]
        (dest / "logcat-pokemmo.log").write_text("\n".join(keep), encoding="utf-8")
        got.append("logcat-pokemmo.log (filtered; app not running)")

    (dest / "SOURCE.txt").write_text(
        f"adb logcat\nserial: {serial or 'default'}\npackage: {ANDROID_PACKAGE}\n"
        f"pid: {pid or 'not running'}\n", encoding="utf-8")
    return dest, got


def pull_downloads(dest: Path, serial: str | None = None) -> tuple[Path, list[str]]:
    """Grab log files the player exported to the device's Downloads folder."""
    dest.mkdir(parents=True, exist_ok=True)
    r = _adb(serial, ["shell",
                      f"ls {DOWNLOADS} 2>/dev/null"])
    names = [n.strip() for n in r.stdout.splitlines()
             if n.strip().lower().endswith((".log", ".txt", ".xml"))]
    got = []
    for n in names:
        out = dest / n
        if _adb(serial, ["pull", f"{DOWNLOADS}/{n}", str(out)]).returncode == 0:
            got.append(n)
    (dest / "SOURCE.txt").write_text(
        f"adb\nserial: {serial or 'default'}\nremote root: {DOWNLOADS}\n",
        encoding="utf-8")
    return dest, got
