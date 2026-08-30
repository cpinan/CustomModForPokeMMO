# PLAN — VanBobby FireRed theme

_Written 2026-08-30. Client revision 32920, theme revision 8._

A PokeMMO theme mod that reskins the client in Pokémon FireRed's window grammar. Ships a
desktop theme and a mobile theme from one archive. Tested on desktop only this round; mobile
is wired but unverified.

Companion document: **`docs/SPEC-firered-style.md`** — every colour and band width in this
plan was measured off the six reference screenshots, not eyeballed.

## Decisions taken

| | |
|---|---|
| Scope | Core widget skin + dialogue + **battle HUD, overworld HUD, summary screen** |
| Fidelity | FireRed grammar and palette at the stock atlas resolution — no chunky upscale, no `xywh` geometry changes |
| Font | Bundle an OFL pixel face; Noto stays as the CJK path |
| Art method | Procedural repaint script, re-runnable after client updates |

## Why this shape

The client's whole widget vocabulary is one 16 KB atlas. `res/pokemmo_ui.png` (471×421) is
sliced by `gfx_ui.xml` into **142 named elements** — `ui-frame`, `ui-button` (31 states),
`ui-checkbox` (21), `ui-inputbox`, `ui-tab`, `ui-popup`, `ui-table-*`. Repaint that one file
and every window in the game changes at once. The remaining scope is four more atlases:

| atlas | size | slices | gives us |
|---|---|---|---|
| `res/pokemmo_ui.png` | 471×421 | 142 named | every frame, button, tab, input, table |
| `res/text-bubble.png` | 162×128 | — | the dialogue box |
| `res/battle-hud.png` | 900×521 | 43 named / 64 areas | HP bar, EXP bar, level box |
| `res/main-hud.png` | 560×560 | 109 named / 129 areas | overworld HUD |
| `res/monster-info.png` | 537×563 | 65 named / 59 areas | summary screen |
| `res/bg.png` | 484×143 | — | login background |

**No `xywh` is edited.** Every replacement PNG keeps its exact pixel dimensions and slice
layout, which is the difference between a one-file swap and re-atlasing 300 rectangles.

## The include strategy — absolute, not vendored

The skill's advice is to vendor `data/themes/default/` into the mod and rewrite the
`../default/` includes. That is 47 MB and it freezes against one client version.

`vanbobby-android-layout-fix` already proved a better route: include the stock files by
**absolute client path**.

```xml
<include filename="/data/themes/default/gfx_ui.xml"/>   <!-- stock, picked up on update -->
<include filename="../firered/gfx_ui-firered.xml"/>     <!-- ours, later include wins -->
```

Later includes win and there is no cascade, so a re-declared `<images file="res/pokemmo_ui.png">`
block with identical slice names replaces the stock one wholesale.

**But "later wins" is only true for widget themes, not for images.** Proven in P0: the
same override did nothing when included last and worked immediately when moved above
`init.xml`. TWL binds an `<image>` reference at the moment the widget theme naming it is
parsed, so an atlas redeclared after `main-widgets.xml` arrives too late. The rule for art
is **declare before first use**, and it is enforced by
`test_art_overrides_are_included_before_anything_consumes_them`. The mod carries only the
art it repaints — target **under 800 KB**, against PARAGON's 20 MB.

## Archive layout

```
mods/vanbobby-firered-theme/
  info.xml                       two <theme> entries, unique names
  icon.png
  firered/                       shared — both themes include from here
    gfx_ui-firered.xml           re-declares pokemmo_ui.png slices
    gfx-firered.xml              text-bubble, battle-hud, main-hud, monster-info, bg
    fonts-firered.xml            pixel fontDefs; MUST be included before <fontGen/>
    colors-firered.xml           constantDef overrides
    res/
      pokemmo_ui.png  text-bubble.png  battle-hud.png
      main-hud.png    monster-info.png  bg.png
      fonts/<pixel>.ttf
  theme/theme.xml                desktop      -> is_mobile="false", name "FireRed"
  theme-mobile/theme.xml         handheld     -> is_mobile="true",  name "FireRed Mobile"
```

