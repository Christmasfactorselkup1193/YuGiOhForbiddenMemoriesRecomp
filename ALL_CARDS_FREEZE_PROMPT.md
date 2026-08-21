# Next session — ALL CARDS before the title screen distorts and freezes

Paste this into a fresh session. **Read `psxrecomp/CLAUDE.md` first** — rule 3
(no printf; every observable is a TCP debug command) and rule 4 (never edit
`generated/`) are absolute.

---

## THE BUG

Enable **`CHEATS → ALL CARDS`** *before the title screen appears* — during the
Konami/title cards or the intro movie — and the game **visually distorts and
then freezes**.

Reported 2026-08-20 by the user. Not yet reproduced under instrumentation.
Doing it after a save is loaded has always been fine, so this is specifically
about applying it too early.

---

## THE LEADING HYPOTHESIS — check this first, it is probably it

`all_cards_changed()` in [src/psx_ygo_cheats.c](src/psx_ygo_cheats.c) writes
**722 bytes to each of three fixed addresses**:

```
0x801D0250   live save struct (+0x50)
0x801D3250   the known mirror (+0x3000)
0x80105D98   third copy - the chest UI's working buffer
```

Its only guard is `psx_mod_game_started()`. **That does not mean what the cheat
needs it to mean.** From `fntrace.c`:

> One-shot game-start detection: fire the first time the game's `entry_pc` is
> dispatched.

So it is true the instant the game EXE begins executing — *before* the title
screen, *before* a save is loaded, and *throughout the intro movie*. The cheat
therefore happily scribbles 2166 bytes into three regions that at that moment
hold something else entirely.

`0x80105D98` is the prime suspect. It is a **UI work buffer**, not save data;
during the intro that memory is very likely the MDEC / streaming buffer for the
FMV. Corrupting it would produce exactly the reported symptom — picture
distortion first, then a hang when the decoder or its queue is fed garbage.

**This is a whole CLASS of bug, not one row.** Every CHEATS row is gated the
same way, so check all of them at the same point in the boot:

| row | what it writes early |
|---|---|
| `ALL CARDS` | 2166 bytes over three buffers |
| `STARCHIPS` | a word to `0x801D07E0` |
| `FREE SPENDING` | per-frame read/write of `0x801D07E0` |
| `LIFE POINTS` | **patches two code words** (`0x800175D0`, `0x8002DC70`) via `psx_mod_write_code_word` |

`LIFE POINTS` is the one to look at second — it is a preference with a settings
key, so it is **re-applied automatically at startup** by
`psx_video_menu_apply_restored()`. If patching those instructions early is
unsafe, it fires on every launch without the player touching anything.

---

## THE FIX IS A BETTER GATE, NOT A DELAY

Do not paper over it with a timer. What these rows actually need is "a save is
loaded and the trunk is real", which `psx_mod_game_started()` cannot answer.

Candidate signals to evaluate:

- the game-state byte at **`0x8009B23A`** (used elsewhere in this project)
- the duel/rank globals near `0x8009B1D5`
- a sanity check on the trunk itself — 722 plausible counts (each 0..250)
  at all three addresses before writing
- a "player is in a menu where this makes sense" gate

A cheap, honest version of the last one: refuse the write unless the three
buffers already look like a trunk. That is self-validating and needs no new
reverse engineering — the same trick `psx_drop_missing.c` uses to identify a
duelist from its resident drop table rather than trusting an index.

---

## HOW TO REPRODUCE AND WATCH IT

`ALL CARDS` has a **NULL settings key**, so it is never restored at startup —
it has to be toggled by hand during the intro. Drive the overlay from the debug
build; host `SendInput` cannot click the SDL window.

```bash
cmake --build build-dbg -j        # debug + TCP debug server on 4370
```

Launch `build-dbg\Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe`, then as soon as
the debug server answers `ping`, open CHEATS and click the row:

```
menu_move/menu_click x=1043 y=31     # the CHEATS title (1920x1506 window px)
menu_move/menu_click x=1400 y=400    # the ALL CARDS row - CONFIRM the y first
```

Verify the toggle landed by reading `menu_settings.ini`, not by assuming the
click worked — blind clicks silently miss, which cost real time this session.
`ALL CARDS` has no settings key, so watch for the "All cards granted" toast or
read the trunk instead.

**When it freezes, the freeze watchdog writes the evidence you need** to
`build-dbg/diagnostics/psx_freeze_dump_psx-runtime_*.json`. `last_store_pc` in
that dump is the single most useful field — it is what identified a BIOS stall
in a different investigation this week. Note the dumps are 40–100 MB; parse
them, do not cat them.

---

## TOOLING GOTCHAS THAT COST TIME THIS WEEK

- **A wedged emulator still answers `ping`.** `ping` is served on the io
  thread; `menu_state`, `frame` and `screenshot_present` need the emu thread.
  If ping works and everything else times out, the emu thread is stuck — that
  is the signature of both this class of freeze and of a modal dialog.
- **A modal dialog looks exactly like a freeze.** The launch-time "Update
  available" box blocks the emu thread. It appears when the local build's
  baked version is older than the published release. CMake reads `VERSION` at
  **configure** time, so after a version bump you must re-run
  `cmake -S . -B build-dbg` or every launch nags and blocks.
- **`card_drops_test` wedges the emulator if hammered** — 9–13 unpaced calls
  kill it, 20 ms between calls survives 120. Documented at the top of its
  handler in `src/psx_ygo_debug.c`; two plausible fixes are already ruled out
  there, so read it before trying a third.
- **Bash cwd silently resets to `C:\dev`.** Use absolute paths.
- **Kill the exe before building** ("Permission denied" at link = the code was
  fine).
- Patch scripts must detect line endings **per file** and be written to a FILE,
  not a heredoc: the tree is mixed CRLF/LF and `psx_video_menu.c` is bare-LF
  with an embedded NUL.

---

## STATE OF THE TREE

Everything below is committed and pushed on `main`; the working tree is clean.

- `MODS → DROP MISSING CARDS` shipped — the 82 never-dropped cards now have
  sources. Placement lives in `drop_missing_cards.ini` in the player-data
  folder; defaults are baked in `src/psx_drop_missing_table.h`, regenerate with
  `tools/gen_drop_table.py`.
- `CHEATS → SHOW OPPONENT HAND` and `CHEATS → FORCE FACE UP` shipped.
- Released **0.2.5**. This bug is NOT in it — 0.2.5 predates the drop mod, but
  `ALL CARDS` is old and the bug almost certainly ships in 0.2.5 too. Worth
  confirming, since that decides whether 0.2.6 is a fix release.
