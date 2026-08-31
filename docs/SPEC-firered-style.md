# SPEC — FireRed visual grammar

_Measured pixel-by-pixel from the six screenshots in `PokemonFireRedRef/` on 2026-08-30._
_Every value below is read off the reference art, not eyeballed._

## The finding

FireRed does **not** have one window style. It has **one grammar with a swappable accent**.
Every panel in every screen is the same four-band construction:

```
outer dark  →  ACCENT band  →  light bevel  →  flat fill
   2px           1-3px           1-2px
```

Change the accent and you change the screen. That is what makes the whole theme
procedural: one `frame(rect, accent)` function reproduces every window in the game.

## The four-band table

| window | outer | accent band | bevel | fill | corner |
|---|---|---|---|---|---|
| battle message | `#283030` ×2 | `#C8A848` ×3 gold | `#E0D8E0` ×2 | `#285068` navy | **chamfered 45°** |
| battle command menu | `#283030` ×2 | `#8888C8` ×1 / `#706880` ×2 lavender | `#D8D0D8` ×1 | `#F8F8F8` white | **square** |
| battle HP box | `#506860` ×1 shadow | `#203800` ×1 olive | `#D8D0B0` ×1 | `#F8F8D8` pale | rounded |
| bag item list | `#686868` ×2 | `#F0C870` ×3 / `#D0B050` ×2 gold | `#E8E0A8` ×1 | `#F8F8C8` pale yellow | square |
| trainer card | `#606070` ×2 | `#A0A0A0` ×1 | — | `#F8F8F8` white | rounded |
| summary sprite panel | `#606878` ×2 | `#C8A8E8` ×1 / `#B088D0` ×1 lavender | — | `#F8F8F8` | square |

Note the two corner treatments. The message box steps its gold band in diagonally over
4 px; the command menu keeps its bands flat and square. Both are needed — chamfer reads as
"dialogue", square reads as "menu".

## Backgrounds are always scanlined

Never a flat fill. Horizontal 1 px stripes, and **the rhythm differs per screen**:

| screen | colors | rhythm | period |
|---|---|---|---|
| bag | `#40B0A0` / `#68C8C0` | 1 : 1 | 2 px |
| trainer card (outside) | `#50C8B0` / `#309890` | 1 : 3 | 4 px |
| trainer card (body) | `#F8F8F8` / `#E0F0F0` | 1 : 1 | 2 px |
| summary | `#F8F0E8` / `#F8A890` / `#F8D0A8` | 9 : 1 : 1 | 11 px |
| summary sprite panel | `#F8F8F8` / `#E8E8E8` | 1 : 2 | 3 px |

This is the cheapest identity win in the whole theme — two colors and a modulo.

## Pill labels

Field labels are rounded capsules, not text on a background:

- capsule `#788090` solid mid-grey, fully rounded ends
- label text `#F8F8F8` white, no outline inside the pill
- value sits outside the pill on the striped background in `#404040`

Used for `No`, `NAME`, `TYPE`, `OT`, `IDNo`, `ITEM`, `TRAINER MEMO`.

## Text carries a hard drop shadow, always

Every string in FireRed is a glyph plus a **1 px hard drop shadow offset by (+1,+1)**.

It is a shadow, **not an outline** — an earlier draft of this spec said outline, which is
wrong. The dark pixels sit to the right and below each glyph pixel and never above or left.
Read a glyph edge, not a colour histogram, and it is unambiguous. Two surfaces agree on the
shape and differ only in tone:

| surface | glyph | shadow |
|---|---|---|
| navy message box `#285068` | `#F8F8F8` | `#685870` |
| blue item bar `#0078C0` | `#F8F8F8` | `#606060` |

"Hard" means fully opaque and one flat colour. The client's default shadow is `#BF000000`,
black at 75%, and stock `title-font` ships `#55000000` — both read as a blur beside a GBA
edge, so `shadow_color` needs an `FF` alpha.

The client supports this directly: `shadow_offset_x`, `shadow_offset_y`, `shadow_color`.
Two stock faces instead use `border_width` for a full surround, `main-border` and
`mechabold`; FireRed has no surrounds, so both become shadows.