`<images file="…">` paths resolve relative to the XML that holds them, so both themes read
the same `firered/res/` copy. One set of art, two themes.

## Palette and visual grammar

Full measured spec: **`docs/SPEC-firered-style.md`**. The short version, and it corrects the
first draft of this plan:

**FireRed has no single window style.** It has one four-band construction with a swappable
accent — `outer #283030 x2 | ACCENT x1-3 | light bevel x1-2 | flat fill` — and the accent is
what changes per screen. The battle message box is navy fill with a gold chamfered frame; the
command menu right next to it is white fill with a square lavender frame; the HP box is pale
yellow with an olive outline and a drop shadow. Same grammar, three accents.

Two corner modes exist and both are needed: **chamfered** (45 degree stair over 4 px, reads as
"dialogue") and **square** (reads as "menu").

Backgrounds are **never flat** — always 1 px horizontal stripes, at a rhythm that varies by
screen (1:1 teal on the bag, 1:3 on the trainer card, 9:1:1 salmon on the summary).

Field labels are **rounded grey pills** (`#788090` capsule, white text), not text on a panel.

And every glyph in the game carries a **1 px hard outline**.

That grammar is why the repaint is procedural rather than 142 pieces of hand art: one
`frame()` function plus a ~20-entry role table covers the whole atlas.

## Phases

_Revised after the reference teardown. See `docs/SPEC-firered-style.md` for the measured
grammar; the ordering below follows identity-per-byte, cheapest and most recognisable first._

### P0 — Spike (ship nothing) — **DONE** (727c76b)
Three unknowns, all now answered on the macOS client. `Loaded theme "FireRed" in 326`:

1. **Does one mod carry two `<theme>` entries?** **Yes.** `FireRed` and `FireRed Mobile`
   ship from one archive; the client selects by name.
2. **Does `../firered/` resolve inside the archive?** **Yes**, for `<include>` and for the
   `<images file>` attribute alike. One copy of the art serves both themes.
3. **Does the desktop client accept absolute `/data/themes/default/...` includes?** **Yes.**
   Nothing is vendored. The spike archive is 12 KB.

Plus the unplanned finding above: art overrides must precede `init.xml`. That cost two
iterations and produced no error message either time.

### P1 — Outlined text  *(moved up from P4)*
FireRed's most recognisable trait is not a window, it is that **every glyph carries a 1 px
hard outline**. Measured on the bag description bar: `#F8F8F8` glyph, `#606060` outline.

`fonts-firered.xml` sets `border_width="1"` with a navy `border_color` on `main`. Because
`pb-dark` (155 refs), `listbox-display` and the whole `main-*` family are `ref="main"`, one
fontDef reaches almost the entire UI. **No art, a handful of lines, largest single change in
the project.** It is also the easiest thing to revert, which is why it goes first.

The pixel face is a separate, later decision inside this phase — outline first, prove it,
then swap the face.

### P2 — The frame primitive, scanlines and the core skin
_Was two phases. Merged, because scanlines had nothing to draw on: panel fills
come out of `pokemmo_ui.png`, and that atlas is not repainted until this phase.
Cheap to build is not the same as possible to validate._

Not 142 hand-mapped slices. One function:

```
frame(rect, accent, corner)  ->  outer #283030 x2 | accent x1-3 | bevel x1-2 | fill
```

with two corner modes, **chamfered** (dialogue, 45 degree stair over 4 px) and
**square** (menus), and fills that are **scanlined** rather than flat, at the per-screen
rhythm in the spec. Then a role table of roughly 20 entries maps the 142 slice names in
`gfx_ui.xml` onto an accent: `ui-frame` -> gold, `ui-popup` -> lavender, `ui-inputbox` ->
white/grey, `ui-button` -> gold, `ui-table-row` -> pale yellow.

