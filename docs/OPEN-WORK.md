# Open work

Everything known to be wrong or unfinished, as of 2026-08-30, written for someone
picking this up cold. Ordered by what will bite you first.

Read `docs/FINDING-string-call-sites.html` before touching any strings rule. It
explains which replacement token works where, which is the single thing that has
cost the most time on this project and is not derivable from the dumps.

---

## Ground rules, learned the expensive way

**A table is not a call site.** `15/42` (EXP, end of battle) accepts a blank line.
`15/1` (encounter, start of battle) does not — blanking it means a wild battle
never loads and the session has to be restarted. Same table, same archive, same
token, opposite outcome. This shipped as 1.9 and had to be pulled the same day.

**`{09}` and `\n\n` are not interchangeable.** `{09}` is an unresolved argument
placeholder; where the engine never fills it, the box sits there and drags. `\n\n`
is a well-formed empty message the engine passes through. Four release cycles
went into learning this.

**An empty override is not a silencing token.** The client reads `<string/>` as
*no override* and shows its own text.

**The reference mod is evidence; the dumps are not.** Where
`MODEXAMPLES/SupersSpeedStrings-*.mod` has an opinion about an address, thousands
of people are running it. Where it is silent about a whole table, that silence is
data too — it was silent about every address 1.9 broke.

**Never automate PokeMMO login or gameplay.** The account can be banned for it.
Driving Mod Management over adb is fine; everything past the LOGIN button is not.

---

## Bugs

### 1. `data/strings/` fix is written but never seen working
**Status:** code fixed 2026-08-30, **awaiting one hardware check.**

`vanbobby-demo-strings` and `vanbobby-region-label-unpad` shipped their strings under
`data/`, which the client treats as a directory overlay and reports as deprecated on every
startup — a visible dialog, not just a log line. Both now ship under `strings/` with
`info.xml` pointing there, matching what the generated mod has done since 1.7, and both went
1.0 -> 1.1 so a fixed artifact is distinguishable from an old one. All seven mods validate
with zero warnings.

**Desktop check passed 2026-08-30.** Both 1.1 mods installed and enabled on the macOS
client: `mods.log` shows both applied, `console.log` shows both string containers populate
from `strings/…` (Classpath) rather than a `data/` directory overlay, and no dialog appears.
One caveat: the macOS client shows no dialog even with the old
`pmmod-demo-strings-1-0.mod` enabled — its info.xml declares the `data/strings/…` path, so
either the declaration counts as "requesting it" or the dialog is Android-only. Desktop
therefore cannot reproduce the failure, and the fix still needs the Retroid to be **seen**
closing it.

Found while checking: the 1.0 -> 1.1 bump had rewritten both info.xml declarations to
`<?xml version="1.1"?>`. Fixed in source and dist, and `pmmod validate` now warns on any
non-1.0 XML declaration (XMLDECL).

**To close this:** install `dist/vanbobby-demo-strings-1-1.mod` and
`dist/vanbobby-region-label-unpad-1-1.mod` on the Retroid, restart, and confirm the dialog
saying *"tries to overlay the data/strings/ directory while not requesting it in the
info.xml"* no longer appears. If it still does, these two are not the cause and something
else ships under `data/` — `log/mods.log` names the mod it objects to.

Both were disabled on the device when last seen. Importing re-enables a mod, so check the
toggles afterwards.

### 2. The installed Android Layout Fix is not the one in this repo
The Retroid runs `android-layout-fix-v3-3-0.mod`, display name
*"Android Layout Fix v3"*, version 3.0. This repo has version **1.0**. The v3
source is not here and its provenance is unknown.

**Fix:** find v3 (check `POKEMMOMODS/`, or pull it back off the device), reconcile
with `mods/vanbobby-android-layout-fix/`, and either bump this to 3.0 or explain
the split. Until then the repo does not describe what is actually running.

### 3. Hordes still print their encounter message
Reported in Johto on 1.10. Hordes are a PokeMMO invention, not in the original
ROM, so the string is not at the Unova `15/2` coordinate the vanilla horde line
uses. It has not been located.

**Fix:** search `dump_strings_en.xml` (the plain-id container) for horde wording;
PokeMMO's own additions live there rather than in the NDS archives. Then treat it
like any battle-adjacent address — see ground rules — and get hardware evidence
before shipping.

---

## Unfinished

### 4. Table 14 is unexplored, and it is the biggest remaining win
1,159 entries: every stat change, status tick, "It's super effective!", faint.
`{09}` is known to stall there. Whether `\n\n` passes through is **unknown** —
SupersStrings does not touch the table, so there is nothing to copy.

