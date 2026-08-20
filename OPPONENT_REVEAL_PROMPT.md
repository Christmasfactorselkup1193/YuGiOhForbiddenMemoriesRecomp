# Next session — reveal the opponent's hand, natively

Paste this into a fresh session. **Read `psxrecomp/CLAUDE.md` first** — rule 3
(no printf; every observable is a TCP debug command) and rule 4 (never edit
`generated/`) are absolute.

This is a separate thread from the duel soft-lock (`NEXT_SESSION_PROMPT.md` +
`ISSUES.md` ISSUE #1). Nothing here depends on that.

---

## THE GOAL

A **toggle cheat that shows the opponent's hand**, drawn the way the player's
hand is drawn. The user's words: *"instead of them being grayed out, they will
show the card sprites like the player hand does."* They explicitly chose the
**native** route over an overlay — it must look like the game drew it.

They also note some duelists may have "secret hands" past the initial five.
Unproven either way; see below.

---

## ESTABLISHED — do not re-derive any of this

### The opponent's hand is already readable

The duel keeps **15 card records per side**, stride 28, from `0x801A7AE4`:

| records | owner |
|---|---|
| 0–4 | player hand |
| 5–14 | player field |
| **15–19** | **opponent hand** |
| 20–29 | opponent field |

Record layout: `+0` id, `+2` atk, `+4` def, `+6` equip-bonus accumulator,
`+10` flags. Flags `0x8000` = LIVE, `0x0400` = FIELD, **`0x2000` = OPPONENT**.

Cross-validated on two independent specimens (a duel savestate and a live
Simon duel). Reading their hand is a solved problem — the whole difficulty is
*display*.

**Secret hands:** in the Simon duel records 15–19 held exactly five cards and
record 20 onward was field, so he held five. The array only reserves five hand
slots per side, so if some duelists hold more they must do it by another
mechanism. Do not assume either way; catch one in the act.

### How a hand card is actually drawn

A card is **two** GP0 `0x64` rects. Read straight out of the player's packets:

```
card 0: 393800A0  00200028   <- ART: clut 0x3938, uv=(160,0), 40x32
card 1: 38F80078  00200028   <- clut 0x38F8, uv=(120,0)
card 2: 38B80050  00200028   <- clut 0x38B8, uv=( 80,0)
card 3: 38780028  00200028   <- clut 0x3878, uv=( 40,0)
card 4: 38380000  00200028   <- clut 0x3838, uv=(  0,0)
        ...
        3C508000  003C0034   <- BACKING: 52x60, uv=(0,128), identical on all five
```

So: **40x32 artwork rect** (per-card CLUT, `u = slot*40`) **+ 52x60 backing**.
The artwork is indexed by **hand slot, not card id** — the game stages the five
hand images into a VRAM strip, each with its own CLUT.

The opponent's packets contain **only the backing**, at `v=192`. There is no
art rect because no art was staged for them.

Both hands are drawn at the same screen positions: y=146, x = 14/74/134/194/254,
same CLUT `0x3C50`, same texpage `0x029E`. The only difference in the backing
is `v`: **128 = face, 192 = back**.

### It is ONE routine, not two

Player faces and opponent backs are both written by
**`pc=0x80084B10`, `ra=0x80042208`** — mode **1** of a 6-entry jump table at
`0x80010520`, dispatched on `(a3>>16)`:

```
[0] 0x800427AC  [1] 0x800421F8  [2] 0x80042210
[3] 0x80042228  [4] 0x80042240  [5] 0x80042378
```

Mode 1's block at `0x800421F8` calls the sprite builder with
`a0 = s2`, `a1 = word[sp+96]`, `a2 = s8 & 0xFFFF`. So face vs back is a
**parameter to a shared path**, which is the good news.

Packet pools: player hand `0x000A5AD0` (stride 0x108), opponent
`0x000C7A50` (stride 0x18).

### Proven NOT to work — do not retry

**Flipping the backing `v` from 192 to 128 does not reveal a card.** Tested
live by patching the texcoord word in a loop while the backs were on screen:
the card turned into a generic **swirl**, because the backing texture is all
there is — nothing is layered on it. A reveal must ADD the art rect, not
redirect the backing.

Also dead ends, with reasons:
- `func_800170C8` is the **field** stat-display pass (600 calls, all records
  5–8), not the hand renderer.
- `gpu_frame_dump`'s `func` attribution is always `0x000029CC` — the kernel DMA
  routine (interpreted install-at-runtime code, CLAUDE.md rule 18). Useless for
  finding game code. Use the entry's `src` (packet address) and write-trace it.
- Per-card **texpage** is not the selector; all cards use `0x029E`.

---

## THE NEXT TASK

**Find the routine that stages a card's image + CLUT into VRAM for a hand
slot.** Everything else is cheap once that exists.

Then, in order:

1. Call it for records 15–19 into a **second** VRAM strip (do not clobber the
   player's — theirs is live at `u = slot*40` with CLUTs `0x3838 + slot*0x40`).
2. Emit the 40x32 art rect per opponent card, pointing at the new strip.
3. Flip their backing `v` 192 -> 128.
4. Put it behind a toggle. Check how the existing cheats/mods are gated
   (`src/psx_ygo_debug.c` registers the fusion commands; the fusion overlay has
   a tune/enable command) and follow that pattern.

Hints for step 0: no `0xA0` (CPU→VRAM) op appears in the frame dumps, so the
upload is likely a **DMA** rather than a GP0 command — look at DMA channel 2
(GPU) activity when the hand changes, not per frame. A hand only re-stages when
it changes, so trace across a draw/play rather than a steady frame.

---

## THE HARNESS (already built — use it)

The opponent plays on its own and the window is far too fast to catch by hand.
`pause`/`step` were removed from the debug server by design.

**Specimen:** the user saved a state at their turn end. Internal **slot 0**
(the F7 UI numbers slots +1, so it is "save state 1" in the menu).

```bash
python tools/opp_watch.py --replay 0
```

Loads the slot, presses Start correctly, waits for the turn to flip, saves a
savestate of the moment, then burst-captures screenshots plus the opponent's
records for the whole turn into `captures/opponent-turn-<stamp>/`.
`captures/` is gitignored.

Sequence timings from this session: turn flips ~1.4 s after Start; the
opponent's turn runs ~11–12 s; the player's hand view returns after that.
To reach the **player's hand** for comparison: load slot 0, Start, wait for
`turn` to go back to 0, settle ~1.5 s.

Useful reads: `fusion_hand` (records + ids), `gpu_frame_dump frame=N`
(`gpu_ring_stats` gives `newest_frame`), `wtrace_arm/reset/dump`.

---

## TOOLING GOTCHAS — these cost real time this session

- **`press` takes the RAW pad word and the PSX pad is ACTIVE LOW.** Idle is
  `0xFFFF`; a PRESSED button is a **zero** bit. `buttons` is NOT a "press
  these" mask — `0x0008` means *every button except Start* and mashes the whole
  d-pad. **Start = `0xFFF7`**, Cross `0xBFFF`, Up `0xFFEF`. Build words by
  clearing bits out of `0xFFFF` (see the `PAD_*` table in `tools/opp_watch.py`).
  Any earlier "input changed nothing" conclusion drawn with the mask form is
  worthless.
- **Savestates and `menu_settings.ini` live in the PLAYER-DATA directory**
  (`Documents\My Games\<title>\`), not beside the exe. `saves/openbios/` and
  `build*/menu_settings.ini` are stale pre-migration copies that nothing reads
  and that read plausibly enough to fool you — this invalidated a
  cross-validation pass and silently changed the user's fast-loading setting.
  **Ask the runtime:** `savestate op=path slot=N` returns the directory and the
  exact file.
- **`savestate op=save` acks BEFORE it writes** (staged onto the emu thread).
  `ok:true` says nothing about the file. Record the mtime and require it to
  move, or you will copy a stale slot and report a fresh capture.
- **Runtime setter commands can persist to the player's real config.**
  `fast_loads level=N` writes `menu_settings.ini`. Treat setters as config
  changes, not probes, and restore anything you flip.
- **`pause` / `step` / `continue` are removed** by design — query a ring buffer
  over the window of interest instead.
- **Bash working directory silently resets to `C:\dev` mid-session.** Use
  absolute paths.
- **Killing the game to relink ends the user's duel.** Ask before rebuilding if
  they are playing.

---

## BUILD / ENVIRONMENT

```
cmake --build build-dbg -j     # debug + TCP debug server on 4370
cmake --build build -j         # release (no debug server)
```

- `C:\msys64\mingw64\bin` FIRST on PATH, and `export USERPROFILE` from Bash or
  ccache aborts.
- **Kill the exe before building** ("Permission denied" at link = the code was
  fine).
- Play the **debug** build (`PlayDebug.bat`) for any of this — the release
  build has no debug server.
- The tree is mixed CRLF/LF; `psx_video_menu.c` is bare-LF with an embedded
  NUL. Patch scripts must detect line endings **per file** and be written to a
  FILE, never a heredoc.
- The fusion assistant lives in `src/psx_fusion_*.c` (main repo);
  `psxrecomp/` is a submodule on branch `ygofm`, pinned from the main repo.
