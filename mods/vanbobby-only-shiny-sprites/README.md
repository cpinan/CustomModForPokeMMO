# Only Shiny Sprites

**Type:** battle sprite mod · **Client:** r32920

## What it does

Hides every **non-shiny opponent** in battle. A normal wild encounter draws
nothing on the enemy side; a shiny draws normally, so it is impossible to miss.

Your own Pokémon is untouched — only the opposing side is blanked. Nothing
outside battle changes either: overworld sprites, party icons, PC boxes and the
Pokédex all render normally.

## How it works

The client tells normal and shiny apart by filename alone:

```
25-front-n.png      Pikachu, enemy side, normal
25-front-s.png      Pikachu, enemy side, shiny
```

So this mod ships a fully transparent 64×64 PNG for every **`-front-n`** file
across the gen 1–5 dex (ids 1–649), including the `-m` / `-f` gendered variants
for species whose ROM sprite differs by gender:

```
sprites/battlesprites/
    1-front-n.png     1-front-n-m.png   1-front-n-f.png
    ... 649 species, 1947 files
```

`front` is the **enemy** sprite and `back` is your own, so shipping only
`-front-` files leaves your side of the battle completely alone.

It ships **no** `-s` files. Shinies are not overridden, so the client falls back
to the ROM's own shiny sprite and they render exactly as they always did.

The archive is under 450 KB — every file is the same handful of transparent
bytes, so it compresses to almost nothing.

## Install

1. Mod Management → **Import Mod** → pick `only-shiny-sprites-1-0.mod`.
2. Enable it, save, restart.
3. Walk into any wild encounter: the enemy side should be empty, your own
   Pokémon unchanged.

## Known limits

* **Covers dex ids 1–649** (gens 1–5). Alternate forms and event costumes use
  their own higher sprite ids and are not blanked, so a normal Rotom form or a
  costumed event Pokémon can still show up. Extend it with
  `pmmod sprites blank <dir> --ids 650-1100` if you hit one.
* **You cannot see what you are fighting.** That is the point, but it does mean
  no visual cue for species, gender or animation state. The name and health bar
  still read normally.
* Only the enemy side is hidden. To blank your own side too, regenerate with
  `pmmod sprites blank <dir> --ids 1-649 --sides front,back`.

## Making shinies bigger

Not included yet, and deliberately so. The scale tables
(`table-front-scale.txt`, `ID=SCALE`) carry the client's own warning
*";Please only include values for overriden sprites!"*, which suggests scaling
may only apply to sprites a mod actually replaces. If that is true, enlarging
shinies means shipping a shiny sprite for every species rather than a few lines
of text.

`shiny-scale-probe` answers that in one wild encounter — see its README.
