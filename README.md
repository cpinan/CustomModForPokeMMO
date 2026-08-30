# CustomModForPokeMMO

*[Versión en español](README.es.md)*

Mods for [PokeMMO](https://pokemmo.com), built and verified against client
revision **32920** (theme revision 8). Two of them fix real bugs that show up on
Android handhelds; the rest are cosmetic.

Every mod here was tested on hardware — a Retroid Pocket G2 running Android 15 —
by reading the client's own `layout loop detected` output out of logcat, not by
eyeballing the UI.

---

## The mods

Each mod has its own README with the full write-up:
[android-layout-fix](mods/android-layout-fix/README.md) ·
[region-label-unpad](mods/region-label-unpad/README.md) ·
[bobby-fast-strings](mods/bobby-fast-strings/README.md) ·
[only-shiny-sprites](mods/only-shiny-sprites/README.md) ·
[shiny-scale-probe](mods/shiny-scale-probe/README.md) ·
[stadium-battlesprites](mods/stadium-battlesprites/README.md) ·
[demo-strings](mods/demo-strings/README.md)

### `android-layout-fix` — stops the "UI layout loop" warning

PokeMMO's stock Android theme gives one widget contradictory width bounds. In
`data/themes/android/ui/android-settings.xml`:

```xml
<theme name="settings-scrollpane" ref="scrollpane">
    <param name="minWidth"><int>1080</int></param>
    <param name="maxWidth"><int>800</int></param>
```

The two values look transposed. The **minimum** is the half that breaks things:
1080px is wider than that widget can ever be given once the tab strip and
borders come out of the screen, so the layout pass never settles. TWL retries a
bounded number of times, gives up, and logs `layout loop detected`, which the
client reports as *"A UI layout loop issue was detected. You may experience
reduced performance or lag."*

Opening **Settings** triggers it every time.

This mod absolute-includes all 51 stock Android theme files and replaces exactly
one, with the bounds swapped back to `min 800 / max 1080`. Because everything
else is pulled straight from `/data/themes/android/`, client updates to the rest
of the theme flow through untouched.

Verified by elimination:

| `settings-scrollpane` | result on device |
|---|---|
| `min 1080 / max 800` (stock) | loops |
| `min 1080 / max 32767` | still loops — so `min > max` was not the cause |
| `min 500 / max 32767` | no loop, but the controls are squeezed |
| **`min 800 / max 1080`** | **no loop, layout renders correctly** |

**Install:** import it, then pick *Android Layout Fix* at
**Settings → Interface → Theme** and restart.

### `region-label-unpad` — fixes the Pokédex loop on Sinnoh and Unova

Not a client bug. [SupersStrings](https://forums.pokemmo.com/index.php?/topic/188112-supersstrings/)
redefines the five region names as padded two-line labels to make the region
buttons wider:

```xml
<string id="250003">[ Sinnoh ]\n___________________</string>   <!-- 19x U+2581 -->
```

That padded label destabilises the Pokédex layout, and only for the regions
whose content already sits near the threshold — which is why Sinnoh and Unova
loop while Kanto, Hoenn and Johto are fine.

The ids are also not private button labels. The client substitutes them as
`{STRING_250000}`…`{STRING_250004}` inside ordinary sentences — *"A ticket
required to sail between the {STRING_250000} and {STRING_250001} regions"* — so
the brackets and block characters leak into item descriptions too.

This mod puts the plain names back and changes nothing else. SupersStrings keeps
working; you only lose the wider region buttons.

**Install:** it must load **after** SupersStrings — use the down arrow in Mod
Management to place it below, then restart.

### `bobby-fast-strings` — faster text, English and Spanish

Removes the text from the interactions you repeat all day — healing counter,
shop flow, day-care and eggs, EXP chatter, field-move prompts, fishing casts —
so the box advances instantly — plus battle status spam, catch results, evolution
and Repel prompts. 463 entries across twelve rules. Quest directions and story
dialogue are left alone, and a global guard keeps item and move descriptions
(966 entries, ~96k characters) off limits no matter what a rule matches.

It is **generated, not hand-written**: `pmmod strings fasttext` reads your own
client's `Settings → Utilities` dumps and applies six regexes from `rules.json`.
Nothing is copied from anyone else's mod, it survives client patches by being
re-run rather than hand-fixed, and any language the client ships comes free.

PokeMMO translates its UI into eleven languages but not the storyline — only 8 of
Kanto's 3,607 storyline ids exist in the translated set. Since silencing is
language-neutral, one storyline file serves every player and Spanish only needs
its own UI file.

### `only-shiny-sprites` — hides every non-shiny in battle

The client tells normal and shiny apart by filename alone — `25-front-n.png`
versus `25-front-s.png` — so this mod ships a fully transparent PNG for every
`-n` file across the gen 1–5 dex, including the `-m`/`-f` gendered
variants. 1,947 files, all the same handful of transparent bytes, which
is why the archive is under 450 KB.

It ships **no** `-s` files. Shinies are not overridden, fall back to the ROM
sprite, and render exactly as they always did. Normal encounters draw nothing at
all, so a shiny is impossible to miss.

Only the enemy side is blanked; your own Pokémon renders normally. Covers dex ids 1–649; alternate forms and event
costumes use higher sprite ids and are not blanked.

### `shiny-scale-probe` — a throwaway diagnostic

Ships only the three scale tables, no sprites, with deliberately extreme values
for common early-route species (some at `1`, some at `4`, against a default of
`3`). One wild encounter answers whether the scale tables apply to sprites a mod
has *not* replaced — which decides whether "make shinies bigger" is ten lines of
text or a per-species asset pull. Delete it once you have the answer.

### `stadium-battlesprites` — Pokémon Stadium 2 battle sprites

299 animated GIFs, front and back, with a per-species scale table.

> Rendered from Pokémon Stadium 2 model rips. Check that you are comfortable
> redistributing them before publishing this folder anywhere.

### `demo-strings` — a worked example

Overrides two menu labels. Useful only as a template for how a strings mod is
put together.

---

## Installing any of them

1. Download the `.mod` from `dist/`.
2. In PokeMMO open **Mod Management** — from the login screen menu on desktop,
   or the hamburger menu on Android.
3. **Import Mod** and pick the file, or **Open Mods Folder** and drop it in.
4. Tick **Enable**, save, and restart the client.
5. Theme mods also need selecting at **Settings → Interface → Theme**, then one
   more restart.

### Things that will trip you up

* **Updating a mod means deleting it first.** The client refuses an import when
  a mod of the same name already exists — *"A mod with that name already
  exists, please delete it before trying to import it again."* Use **Delete
  Mod**, then import the new build.
* **The list re-sorts as you toggle.** Disabling a mod drops it toward the
  bottom, so the row you were aiming at moves under your finger. Re-read the
  list after each toggle instead of trusting positions.
* **Order decides who wins.** When two strings mods override the same id, the
  one *lower* in the list is applied last and takes effect. The up/down arrows
  set that order. `region-label-unpad` only works if it sits below
  SupersStrings.
* **Enabling a theme is not selecting it.** A theme mod does nothing until you
  pick it in **Settings → Interface → Theme**. Only one theme can be active at
  a time.
* **A broken mod fails silently at import.** If any file a mod declares does
  not parse, the client refuses the whole thing and the UI shows nothing at
  all — the mod simply never appears in the list. The reason is only in the
  log: `String with path ... is not valid`. Worth knowing that XML forbids
  `--` inside comments, which is exactly how this bit us.
* **Check the log rather than guessing.** `log/mods.log` prints
  `<mod> applied.` for each one that loaded, and `is disabled, skipping.` for
  the rest. On Android the same lines go to logcat under the `mod` tag.

### Which mods go together

| If you run | Also run | Why |
|---|---|---|
| SupersStrings | `region-label-unpad` | otherwise the Pokédex loops on Sinnoh and Unova |
| `bobby-fast-strings` | nothing extra | it never touches the region names |
| Any Android handheld | `android-layout-fix` | Settings loops without it |

`bobby-fast-strings` and SupersStrings both silence dialogue, so running both is
redundant rather than harmful — whichever sits lower wins on shared ids.

## Building from source

Each folder under `mods/` is the archive laid out exactly as the client reads
it. Zip the **contents** of a folder — not the folder itself, or `info.xml` ends
up one level too deep and the client will not list the mod.

## Compatibility

Built against client revision 32920 / theme revision 8. A theme built for a
newer revision is refused outright, so if a client update breaks one of these,
check `Client Theme Revision` at the top of `log/mods.log` and re-base.

## Credits

* SupersStrings by **superworldsun** — `region-label-unpad` exists to sit
  alongside it, not to replace it.
* The absolute-include pattern for themes is borrowed from
  [pokemmo-port-themes](https://github.com/CodesNL/pokemmo-port-themes).

## Not affiliated with PokeMMO

These are unofficial modifications. The developers do not endorse third-party
add-ons; install at your own risk, and only from sources you trust.