`tools/build-firered-theme.py` parses the stock `gfx_ui.xml` for every `<area xywh>`,
applies the role table, asserts the output dimensions match, and emits a coverage report
naming every slice it painted and every one it passed through.

This is the first milestone visible without being told where to look: every window,
button, tab, input and table changes at once. It also completes P1, because the text
shadow can finally be retuned from black to FireRed's own `#606060` against light panels.

### P3 — Login splash plate
The FireRed title screen, adapted to the one surface the login screen exposes.

**Only `bg.png` is themeable there.** `logingui > logo` binds `background-image`, and that
is the whole extent of it. There is no widget for the full-screen backdrop; the
checkerboard and the 3D model come from the client and from `vanbobby_pokemmo3d.mod`.

`bg.png` is declared `xywh="*"`, a whole image with no slice geometry, so unlike every
other atlas it may be **resized**. The plate can be considerably larger than the stock
484x143.

Composition measured off `PokemonFireRedRef/splash.jpg` (720x480, a 3x scale of the GBA
240x160), read as horizontal bands down the left edge:

| band | height @3x | colour |
|---|---|---|
| top rule | 25 px | `#F04800` orange |
| black | 61 px | `#000000` |
| teal field | 143 px | `#30A890` |
| flame row | ~20 px | `#F0C030` gold, `#F0F0A8` cream |
| black | 112 px | `#000000` |
| bottom rule | 27 px | `#780000` dark red |

**Lettering is original, in FireRed's style, not a trace of Nintendo's wordmark, and the
Charizard is not reused.** That is partly a takedown-risk call for a forum release, but
mostly it is the right product answer: the client is PokeMMO, so the plate should read
PokeMMO in FireRed's blocky gold-on-blue outlined lettering rather than borrow another
game's title.

### P3b — The animated login backdrop
_Requested: replace the 3D checkerboard-and-Reshiram scene with something GBA
Pokemon. Investigated before planning, because the honest answer constrains it._

**A theme cannot reach it.** Four things were checked:

| checked | result |
|---|---|
| `logingui` widget theme | exposes `logo` -> `background-image` and nothing else. No backdrop widget exists. |
| `themes/default/textures/bg_00..02.png` | ~900x900 painted sky and cloud plates. These are the overworld and battle sky, not the login scene. |
| client settings | the only background toggle in `strings_en.xml` is **Show Battle Background**. No login or 3D scene option. |
| `vanbobby_pokemmo3d.mod` | listed in `enabled_mods` but **not installed** in `data/mods/`, and the 3D scene still renders. It is client-native. |

So the scene is drawn by the client from its own region models, and no theme file
feeds it. Three routes remain, and they are genuinely different in cost:

1. **Cover it with the plate.** `bg.png` is `xywh="*"` and the `logo` widget sizes
   itself to the image, so a much larger plate, say 1280x720, would occupy most of
   the screen and read as a GBA title screen with the login window on top. Cheapest
   by a wide margin and the only one that changes what you actually see at login.
   Unknowns worth one iteration: whether the widget centres or anchors, whether it
   scales with the window, and whether it pushes the login window off-centre.
2. **Restyle the sky plates.** `textures/bg_00..02.png` are theme-owned and
   replaceable, so they can become flat GBA-style skies. Real work with real
   payoff, but it lands on the **overworld and battle**, not the login screen.
   Worth doing; does not answer this request.
3. **Go after the scene itself.** The models live in `cache/region-models-*.bin`
   and `data/data.pak`. Whether a mod can substitute either is unknown and would
   need its own spike. Highest risk, and quite possibly not moddable at all.

Recommended: 1 now, 2 later as its own phase, 3 only if 1 disappoints.

### P4 — Dialogue box and pill labels
`text-bubble.png` gets the navy-fill/gold-chamfer treatment. Pill labels (`#788090` capsule,
white text) are added as a reusable slice for field headers.

