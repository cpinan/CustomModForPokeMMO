"""Locating the installed PokeMMO client and its moddable surfaces."""
from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path

ENV_VAR = "POKEMMO_HOME"

_CANDIDATES = {
    "Darwin": [
        "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live",
        "~/Library/Application Support/com.pokeemu.macos/pokemmo-client-beta",
        "/Applications/PokeMMO.app/Contents/Resources/pokemmo-client-live",
    ],
    "Linux": [
        "~/.local/share/pokemmo/pokemmo-client-live",
        "~/PokeMMO",
        "~/snap/pokemmo/current/pokemmo-client-live",
    ],
    "Windows": [
        "~/AppData/Roaming/com.pokeemu.win/pokemmo-client-live",
        "C:/Program Files/PokeMMO",
    ],
}


@dataclass(frozen=True)
class Client:
    root: Path

    # --- moddable surfaces -------------------------------------------------
    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def mods_dir(self) -> Path:
        return self.data / "mods"

    @property
    def strings_dir(self) -> Path:
        return self.data / "strings"

    @property
    def themes_dir(self) -> Path:
        return self.data / "themes"

    @property
    def resources_zip(self) -> Path:
        return self.data / "resources.zip"

    @property
    def config(self) -> Path:
        return self.root / "config" / "main.properties"

    @property
    def mods_log(self) -> Path:
        return self.root / "log" / "mods.log"

    @property
    def console_log(self) -> Path:
        return self.root / "log" / "console.log"

    @property
    def dump_dir(self) -> Path:
        return self.root / "dump"

    @property
    def launcher(self) -> Path:
        if platform.system() == "Windows":
            return self.root / "PokeMMO.exe"
        return self.root / "PokeMMO.sh"

    @property
    def native_binary(self) -> Path:
        """The real executable. PokeMMO.sh execs it *without* forwarding
        arguments, so anything with flags has to run this directly."""
        import platform as _p

        if _p.system() == "Windows":
            return self.root / "PokeMMO.exe"
        osdir = "macos" if _p.system() == "Darwin" else "linux"
        arch = "arm64" if _p.machine() in ("arm64", "aarch64") else "x64"
        return self.root / "bin" / osdir / arch / "PokeMMO"

    @property
    def revision(self) -> str:
        f = self.root / "revision.txt"
        return f.read_text().strip() if f.is_file() else "?"

    def is_running(self) -> bool:
        """Best-effort: the client holds its own binary open while running."""
        import subprocess

        try:
            out = subprocess.run(
                ["pgrep", "-f", "PokeMMO"], capture_output=True, text=True, timeout=5
            )
            return out.returncode == 0 and bool(out.stdout.strip())
        except Exception:
            return False


def find_client(explicit: str | None = None) -> Client:
    tried: list[str] = []
    for cand in filter(None, [explicit, os.environ.get(ENV_VAR)]):
        p = Path(cand).expanduser()
        if (p / "data").is_dir():
            return Client(p.resolve())
        tried.append(str(p))

    for cand in _CANDIDATES.get(platform.system(), []):
        p = Path(cand).expanduser()
        tried.append(str(p))
        if (p / "data").is_dir():
            return Client(p.resolve())

    raise SystemExit(
        "Could not locate a PokeMMO client.\n"
        "Pass --client /path/to/pokemmo-client-live or set "
        f"{ENV_VAR}.\nLooked in:\n  " + "\n  ".join(tried)
    )
