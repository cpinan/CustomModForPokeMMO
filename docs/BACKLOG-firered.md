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
neither moves a widget. 0.51 ships a probe rather than a guess - `battlegui`,
`battle-panel` and `battle-fight` each get a deliberately lopsided border, with
four different numbers on the button so one screenshot says both which handle
moves what and which side each slot of `<border>` addresses.

Remove the probe in 0.52 whatever the answer, and write the answer here.

## 5. Smaller things

- Settings checkmarks are faint; the glyph recolour maps them too light.
- Username and Password fields use different slice families and do not match.
- `enabled_mods` in the local client references `vanbobby_pokemmo3d.mod`, which
  is not installed. Harmless, and not ours.

---

**All three of 1, 2 and the battle-name half of 1 land on the same missing
piece: a widget-theme override layer.** That is the argument for doing it next
rather than more art.
