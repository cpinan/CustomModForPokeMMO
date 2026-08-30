# CustomModForPokeMMO

Mods for [PokeMMO](https://pokemmo.com), built and verified against client
revision **32920** (theme revision 8). Two of them fix real bugs that show up on
Android handhelds; the rest are cosmetic.

Every mod here was tested on hardware — a Retroid Pocket G2 running Android 15 —
by reading the client's own `layout loop detected` output out of logcat, not by
eyeballing the UI.

---

## The mods

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