**This is the single highest identity-per-byte change in the project** — a handful of
`fontDef` lines, no art at all. Shipped in P1.

## Accent bars

- description bar: `#0078C0` fill, `#005070` ×2 top edge, `#10A8D8` ×1 highlight
- pocket tab: `#F0C870` fill with a `#D88848` underline bar
- card header band: `#68A0D8`
- dex header: `#C0B088` taupe over `#E0D8C0`

## HP bar

- capsule outline `#506858`, white inner cap `#F8F8F8`
- track `#484058` dark
- fill `#58D080` green (yellow and red variants follow the GBA thresholds)
- `HP` label in `#F8D050` gold

## Palette, consolidated

```
STRUCTURE   #283030 outer dark      #686868 outer grey     #606070 card grey
            #606878 panel grey      #506860 olive shadow

ACCENT      #C8A848 gold            #F0C870 gold light     #D0B050 gold dark
            #8888C8 lavender lt     #706880 lavender dk    #B088D0 / #C8A8E8 violet
            #0078C0 blue            #005070 blue dark      #10A8D8 blue light
            #68A0D8 header blue     #203800 olive          #D88848 orange rule
            #F85000 arrow red

SURFACE     #F8F8F8 white           #F8F0E8 cream          #F8F8C8 pale yellow
            #F8F8D8 pale            #E0D8C0 tan            #C0B088 taupe
            #285068 navy fill       #E0D8E0 bevel          #D8D0B0 bevel warm

STRIPE      #40B0A0 / #68C8C0 teal      #309890 / #50C8B0 teal dark
            #F8A890 / #F8D0A8 salmon    #E0F0F0 ice        #E8E8E8 grey

TEXT        #F8F8F8 white           #404040 body           #606060 outline
            #788090 pill grey       #285068 navy
```

## Type badge colors

From Bulbapedia's colour templates, matching the `TYPE` badges on the summary screen
(`FIRE` orange, `FLYING` pale). Game colours: FireRed `#F15C01`, LeafGreen `#9FDC00`.

```
normal  #9FA19F   fire   #E62829   water   #2F97E8   grass    #3FA129
electric#FAC000   ice    #3DCEF3   fighting#FF8000   ground   #915121
flying  #81B9EF   bug    #91A119   ghost   #704170   dragon   #5060E1
dark    #624D4E   fairy  #EF70EF
```
Bulbapedia did not return poison, psychic, rock or steel — take those from the client's
own existing type colours rather than inventing them.

## The reference set

`spriters-resource.com` returns **HTTP 403** to automated fetches, so the sheets could not
be pulled directly; they were supplied locally instead, in `PokemonFireRedRef/001/`:

| file | drives |
|---|---|
| `splash-login.jpg` | the login plate: band proportions at native 240x160 |
| `battle-system.jpg` | the battle screen in situ |
| `HP Bars & In-battle Menu.png` | the HP plate, the FIGHT menu box, and the GBA font |
| `Menu Elements - Pokemon Summary Menu.png` | summary panels, grey pill labels, type badges |
| `Menu Elements - Interface & Bag Screens.png` | bag pockets, list panel, description bar |
| `Menu Elements - PC Interface.png` | PC boxes and slots |
| `Menu Elements - Pokedex.png` | dex list and entry |
| `Menu Elements - Type _ Status Icons.png` | type badges and status icons |

The kits **confirm the measurements taken from the screenshots**, pixel for pixel. The
battle HP plate reads `#506860` shadow, `#203800` olive outline, `#D8D0B0` bevel,
`#F8F8D8` fill; the FIGHT menu box reads `#283030` x2, `#8888C8`, `#706880` x2, `#D8D0D8`,
white fill. Both match the earlier table exactly, so the grammar was right.

The HP Bars sheet also contains **the GBA font itself**, in three palettes with full
upper case, lower case, digits and punctuation. That is the highest fidelity option for
the pixel-font phase and also the most legally exposed thing in the project: it is
Nintendo's typeface. The recommendation remains an OFL face; the sheet is a reference for
letterform proportions, not something to ship.

Still not covered by any reference: the party list, shop, start menu and options. Those
PokeMMO screens are extrapolated from the grammar rather than copied, which the mod
description should say.
