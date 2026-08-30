# Shiny Scale Probe

**Type:** test mod, not a feature · **Client:** r32920

## What it is for

Answers one question: **do the battle sprite scale tables work on sprites a mod
has not replaced?**

That matters because "make shinies bigger" is either a few lines of text or a
50 MB asset pull, depending on the answer.

## What it does

Ships only the three scale tables, no sprites at all, with deliberately extreme
values for common early-route species:

| species | id | scale |
|---|---|---|
| Caterpie, Pidgey, Rattata, Zubat | 10, 16, 19, 41 | `1` — should look tiny |
| Weedle, Oddish, Starly, Bidoof, Patrat, Poochyena | 13, 43, 396, 399, 504, 261 | `4` — should look oversized |

Default is `3`, so both directions should be obvious at a glance.

## How to run it

1. Import, enable, restart.
2. Walk into grass until you meet any species in the table.
3. Look at the size.

**If sizes changed** → scaling works on ROM sprites. `only-shiny-sprites` can
enlarge shinies with a text file listing every dex id at scale `4`, and the mod
stays tiny.

**If nothing changed** → scaling only applies to sprites a mod ships, so
enlarging shinies requires shipping a shiny sprite per species.

Either way, delete this mod afterwards — it exists to be thrown away.
