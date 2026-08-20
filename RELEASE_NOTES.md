# Release notes

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
