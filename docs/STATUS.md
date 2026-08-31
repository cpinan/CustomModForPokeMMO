# STATUS — FireRed theme for PokeMMO

_Last updated: 2026-08-30 · branch `main` · clean · shipped `dist/vanbobby-firered-theme-0-23.mod` (1.3 MB)_

## Next action

Spike one nested widget override — put a `border` on `trainercard`'s `dialoglayout`
(`main-widgets.xml:1144`) via `firered/widgets-firered.xml` — to settle whether re-declaring a
NESTED `<theme>` merges into the stock one or replaces it wholesale. That answer decides whether
the bag/card/dex work is small overrides or vendored files, and everything else waits on it.

## State

- **All 13 atlases and all 65 fonts are generated, not drawn.** Four scripts under `tools/`
  rebuild every asset from the stock client plus the references. A client update is a re-run.
- **The login screen is done**: the client's 3D backdrop is covered, a painted scene fills the
  window, the POKEMMO/FIRERED plate and Charizard sit on top. 25 tests, all green.
- **The widget layer exists but has exactly one entry in it** —
  `firered/widgets-firered.xml`, which sets `logingui`'s background. The mechanism is proven;
  nothing else uses it yet.
- **Screen layouts are still generic.** Bag, trainer card and dex get their look from
  prefix-matched roles in `build_firered_atlas.py`, not from their own kits. That is the gap
  between "FireRed palette" and "looks like the game".
- **Mobile has never been launched.** `theme-mobile/` is wired and generated but unverified.
- Deliberately not built: the pixel font (P7, licensing undecided), chat readability (needs a
  decision, see below), `<constants>` for FireRed/LeafGreen colour swap.

## In flight

Nothing half-written in the repo. The next three pieces of work, in the priority the user set:

- **Bag** — `data/themes/default/ui/inventory.xml`. Kit:
  `PokemonFireRedRef/001/...Interface & Bag Screens.png`. Wants the tan pocket tabs with the
  orange underline, the pale-yellow list panel with dashed row separators, and the solid
  `#0078C0` description bar with a white rounded item square.
- **Trainer card** — `<theme name="trainercard">` at `main-widgets.xml:1144`, whose
  `dialoglayout` draws `trainer-card.background` with `border 25`. Kit:
  `...Trainer Card Kit.png`. Wants the blue header band, the gold outlined title, the
  scanlined light-blue body and the badge row of rounded slots.
- **Pokédex** — `data/themes/default/ui/monster-dex.xml`. Kit: `...Pokedex.png`. Also fixes the
  clipped title in `docs/BACKLOG-firered.md`. Note the stock ANDROID theme comments this file
  out, so the mobile dex is a separate problem.

## Verify

```bash
tools/verify.sh
```

Regenerates every asset from source, runs the 25 invariant tests, then `git diff`s the mod tree.
A non-empty diff means a generator no longer reproduces what is committed. No client, no device,
no login.

## Open questions

- **Layer or vendor?** PARAGON does NOT layer: it vendors whole `default/ui/*.xml` files and
  edits them in place — 374 changed lines in `inventory.xml`, 853 in `monster-dex.xml`, 502 in
  `customization.xml` — and its `theme.xml` includes 20 of its own copies. We layer, via absolute
  includes plus a late override file. Layering survives client updates; vendoring gives full
  control over deeply nested widgets. The spike in "Next action" decides which is actually
  needed. Vendoring only the three files in flight is the likely middle.
- **Chat.** Dark and translucent by design, and its text is dark now. Lighten the frame, which
  breaks see-through-to-world, or keep chat fonts light, which splits the font rule. Asked
  2026-08-30, undecided.
- **Pixel font.** The real GBA font is in `001/...HP Bars & In-battle Menu.png`, full character
  set. Highest fidelity and the most legally exposed thing here, being Nintendo's typeface.
  Recommendation stands: an OFL face. Undecided.
- **Charizard is a still.** The 20-frame animated path works and is one flag away
  (`build_firered_splash.py --frames 20`), but costs ~1.6 MB.

## Do not redo

- **A theme CANNOT restructure the widget tree.** It changes appearance and geometry —
  background, font, border, gaps, min/max size, alignment. It cannot reparent or reorder. FireRed
  puts the Pokémon's name inside the HP plate; PokeMMO makes it a sibling with no background. We
  can give that sibling a plate; we cannot move it inside.
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
