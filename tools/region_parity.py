#!/usr/bin/env python3
"""Report lines this mod silences in one region and leaves drawing in another.

PokeMMO ships the same game text five times over -- Kanto and Hoenn as plain
ids, Sinnoh, Johto and the two Unova archives as NDS coordinates. That
redundancy is an oracle no external mod can give you, and it is the only thing
that catches a miss SupersSpeedStrings also misses.

Run it to a fixpoint: closing a gap gives the next one a silenced twin to
disagree with, so a clean second pass is the finish line, not the first.

See `pmmod.regions` for how each disagreement is classified. Exits non-zero
while any disagreement is still unexplained.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "modkit/src"))

from pmmod import regions            # noqa: E402

DUMPS = ROOT / "strings-work" / "dumps"
RULES = ROOT / "strings-work" / "rules.json"

print(regions.report(DUMPS, RULES))
raise SystemExit(1 if regions.gaps(regions.compare(DUMPS, RULES)) else 0)
