"""Install, enable, disable and list mods in a real client install."""
from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from . import props
from .paths import Client

MOD_EXTS = (".mod", ".zip")


@dataclass
class InstalledMod:
    file: Path
    name: str
    version: str
    author: str
    enabled: bool
    official: bool = False

    @property
    def key(self) -> str:
        """What client.mods.enabled_mods stores: the file name."""
        return self.file.name


def _meta_of(path: Path) -> dict:
    try:
        if path.is_dir():
            raw = (path / "info.xml").read_bytes()
        else:
            with zipfile.ZipFile(path) as zf:
                raw = zf.read("info.xml")
        root = ET.fromstring(raw)
        return {k: root.get(k, "") for k in ("name", "version", "author")}
    except Exception:
        return {"name": path.stem, "version": "?", "author": "?"}


def list_mods(client: Client) -> list[InstalledMod]:
    enabled = set(props.enabled_mods(client.config))
    found: list[InstalledMod] = []
    if client.mods_dir.is_dir():
        for p in sorted(client.mods_dir.iterdir()):
            if p.name.startswith("."):
                continue
            if p.is_dir() or p.suffix.lower() in MOD_EXTS:
                m = _meta_of(p)
                found.append(InstalledMod(p, m["name"], m["version"], m["author"],
                                          p.name in enabled))
    if client.resources_zip.is_file():
        m = _meta_of(client.resources_zip)
        found.insert(0, InstalledMod(client.resources_zip, m["name"], m["version"],
                                     m["author"], True, official=True))
    return found


def install(client: Client, artifact: Path, enable: bool = False,
            force: bool = True) -> InstalledMod:
    artifact = Path(artifact).expanduser().resolve()
    client.mods_dir.mkdir(parents=True, exist_ok=True)
    dest = client.mods_dir / artifact.name
    if artifact.is_dir():
        if dest.exists():
            if not force:
                raise SystemExit(f"{dest} already exists")
            shutil.rmtree(dest)
        shutil.copytree(artifact, dest)
    else:
        if dest.exists() and not force:
            raise SystemExit(f"{dest} already exists")
        shutil.copy2(artifact, dest)
    m = _meta_of(dest)
    mod = InstalledMod(dest, m["name"], m["version"], m["author"], False)
    if enable:
        set_enabled(client, dest.name, True)
        mod.enabled = True
    return mod


def uninstall(client: Client, name: str) -> Path:
    target = _resolve(client, name)
    set_enabled(client, target.file.name, False)
    if target.file.is_dir():
        shutil.rmtree(target.file)
    else:
        target.file.unlink()
    return target.file


def set_enabled(client: Client, name: str, on: bool) -> list[str]:
    current = props.enabled_mods(client.config)
    try:
        key = _resolve(client, name).file.name
    except SystemExit:
        if on:
            raise
        key = name          # disabling something already removed from disk
    if on and key not in current:
        current.append(key)
    if not on and key in current:
        current = [m for m in current if m != key]
    props.set_enabled_mods(client.config, current)
    return current


def set_verbose(client: Client, on: bool) -> None:
    props.set_keys(client.config, {props.VERBOSE_KEY: "true" if on else "false"})


def set_theme(client: Client, theme: str) -> None:
    props.set_keys(client.config, {props.THEME_KEY: theme})


def _resolve(client: Client, name: str) -> InstalledMod:
    mods = list_mods(client)
    for m in mods:
        if name in (m.file.name, m.file.stem, m.name):
            return m
    for m in mods:
        if name.lower() in m.name.lower():
            return m
    raise SystemExit(
        f"No installed mod matches {name!r}. Installed: "
        + ", ".join(m.file.name for m in mods))
