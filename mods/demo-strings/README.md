# Demo Strings

**Type:** strings mod · **Purpose:** worked example

## What it does

Renames two menu labels, and nothing else:

| id | vanilla | after |
|---|---|---|
| 1190 | Mod Management | Mod Management [pmmod] |
| 1191 | Get Mods | Browse Mods |

It exists to show the smallest possible strings mod that actually loads, and to
give you something whose effect is visible on the login screen without entering
the game.

## How a strings mod is put together

`info.xml` declares the files, one `<string>` element per file:

```xml
<strings string_revision="1">
    <string path="data/strings/strings_en_pmmod_demo_strings.xml"/>
</strings>
```

The file itself is marked `is_primary="0"` — a secondary container. It lists
only the ids it overrides; everything else falls through to the client's own
`data/strings/strings_en.xml`, which is the primary.

```xml
<strings lang="en" lang_full="English" is_primary="0">
  <string id="1190">Mod Management [pmmod]</string>
</strings>
```

To find the id for a piece of text, search the client's `strings_en.xml` for the
text itself.

## Storyline text is different

NPC dialogue does not live in `strings_en.xml` — it comes out of the ROMs and
uses a different root element and a three-part key:

```xml
<ds_strings_archive archive_type="0" lang="en" region_id="3">
  <string block_id="0" entry_id="120" table_id="213">…</string>
</ds_strings_archive>
```

Dump it first with **Settings → Utilities → Dump Storyline Strings**. Note the
`region_id` there runs 0–4 with Johto as 4, which is *not* the same id space the
sprite folders use (`0/1/2/3/10`).

## Install

Import, enable, restart, and look at the login-screen menu.
