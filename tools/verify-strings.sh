#!/bin/sh
# Proves the toolkit and every mod source are still sound.
# No client or device required.
#
# The dump folder is NOT in this repository: `strings-work/dumps/` is the game's
# own text, ~166,000 entries, and the whole point of generating the strings mod
# instead of hand-writing one is that nobody redistributes it. Produce your own
# with Settings > Utilities and drop them there. Without them the corpus,
# cross-region and parity suites skip and the rest of this script still runs,
# which is the honest result -- not a pass.
set -e
cd "$(dirname "$0")/.."

PMMOD=modkit/bin/pmmod

echo "== unit + corpus tests =="
PYTHONPATH=modkit/src python3 -m unittest discover -s modkit/tests -t modkit -q

echo
echo "== mod sources =="
for d in mods/*/; do
    [ -f "$d/info.xml" ] || continue
    "$PMMOD" validate "$d" | grep -v '^$' | tail -1
done

if [ -d strings-work/dumps ]; then
    echo
    echo "== field-move tables agree across archives =="
    python3 tools/fieldmove_parity.py | tail -1

    echo
    echo "== regions agree with each other =="
    python3 tools/region_parity.py | tail -1
else
    echo
    echo "== no strings-work/dumps: field-move and cross-region checks SKIPPED =="
fi

echo
echo "== theme lint (contradictory min/max bounds) =="
"$PMMOD" theme lint mods/vanbobby-android-layout-fix/theme

if [ -d strings-work/dumps ]; then
    echo
    echo "== fasttext generator dry run =="
    "$PMMOD" strings fasttext /tmp/pmmod-verify-out \
        --dumps strings-work/dumps --rules strings-work/rules.json --dry-run
fi

echo
echo "== every mod builds =="
for d in mods/*/; do
    [ -f "$d/info.xml" ] || continue
    "$PMMOD" build "$d" -o /tmp/pmmod-verify-dist | tail -1
done

echo
echo "OK"
