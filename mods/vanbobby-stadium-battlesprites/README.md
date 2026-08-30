# Stadium 2 Battle Sprites

**Type:** battle sprite mod · **Client:** r32920

## What it does

Replaces the in-battle Pokémon sprites with animated renders of the Pokémon
Stadium 2 models — 299 GIFs covering front and back views, plus a per-species
scale table so they sit correctly on the battle floor.

## Layout

```
sprites/battlesprites/
    1-front-n.gif              Bulbasaur, enemy-facing, normal
    1-back-n.gif               Bulbasaur, your side, normal
    ...
    table-front-scale.txt      ID=SCALE, applied to the enemy-facing sprite
```

The filename grammar the client enforces is
`ID-(front|back)-(n|s)[-(m|f)][-FRAME]`, where `front` is the **enemy** sprite
and `back` is **yours**, `n`/`s` is normal/shiny and the optional gender is
`m`/`f`. An animated GIF must **not** carry a frame id — it already has its own
frames.

`table-front-scale.txt` holds one `ID=SCALE` per line; `;` starts a comment.
Only list species you actually want to override.

## Install

1. Mod Management → **Import Mod** → pick `vanbobby-stadium-2-battle-sprites-1-0.mod`.
2. Enable it, save, restart.
3. Enter any battle.

Battle sprites are resolved lazily, so verbose mod logging will not print a line
per sprite the way it does for icons and overworld art. `<mod> applied.` in the
log plus seeing them in a battle is the confirmation.

## Provenance

Rendered from Pokémon Stadium 2 model rips. They are derived from Nintendo
assets — check you are comfortable redistributing them before republishing this
folder anywhere.

## Note on older builds

An earlier version of this pipeline emitted `sprites/front/1.gif`,
`sprites/back/1.gif` and `sprites/scale.txt`, with no `info.xml`. The loader
reads none of those paths, so that build never appeared in Mod Management at
all. The layout here is the one the client actually reads.
