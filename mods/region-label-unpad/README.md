# Region Label Unpad

**Type:** strings mod · **Companion to:** SupersStrings · **Client:** r32920

## What it does

Restores the five region names to plain text: `Kanto`, `Hoenn`, `Unova`,
`Sinnoh`, `Johto`.

That fixes the layout loop that hits the **Pokédex when you pick Sinnoh or
Unova**, and it stops region names showing up with brackets and underscores
inside ordinary sentences.

## The bug

This one is not PokeMMO's. [SupersStrings](https://forums.pokemmo.com/index.php?/topic/188112-supersstrings/)
redefines the region names as two-line labels padded with 19 `▁` characters:

```xml
<string id="250003">[ Sinnoh ]\n▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁</string>
```

That is its "Bigger buttons to the 5 regions" feature — the padding row forces
the button to measure wider. The side effect is that the padded label
destabilises the Pokédex layout, and only for the regions whose content already
sits near the threshold, which is why Sinnoh and Unova loop while Kanto, Hoenn
and Johto behave.

There is a second, quieter side effect. Those ids are not private button labels:
the client substitutes them into ordinary strings as `{STRING_250000}` …
`{STRING_250004}`. For example `strings_en.xml` id 100028 reads

> A ticket required to sail between the {STRING_250000} and {STRING_250001} regions.

so the brackets and block characters end up inside item descriptions too.

## The fix

Five lines. Nothing else is touched:

```xml
<string id="250000">Kanto</string>
<string id="250001">Hoenn</string>
<string id="250002">Unova</string>
<string id="250003">Sinnoh</string>
<string id="250004">Johto</string>
```

## Install

1. Mod Management → **Import Mod** → pick `region-label-unpad-1-0.mod`.
2. Enable it.
3. **Order matters** — use the down arrow so it sits *below* SupersStrings in
   the list. The last mod to load wins for a given string id.
4. Save and restart.

Confirm it took by checking `log/mods.log` (or logcat on Android): the line

```
Populating secondary string container[0]: en from data/strings/strings_en_region_label_unpad.xml
```

must appear **after** the one for `sws_strings_en.xml`.

## Trade-off

You lose the wider region buttons that SupersStrings adds. Everything else it
does — the fast text, the sorting, all ~1,797 of its other string overrides —
keeps working untouched.

The better long-term fix is upstream: widen those buttons from the theme rather
than by padding a string that the client also uses inside sentences.
