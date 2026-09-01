"""Package a mod for distribution: archive + checksum + forum post draft."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import build as build_mod
from . import spec

POST_TEMPLATE = """{name} v{version}

{description}

[b]What it changes[/b]
{changes}

[b]Install[/b]
1. Download [b]{filename}[/b] below.
2. In PokeMMO open [b]Mod Management[/b] (login screen, or the menu on Android).
3. [b]Import Mod[/b] and pick the file -- or [b]Open Mods Folder[/b] and drop it in.
4. Tick [b]Enable[/b], save, and restart the client.{theme_step}

[b]Compatible with[/b] client revision {client_revision}{theme_note}

[b]Checksum[/b] (SHA-256)
{sha256}

[b]Credits[/b]
{author}
"""

THEME_STEP = ("\n5. Choose the theme at [b]Settings > Interface > Theme[/b] and "
              "restart once more.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release(src: Path, out_dir: Path, client_revision: str = "?",
            theme_revision: str | None = None, changes: str = "") -> dict:
    src = Path(src).expanduser()
    out_dir = Path(out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = build_mod.read_meta(src)
    artifact = build_mod.build(src, out_dir)
    digest = sha256(artifact)

    is_theme = (src / "info.xml").read_text(encoding="utf-8").find("<themes") >= 0
    post = POST_TEMPLATE.format(
        name=meta["name"], version=meta["version"],
        description=meta["description"] or "-",
        changes=changes or "- (list the visible changes here)",
        filename=artifact.name,
        theme_step=THEME_STEP if is_theme else "",
        client_revision=client_revision,
        theme_note=(f", theme revision {theme_revision}" if theme_revision and is_theme else ""),
        sha256=digest,
        author=meta["author"] or "-",
    )
    post_path = out_dir / (artifact.stem + ".forum-post.txt")
    post_path.write_text(post, encoding="utf-8")
    (out_dir / (artifact.name + ".sha256")).write_text(
        f"{digest}  {artifact.name}\n", encoding="utf-8")

    checklist = out_dir / (artifact.stem + ".checklist.md")
    checklist.write_text(_checklist(meta, artifact), encoding="utf-8")
    return {"artifact": artifact, "sha256": digest, "post": post_path,
            "checklist": checklist}


def _checklist(meta: dict, artifact: Path) -> str:
    link_ok = meta["weblink"].startswith(spec.WEBLINK_PREFIX)
    return f"""# Release checklist — {meta['name']} v{meta['version']}

- [{'x' if meta['name'] else ' '}] `name` set in info.xml ({meta['name'] or 'MISSING'})
- [{'x' if meta['version'] else ' '}] `version` bumped ({meta['version'] or 'MISSING'})
- [{'x' if meta['author'] else ' '}] `author` credited ({meta['author'] or 'MISSING'})
- [{'x' if link_ok else ' '}] `weblink` points at {spec.WEBLINK_PREFIX}… (currently: {meta['weblink'] or 'empty'})
- [ ] icon.png is real art, 48x48
- [ ] `pmmod validate` clean
- [ ] installed and enabled on a real client, `pmmod log` shows "{artifact.name} applied."
- [ ] looked at the change in game (battle / bag / map, whichever applies)
- [ ] third-party art credited, and you have the right to redistribute it
- [ ] posted in Client Customization on forums.pokemmo.com, with the
      thread URL put back into `weblink` before the final build

Distribution: {artifact.name}
"""
