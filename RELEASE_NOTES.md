# Release notes

## 0.2.5

Extract this over your existing install as usual. Your saves live in
`Documents\My Games\Yu-Gi-Oh Forbidden Memories Recompiled` from 0.2.3 onward,
so nothing this update writes can reach them.

### Two new cheats — `CHEATS`

**`SHOW OPPONENT HAND`.** See what the computer is holding. This is not an
overlay drawn on top of the game: the duel already knows how to draw the
opponent's hand exactly the way it draws yours, and a single flag is all that
keeps it face down. Turning the row on clears that flag, so you get their real
card art, names and ATK/DEF, in the game's own renderer, un-greyed.

**`FORCE FACE UP`.** The computer sets cards face down constantly and you are
meant to guess. With this on, anything it sets plays face up instead — and
cards already sitting face down on its field turn over too, the next time the
view redraws.

Worth knowing before you switch it on: this one changes the duel, not just the
picture. A monster revealed this way genuinely *is* face up, so it will not
flip when you attack it. It stays in defense position if that is how it was
set. Switching the row back off stops new cards being revealed; it does not
re-hide anything already turned over.

Both are preferences, not save writes, so they persist across launches and
cannot damage your save.

### Fusion assistant: equips are worth what they add

An equip scored zero. The hint ranked each line by the printed stats of the
*result* card, and in an equip chain the result is still the base monster — so
a two-card line and a three-card line scored identically, and the tie-break
preferred the shorter one. With two Blue-Eyes plus Dragon Treasure and
Megamorph in hand, the assistant offered Blue-Eyes and one equip and threw away
the play that actually wins the turn.

It now carries the running bonus through the chain, so `NUMBERS + INFO` reports
what the summon will really put on the field. That hand now reads 4500/4000,
which is what the game produces when you play it.

### `VIDEO → WINDOWED SCALE` is a slider

It was a cycling option: eight presses to get from 3x to 7x, reading the label
after each one. It is now a track with a notch per step — drag it, click
anywhere on it, or type a value.

### Disc timing: a stability fix

Fast and instant loading were compressing the completion of Stop, MotorOn and
Seek as well as the sector cadence. A completion delivered inside the frame
that issued it can be missed by the game's disc queue, which then never pumps
again. Those three commands now always complete at hardware pace. Load times
are unaffected — that win comes from sector cadence, which is untouched, and
measures the same before and after.

Related: the README no longer advises keeping `FAST LOADING` off. That advice
went up while the rare duel soft-lock had fast loading as an open suspect; a
full start-to-finish playthrough on instant loading at 3x speed has since run
without a freeze.

## 0.2.4

> **About 0.2.3:** it was published and withdrawn within about five minutes and
> was not stable — its launch-time update check silently disabled itself. If
> you happened to grab it, replace it with this build. Everything below applies
> to 0.2.4, and 0.2.3 is best treated as never having shipped.

**Read this if you are updating from 0.2.2 or earlier — it affects your saves.**

### Install this update over your existing folder

Extract this release **on top of your current install**, replacing the files
when Windows asks. That is the whole procedure, and it is what lets the game
find your existing saves.

On the first launch after that, the game copies your memory cards and save
states out of the game folder and into

```
Documents\My Games\Yu-Gi-Oh Forbidden Memories Recompiled
```

You do not have to move anything yourself. The originals are **copied, not
moved** — they stay in the old folder untouched, so nothing is lost if
something goes wrong or you want to go back.

### If you extracted somewhere else instead

Your saves are not gone. They are still sitting in your old game folder,
where every previous version kept them. Copy these from the **old** folder
into `Documents\My Games\Yu-Gi-Oh Forbidden Memories Recompiled`:

- `card1.mcd`, `card2.mcd` — memory cards
- the `saves\` folder (its `openbios\` subfolder holds your save states)

Then launch the game again.

### After this, updates stop being fragile

From 0.2.3 onward your saves live outside the game folder for good. Later
updates can be extracted anywhere — over the top, into a fresh folder, it no
longer matters, because nothing an update writes can reach them.

Before this change, saves survived an update only because the release archive
happened not to contain a `saves\` folder, and extracting into a new folder
silently left every save behind. That is what this release fixes.

Running the game off a USB stick or a shared machine? Put an empty file named
`portable.txt` next to the exe (or set `PSX_PORTABLE=1`) and everything stays
in the game folder as before.

---

### Also in this release

**Update notifications.** The game now checks for a newer release each time it
starts and offers to open the download page. It never downloads or installs
anything by itself. Set `update_check=0` in `menu_settings.ini` to turn the
check off entirely — with that set, no request is made at all.

**VIDEO > WINDOWED SCALE.** A new option under SCREEN, 1x to 8x, default 3x.
It resizes the window so the picture is an exact whole-number multiple of the
original 320x240 — at 3x that is a 960x720 picture with no blurring and no
uneven pixels. It applies when SCREEN is WINDOWED and SCALING is INTEGER; the
row says so when it is not.

**The menu bar no longer covers the game.** The picture was being drawn behind
the menu bar instead of below it, so the top of the screen was hidden and the
image sat off-centre. Maximising changed how much was covered but never fixed
it.
