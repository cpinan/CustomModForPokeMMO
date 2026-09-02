# BACKLOG — FireRed theme

Known defects, deferred by agreement. Not blockers.

## 1. Text on the bare game world is barely readable

**Where:** the overworld HUD top left (route, money, clock), and the Pokemon name
and level labels in battle.

**Why it is hard.** These widgets have no panel behind them; the text sits
straight on the map or the battle scene. They draw with `pb-dark` and
`mechabold`, which are the SAME faces the cream panels use, so a single colour
cannot serve both: a dark glyph vanishes on the dark world, a light one vanishes
on cream.

**What was tried.** A light 1px outline on those six faces, so a dark glyph would
read on both grounds. It is better than nothing and it is what stock's
`main-border` does, but at size 12 over a busy, mid-tone map it is still weak,
and it does not survive a dark scene at night.

**The real fix** is the widget layer, not the font layer: point those specific
widgets at a dedicated light-on-dark face, and give the battle name label an
actual plate. FireRed puts the name and level INSIDE the cream HP plate; PokeMMO
splits them into a separate background-less widget, which is the whole problem.

## 2. Padding and clipping

**Where:** the Pokedex title is clipped at the top. Suspected elsewhere.

**Why.** `border` and `defaultGap` are widget parameters in the layout XML, not
atlas art. Nothing in the generated atlases can move them.

## 3. Chat is dark and translucent

By design in the stock client, and its text is dark now. Needs a decision rather
than a fix: lighten the chat frame, which breaks the see-through-to-world
behaviour people rely on, or keep chat fonts light, which splits the font rule.

## 4. The battle menu's POSITION is not known to be reachable

FireRed puts FIGHT / BAG / POKeMON / RUN bottom **right**, beside the message
box. PokeMMO's client puts them bottom left and the theme has no documented
handle for it: PARAGON and both Emerald themes restyle the battle screen and
neither moves a widget. 0.51 probed it and got half an answer immediately: with `300,10,10,10` on
`battlegui`, `battle-panel` and `battle-fight`, the menu **disappeared entirely**
and the navy band rendered empty.

**Settled: TWL's `<border>` is `(top, left, bottom, right)`.** Slot one is TOP,
so 300 pushed the menu's content down and out of a band about 160 tall. The rest
of this file already assumed that order - `36,5,5,5` on the dex title, `22,8,8,8`
on the summary - and now it is proven rather than inherited.

**Answered on 2026-09-02: the position IS themeable, and the handle is LEFT
padding on `battle-panel`.** `10,300,10,10` walked the whole command block from
the left edge to about the middle of the band, message column and all. 0.53 uses
860, which is that 300 plus the 560 the menu was still short of the right edge,
and takes top and bottom down to 4 because the second row was clipping off the
bottom of the screen. The band's height belongs to the client, so the room has
to come out of padding.

0.53 then overshot at 860 and clipped its second row, which is what prompted
`tools/layout_check.py`: the geometry is arithmetic over the theme's own borders
and the real TTF metrics, so a wrong number is now caught before a build instead
of after a restart, a login and an encounter. 0.54 ships its answer, `0,831,0,10`.

One more finding from the same shot: pointing the other eleven buttons at
`battle-fight` with `ref=` reached **none** of them - only FIGHT took the white
box. A ref inside the *same file* did not carry the params either, so all twelve
are now written out in full. That is the "name the leaves" rule one level deeper
than 0.48 found it.

## 5. Smaller things

- Settings checkmarks are faint; the glyph recolour maps them too light.
- Username and Password fields use different slice families and do not match.
- `enabled_mods` in the local client references `vanbobby_pokemmo3d.mod`, which
  is not installed. Harmless, and not ours.

---

**All three of 1, 2 and the battle-name half of 1 land on the same missing
piece: a widget-theme override layer.** That is the argument for doing it next
rather than more art.
