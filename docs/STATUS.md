# STATUS — FireRed theme for PokeMMO

_Last updated: 2026-08-31 · branch `main` · clean · shipped `dist/vanbobby-firered-theme-0-24.mod` (1.3 MB)_

## Next action

**Session goal set by the user 2026-08-31: make the bag read like FireRed's bag, layouts
included.** Start by having the user log in on the desktop client (0.24 is installed and
enabled) and open the bag; screenshot it, then iterate — art in the bag roles/painter in
`tools/build_firered_atlas.py`, layout in PARAGON-style param overrides (border, gaps,
min/max, alignment) as merge-blocks in `firered/widgets-firered.xml`, against the kit
`PokemonFireRedRef/001/...Interface & Bag Screens.png`.

## State

- **All 13 atlases and all 65 fonts are generated, not drawn.** Four scripts under `tools/`
  rebuild every asset from the stock client plus the references. A client update is a re-run.
- **The login screen is done**: the client's 3D backdrop is covered, a painted scene fills the
  window, the POKEMMO/FIRERED plate and Charizard sit on top. 25 tests, all green.
- **The widget layer has two entries** in `firered/widgets-firered.xml`: `logingui`'s
  background and `inventory-button`'s item square (`ui-box.background`). Overrides merge, so
  each block names only what it changes.
- **Bag, trainer card and dex have their own screens as of 0.24** — `bag-list` and
  `dex-frame` roles, a `paint_bag_tab` painter for the open-pocket underline, and a
  `paint_trainer_card` painter for the whole card texture. The builder now takes a per-atlas
  `special={name: painter}` hook for slices that are compositions, not panels. **None of it
  has been seen in game yet.** Not done from the kits: the bag's dashed row separators and
  `#0078C0` description bar (no stock widget maps to either — the row and description
  surfaces are shared or absent), and the dex title clip (BACKLOG 2, needs eyes on it).
- **Mobile has never been launched.** `theme-mobile/` is wired and generated but unverified.
- Deliberately not built: the pixel font (P7, licensing undecided), chat readability (needs a
  decision, see below), `<constants>` for FireRed/LeafGreen colour swap.

## In flight

**Bag parity is the open piece of work.** 0.24 shipped the art first pass; the layout half
has not started. The knobs, all verified to exist:

- `mods/vanbobby-firered-theme/firered/widgets-firered.xml` — add merge-blocks re-declaring
  `inventory-tabbedframe` (and its nested `dialoglayout > tabbedpane > tabbox`) and
  `inventory-tab-empty`. Stock blocks to mirror are in the client's
  `data/themes/default/ui/inventory.xml` (188 lines, read it fresh — tab band `border
  0,0,15,0`, tabs `border 20,0`, pane min 530x378).
- `tools/build_firered_atlas.py` — `bag-list` role, `paint_bag_tab`, and the `bag`/`card`
  palette constants; iterate colours per screenshot.
- The bag's dashed row separators and `#0078C0` description bar need the real bag on screen
  first: no stock theme in `ui/inventory.xml` names a row-separator or description surface,
  so the owning widget has to be identified visually before it can be themed.

Trainer card and dex shipped the same untested first pass; they wait behind the bag. The
stock ANDROID theme comments out `monster-dex.xml`, so the mobile dex is a separate problem.

## Verify

```bash
tools/verify.sh
```

Regenerates every asset from source, runs the 25 invariant tests, then `git diff`s the mod tree.
A non-empty diff means a generator no longer reproduces what is committed. No client, no device,
no login.

## Open questions

- ~~**Layer or vendor?**~~ **Answered 2026-08-30: layer. Nested `<theme>` re-declaration
  MERGES into the stock block — it does not replace it wholesale.** Spiked on the login
  screen, no login needed: re-declared `logingui > login-window` with only
  `minWidth 620` in `widgets-firered.xml`. The window rendered 620 wide and kept its stock
  title bar, background, `minHeight` and the nested `dialoglayout`'s `60,20,20,20` title
  inset — under wholesale replacement all of that styling would have vanished. The shipped
  `logingui` background override making the login dialog keep all its nested styling is the
  same behaviour one level up. So bag/card/dex are small override blocks in
  `widgets-firered.xml`; vendoring stays available for the dex's block-DROP trick only
  (removing a `<theme>` needs a vendored file — an override can set params, not delete
  blocks).
- **Chat.** Dark and translucent by design, and its text is dark now. Lighten the frame, which
  breaks see-through-to-world, or keep chat fonts light, which splits the font rule. Asked
  2026-08-30, undecided.
- **Pixel font.** The real GBA font is in `001/...HP Bars & In-battle Menu.png`, full character
  set. Highest fidelity and the most legally exposed thing here, being Nintendo's typeface.
  Recommendation stands: an OFL face. Undecided.
- **Charizard is a still.** The 20-frame animated path works and is one flag away
  (`build_firered_splash.py --frames 20`), but costs ~1.6 MB.

## Do not redo

- **Layout IS heavily changeable, so do not talk yourself out of it.** An earlier read of this
  called it near-impossible. Measured against PARAGON, that was wrong: its bag redesign adds and
  removes ZERO theme blocks in `ui/inventory.xml` and still changes 374 lines, all of them
  `border`, `background`, `minWidth`, `minHeight`, `maxWidth`, `maxHeight`, `alignment`,
  `textAlignment`, `spacing` and the gap params. Its dex changes 853 lines and adds one generic
  block while dropping 15. That is enough control to resize panels, re-pad them, re-align their
  contents and drop backgrounds entirely.

  The one real limit: a theme cannot ADD, REMOVE or REPARENT a widget in the tree. FireRed puts
  the Pokémon's name inside the HP plate; PokeMMO makes it a sibling with no background. Give the
  sibling a plate and pad it so the pair reads as one unit; it still cannot be moved inside.
  Dropping a `<theme>` block from a VENDORED file is also a technique, as the dex shows: the
  widget survives, it just falls back to default styling.
- **The login backdrop IS reachable** — via `logingui`'s own `background` param, which stock
  leaves unset. This was called impossible three times before PARAGON's `android.xml` disproved
  it. Check the CONTAINER, not just the leaf widgets.
- **The login logo slot is a fixed 484x143 design px** and scales whatever it is given. A
  1728x946 plate renders squashed. Author at 968x286, twice the slot, for a 1:1 retina landing.
- **Art must be included BEFORE `init.xml`/`main-widgets.xml`; widget overrides AFTER.** TWL binds
  an `<image>` when the widget theme naming it is parsed, but widget themes are last-wins. The two
  rules point opposite ways; `test_art_overrides_are_included_before_anything_consumes_them`
  enforces both.
- **The stock atlases overlap themselves in 129 places** and use a NEGATIVE extent to mean mirror.
  Nothing can be repainted in place; the builder repacks every slice.
- **A tint MULTIPLIES the art.** `label2.background` ships `tint="#99949494"`; painting under a
  tint gives mud. Painted slices lose their tint, glyphs keep theirs.
- **A face gets an outline OR a shadow, never both** — two rings on an antialiased glyph reads as
  fringing.
- **`--` is illegal inside an XML comment** and makes the file unparseable. Caught three times
  here; there is now a test.
- **`shot.sh --click` takes RETINA pixels, not design points** — it halves what you give it.
- **BSD `sed` has no `0,/re/` address and BSD `pgrep` has no `-c`.** Both fail silently-ish.
