# STATUS — CustomModForPokeMMO

_Last updated: 2026-09-02 · branch `main`, pushed · 0 uncommitted files_

## Next action

**Open a battle in the desktop client and send one screenshot of the command menu** — it
answers the FireRed 0.51 layout probe and unblocks 0.52.

## State

- **`vanbobby-fast-strings` is 1.16**, confirmed on the Retroid on 2026-09-02: every HM acts
  with no box, Sweet Scent / Fly / Teleport are silent, a Repel reports itself again. 709
  entries, 35 rules, five archives.
- **FireRed theme is 0.51**, installed and enabled on the **desktop** client (`client.ui.theme=FireRed`,
  0.50 disabled). The battle command menu is now a white box with black text on the navy band.
  Bag, trainer card, dex and summary already read like FireRed's.
- **Client-written text is its own address space, and `{STRING_nnnnnn}` is how you find it.**
  No dumped ROM line carries that slot, so any entry that does is one PokeMMO wrote — the
  field-move box `16780155`, the Secret Power obstacles, the horde lines. Grep for it before
  reaching for another archive rule.
- **The regions are each other's oracle.** The same text ships five times over, so a line
  silenced in one region and drawing in another is a bug no comparison against another mod can
  find. `tools/region_parity.py` reports them; `test_region_parity.py` fails the build on one.
- **The battle engine is fenced in every region**, and only addresses in `DS_PROVEN_IN_ENGINE`
  may be silenced inside one. That list is the gate the probes below exist to open.
- **113 tests**, stdlib only, no client and no device. They skip cleanly without the dumps.
  `strings-work/dumps/` and `MODEXAMPLES/` live outside the repo and are symlinked in.
- **What changed when is in `CHANGELOG.md`**, grouped by date and named by mod.

## In flight

- `mods/vanbobby-firered-theme/firered/widgets-firered.xml:337` — **layout probe, remove in
  0.52 whatever the answer.** `battlegui` and `battle-panel` carry `300,10,10,10`; `battle-fight`
  carries `120,10,30,60` while its siblings keep an even `8,8,8,8`. One battle screenshot says
  which handle moves the menu and which slot of `<border>` is which side. Record the answer in
  `docs/BACKLOG-firered.md` item 4.
- `/storage/EAFF-F713/Download/vanbobby-fast-strings-1-17-probe2.mod` on the Retroid's SD card —
  **staged, not installed.** 1.16 plus eight blanked end-of-battle addresses (Unova-0 `15/44-50`,
  `15/65`) and the two horde ids (`5021`, `5023`). Import it, delete the 1.16 entry, save,
  restart; then win a battle, catch something, and check a wild encounter still **loads**. If it
  holds, move both rules into `strings-work/rules.json` and add the eight addresses to
  `DS_PROVEN_IN_ENGINE` in `modkit/tests/test_corpus.py` citing hardware. If it hangs, reinstall
  `vanbobby-fast-strings-1-16.mod` from the same folder and record the no in `docs/OPEN-WORK.md`.

## Verify

```bash
tools/verify-strings.sh   # every mod source + 113 tests (needs no client)
tools/verify.sh           # the FireRed theme's generators and invariants
```

## Open questions

- **Is table 14 worth probing at all?** 1,159 entries — every faint, status tick and
  "It's super effective!". `probe-faint-ds` in `rules.json` is the one-address experiment
  (`14/1`) and stays disabled. Settle two things first, both answerable while playing: are those
  messages tap-gated or do they auto-advance, and is silencing them even wanted mid-battle.
  It is the riskier probe — table 14 is the in-battle state machine that hung on 2026-08-30.
- **Move Relearner, Unova 204** (`docs/OPEN-WORK.md` item 7) — fenced, not decided. One build
  and one relearned move closes it.
- **Elite Four and Gym Leader dialogue** (item 8) — 162 NDS entries the reference silences and
  this mod does not. Kept out of scope on 2026-09-01; worth revisiting, since PokeMMO's Elite
  Four is a daily run.
- **1.13's 133 newer entries have still never been seen in game** — the Unova-1 Day Care lines
  (`426/17`, `426/26`) and the move tutors are the ones worth walking past.

## Do not redo

- **Do not push mods to `/sdcard/Download` for the Retroid.** The client's Import picker browses
  the **SD card**, `/storage/EAFF-F713/Download`. Internal storage is invisible to it, and a file
  pushed there looks like a stale index but is not one.
- **Do not try to remove a battle box with `{09}`, an empty override, or a control code.** All
  three were settled on hardware 2026-08-30: `{09}` leaves an empty box that still costs a tap,
  an empty override is read as no override and the vanilla text returns, and the corpus has no
  skip code. Only a blank line has ever worked, and only at proven addresses.
- **Do not blank Unova-0 table 15's battle-START entries** (`15/1-31`). It hangs a wild encounter
  and costs the session. `battle-flow-ds` is disabled for that reason.
- **Do not override a base theme and expect its refs to follow.** A `ref=` binds when the
  referring file is parsed, so `rbattle` / `mobile-battle` / `logingui` overrides reach nothing.
  Name the leaves. This cost 0.25 and 0.48.
- **Do not chase the field-move or HM boxes through the NDS archives again.** Coverage there
  matches the reference address for address; what was left was client-written plain ids.
- **Do not try white text on navy for the battle menu.** 0.48 and 0.49 both died on the font set:
  the only light faces left are 48 / 32 / 18pt and the description line needs about 14. Black on
  white, shipped in 0.51, is the pairing that fits.
- **Do not put `--` inside an XML comment.** It is not well formed, and the theme loads half
  built with nothing useful in the log.