### P5 — Battle HUD and summary
`battle-hud.png` (43 named / 64 areas) — HP capsule `#506858` outline, `#484058` track,
`#58D080` fill, gold `HP` label. Then `monster-info.png` (65 named / 59 areas).

### P6 — Overworld HUD  *(droppable)*
`main-hud.png` is 109 named slices across 129 areas, the largest and riskiest surface, and
the least FireRed-recognisable — the GBA has no persistent overworld HUD to copy, so it is
pure extrapolation. **Recommend deferring to 1.1** and shipping 1.0 without it. Kept in the
plan so the call is explicit rather than quiet.

### P7 — Font face
Swap the pixel face on top of the outline from P1. Candidates, all OFL from Google Fonts:
**Silkscreen** (8 px design, condensed, best at `size="12"`), **Pixelify Sans**
(proportional with a real bold and true lowercase descenders, closest to FireRed's
letterforms), **Press Start 2P** (monospace and wide, probably too wide for dense tables).

**The CJK gate.** `main` is `NotoSansCJK-Medium.ttc` with `faces="sc,tc,jp"` and
`default="true"`. A pixel TTF has no CJK glyphs and `fontDef` exposes no fallback-chain
attribute, so a naive swap may give Chinese and Japanese players tofu. Launch with a CJK
string on screen and look. If it breaks, restrict the pixel face to headers —
`title-font`, `mechabold`, `main-border` — and leave `main` on Noto. The P1 outline survives
either way.

### P8 — Mobile wiring, constants, packaging
Mobile `theme.xml` layers the same overrides after the stock `android/ui/android-*.xml`
includes. Carry over the `settings-scrollpane` `minWidth 1080 / maxWidth 800` fix from
`vanbobby-android-layout-fix` — otherwise FireRed inherits the Settings-screen freeze.

**Expose the accent as a theme `<constant>`.** The grammar is already parameterised by one
accent colour, so a `COLOR` constant in `info.xml` gives the player FireRed / LeafGreen
(`#F15C01` / `#9FDC00`) and anything between for free. This was going to be deferred to 1.1;
after the teardown it is nearly free, so it ships in 1.0.

Build to `dist/vanbobby-firered-theme-1-0.mod`, strip `.DS_Store`.

## Verification

Added to `tools/verify.sh`, no client needed:

- every emitted PNG matches the stock file's pixel dimensions exactly
- every slice name in our `<images>` blocks exists in the stock block we are replacing
  (a typo'd name is a silent no-op, the worst failure mode in TWL)
- no `<include>` escapes the archive except the known-absolute `/data/themes/…` set
- `pmtheme.py check` clean, minus the findings inherited from stock
- `fonts-firered.xml` is included before `<fontGen/>`

On the desktop client:

```bash
# unzipped folder in data/mods/ loads — edit in place, restart, read the log
C=~/Library/Application\ Support/com.pokeemu.macos/pokemmo-client-live
# client.mods.enabled_mods, client.ui.theme=FireRed, client.ui.theme.mobile=false
"$C/PokeMMO.sh"
grep -iE 'theme|applied|skipping|revision' "$C/log/mods.log"
```

`client.mods.debugs.verbose.enabled=true` is already on, so the log names every file taken
from the archive — that is the proof the atlas actually replaced the stock one.

**Login is manual.** Automated input never touches the LOGIN button or gameplay. What I can
verify unattended: the login screen, the Settings → Interface → Theme picker, and the log.
Party, bag, battle and summary screens need you at the keyboard; I will screenshot once you
are in.

## Open questions

- **iOS.** Assumed to use the same `is_mobile="true"` slot as Android — the client exposes one
  mobile theme flag, not two. Unverified; no iOS device here. Flagging, not blocking.
- **Theme constants.** PARAGON exposes user-editable colours via `<constants>` in `info.xml`.
  Worth adding for FireRed vs LeafGreen (green palette, same art) — deferred to 1.1.
