#!/usr/bin/env python3
"""Report field-move lines silenced in one NDS archive and not in its twin.

See `pmmod.fieldmoves` for what this compares and why the SupersSpeedStrings
parity suite cannot catch it. Exits non-zero when a gap is present.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "modkit/src"))
sys.path.insert(0, str(ROOT / "modkit"))

from pmmod import fasttext, fieldmoves          # noqa: E402
from tests.test_corpus import load_ds_dumps     # noqa: E402

rules, guards = fasttext.load_rules(ROOT / "strings-work/rules.json")
_, silenced, _ = fasttext.scan(ROOT / "strings-work/dumps", rules, guards)
ds_text = load_ds_dumps()
print(fieldmoves.report(ds_text, silenced))
raise SystemExit(1 if fieldmoves.gaps(ds_text, silenced) else 0)