`probe-faint-ds` in `strings-work/rules.json` was built for exactly this: one
address, `14/1` (`The wild {00} fainted!`), blanked. It is currently **disabled**,
because it sits in the same state machine that hung on `15/1` and leaving it armed
was not worth another lost session.

**Before spending a cycle on it, settle two things:**
1. Are table 14 messages tap-gated at all, or do they auto-advance mid-battle? The
   symptom was always the *end* of a fight, which suggests the per-turn run
   already flows and there is nothing to win.
2. Is it even wanted? "It's super effective!" is information in a real battle and
   noise in a grind.

If you do try it: enable only `probe-faint-ds`, nothing else, and win one wild
battle. `test_the_table_14_probe_is_a_single_address` enforces that it stays one
address.

### 5. Does `modkit/` ship?
It is not in this repo. Without it nobody can regenerate the mod or run the 99
tests, so the published `rules.json` is inert — a reader can see the rules but not
apply them. Deferred on 2026-08-30, still undecided.

### 6. Workspace and repo hold duplicate trees
The working directory has `mods/` and `dist/` that duplicate
`CustomModForPokeMMO/mods/` and `.../dist/`, kept in sync by hand. Every release
so far has needed a manual copy step, which is exactly the kind of thing that
silently drifts — bug 2 above may already be an instance of it.

**Fix:** one canonical location, then update `tools/verify.sh` and the
`--dumps`/`--rules` defaults in `modkit/src/pmmod/cli.py:660`.

### 7. Johto parity is close but not complete
`counters-ds-johto` covers 57 addresses. SupersStrings covers 104 in that archive;
the other 47 are Gym Leader and Elite Four dialogue, deliberately out of scope
here. Two more are deliberate keeps (`211/16`, `211/23` — errors explaining why a
move did nothing). Nothing to do unless the scope changes; recorded so the gap is
not mistaken for an oversight.

### 8. Bug report to PokeMMO not filed
Two findings worth reporting, both with evidence in this repo:
- The stock android theme ships `settings-scrollpane minWidth 1080 / maxWidth 800`,
  which loops the settings screen on handhelds. See `docs/FINDING-layout-loop.md`.
- The string dump utility aborts on a NUL byte in Sinnoh's data
  (`SAXException: An invalid XML character (Unicode: 0x0)`), so no user can dump
  Johto at all without physically removing the Platinum ROM. The client's error
  dialog says *"ensure you have write permissions in the client folder"*, which is
  wrong and sends people down the wrong path entirely.

---

## Regenerating the dumps

`strings-work/dumps/` came from the **desktop** client at
`~/Library/Application Support/com.pokeemu.macos/pokemmo-client-live/`, not from
Android — adb cannot read the Android client's private storage.

Johto needs a workaround, because the dump walks regions in order and dies on
Sinnoh before reaching it:

1. Quit the client. It holds the ROMs open and rewrites `config/main.properties`
   on exit.
2. Move `roms/3.nds` (Platinum) **out of the `roms/` folder**. Editing
   `client.roms.nds3` does nothing and renaming the file does nothing — the client
   scans that folder and identifies ROMs by content. Both were tried.
3. Launch, then Settings > Utilities > Dump Storyline Strings. No login needed.
4. It still throws on Johto, having written ~4.7 MB. Repair the file: drop the one
   incomplete trailing element, append `</ds_strings_archive>`. That recovers
   41,522 entries with nothing lost.
5. Move the ROM back and verify the checksum.

Sinnoh writes a **truncated** `dump_CPU_0_en.xml` before it throws. Do not let it
overwrite the good repaired copy already in `strings-work/dumps/`.

---

## Verify

```bash
tools/verify.sh
```

99 tests, every mod source validated, the theme linted, the generator dry-run, and
all seven mods built. No client or device needed.

Two tests are the ones that matter most, both in `modkit/tests/test_corpus.py`:

- `test_only_proven_addresses_are_silenced_in_a_battle_engine` — general, not a
  list of known-bad addresses. Anything inside a battle engine fails unless it is
  in `DS_PROVEN_IN_ENGINE` *with a note saying what proved it*. This would have
  caught 1.9 before it shipped.
- `test_the_gba_pattern_rules_cannot_reach_the_nds_archives` — `move-learned`,
  `catch-flow` and `evolution` were written against the GBA ids and were drifting
  into Sinnoh table 368 and Johto table 197, those archives' battle engines.

If you change a rule and only the shipped-files test fails, you forgot to
regenerate:

```bash
modkit/bin/pmmod strings fasttext mods/vanbobby-fast-strings \
  --dumps strings-work/dumps --rules strings-work/rules.json \
  --name "VanBobby Fast Strings" --mod-version <next> --author carlospinan --langs en,es
```
