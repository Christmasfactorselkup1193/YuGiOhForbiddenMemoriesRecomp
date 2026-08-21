# Release notes

## 0.2.6

Extract this over your existing install as usual. Your saves live in
`Documents\My Games\Yu-Gi-Oh Forbidden Memories Recompiled` from 0.2.3 onward,
so nothing this update writes can reach them.

### New: `MODS → DROP MISSING CARDS`

**82 of the game's 722 cards are dropped by nobody.** Both of Exodia's legs are
among them, which is why the card list cannot be completed by duelling in the
stock game. Turn this on and every one of them has a source.

Nothing on your disc is touched. A duel loads the current opponent's drop
weights into memory, and this rewrites that copy — so the change lasts exactly
as long as the duel does.

The placement is yours to change. On first run it writes
**`drop_missing_cards.ini`** next to your saves, listing every card by name
under the duelist that drops it:

```ini
[Weevil Underwood]
52  =  30,  20,   0   ; Hercules Beetle
278 =  30,  20,   0   ; Petit Moth
```

The three numbers are the S/A POW, B/C/D and S/A TEC rates, as weights out of
2048 — 20 is about 1%. Each band always totals 2048, so whatever you add comes
off that duelist's normal drops in proportion. The shipped table adds about 1–6%
per duelist, which you will not notice. Delete the file to get the defaults
back.

### Fixed: `CHEATS → ALL CARDS` before the title screen

**Turning `ALL CARDS` on during the Konami logos or the intro movie distorted
the picture and then froze the game.** It never reached the title. This is in
0.2.5 too.

The row writes card counts to three places in memory, and one of those is only
the card chest's working buffer while the chest is the screen you are on. Before
a save is loaded it belongs to the intro instead, so the row was writing over
the movie as it played.

The three rows that write save data — `ALL CARDS`, `STARCHIPS` and
`FREE SPENDING` — now check that a save is actually loaded first, and say
"load a save first" instead of doing anything if it is not. `ALL CARDS` also
leaves the chest's buffer alone unless it really is the chest's buffer, which
means the same mistake cannot corrupt a duel or a shop screen either.

### No more startup toast for cheats you never touched

Stored cheat settings are re-applied as the game starts, and the two reveal rows
announced themselves while that happened — every launch opened with
"Their cards: face up", even when the setting was OFF and nothing had changed.
The message is still there when you move the row yourself.

## 0.2.5

Extract this over your existing install as usual. Your saves live in
`Documents\My Games\Yu-Gi-Oh Forbidden Memories Recompiled` from 0.2.3 onward,
so nothing this update writes can reach them.

### Updates now actually rebuild

**If your install folder has brackets in its name — `ygofm-0.2.5-win-x64(1)`,
which is what your browser makes the second time you download the same zip —
every update so far has silently done nothing.** You would extract the new
version, launch it, watch it generate, and still be playing the old build. No
error, anywhere.

The updater hands off to a rebuild step that has to run after the game exits.
That handoff lost the folder path at the first bracket, so the rebuild never
started. Fixed. A `&` in the folder name broke it the same way.

If you are on a broken install right now, this release repairs it — extract it
over the top and launch it once. It will rebuild, and that first launch takes a
few minutes.

### Two new cheats — `CHEATS`

**`SHOW OPPONENT HAND`.** See what the CPU is holding.

**`FORCE FACE UP`.** The computer sets cards face down constantly and you are
meant to guess. With this on, anything it sets plays face up instead — and
cards already sitting face down on its field turn over too, the next time the
view redraws.

### Fusion Assistant

Equips are worth what they add. Equips such as 'Megamorph' weren't being
properly considered, fixed.

### `VIDEO → WINDOWED SCALE` is a slider

It was a cycling option: eight presses to get from 3x to 7x, reading the label
after each one. It is now a track with a notch per step — drag it, click
anywhere on it, or type a value.

### Disc timing: a stability fix

Duels would occasionally freeze while fast loading was set to INSTANT, fixed.

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
