# Yu-Gi-Oh! Forbidden Memories — Recompiled

A static recompilation of **Yu-Gi-Oh! Forbidden Memories** (USA, SLUS-01411).
The game's MIPS code is translated to C ahead of time and compiled into a native
executable — it is not interpreted by an emulator.

On top of that sits a set of quality-of-life features built specifically for
this game: a live duel-rank meter, a fusion assistant that reads your actual
hand, a card-drop multiplier with a proper results screen, and a small cheat
menu. All of it drawn in the game's own art, all of it toggleable at runtime.

Built on [PSXRecomp](https://github.com/mstan/psxrecomp).

> **You bring your own disc.** Nothing in this repository, and nothing in the
> download, contains any part of the game. The C is generated on your machine,
> from your copy, the first time you run it.

| | |
|---|---|
| Serial | SLUS-01411 (USA / NTSC-U) |
| Players | 2 |
| Publisher | Konami, 1999 |
| BIOS | OpenBIOS, bundled — a retail dump is optional |

---

## What this adds

Everything below lives in the in-game overlay menu on **`F10`**, and every
setting takes effect immediately — no restart, no patched save.

### ⚔️ Duel rank meter — `VIEW → DUEL RANK`

The game grades every duel you win, but it only tells you afterwards. This puts
the grade on screen **while you play**, so you can see a careless move cost you
an S before the duel is over.

| Mode | What you get |
|---|---|
| `OFF` | stock behaviour |
| `IN GAME` | the game's own POW/TEC badge and rank letter, beside the FIELD box |
| `IN GAME + SCORE` | the same, plus the raw 0–99 score |
| `OVERLAY TEXT` | plain text in the corner — never covered by a card view |

The sprites are the game's, lifted from its own VRAM, so the meter sits in the
HUD looking like it was always there. It tracks the picture through scaling and
aspect changes, and hides itself the moment a card view covers the box it
labels.

### 🧩 Fusion assistant — `VIEW → FUSION HINT`

Forbidden Memories has thousands of fusions and teaches you none of them. This
reads the cards actually in your hand, checks them against the game's own fusion
tables, and tells you what they make.

| Mode | What you get |
|---|---|
| `OFF` | stock behaviour |
| `NUMBERS` | pick order marked on the cards themselves |
| `NUMBERS + INFO` | pick order plus the name of the card it produces |

`VIEW → SUGGEST FUSION BY` chooses whether it optimises for **ATTACK** or
**DEFENSE**.

It reads the game's real fusion and equip tables out of memory rather than a
copied list, so its answers are the game's answers — including the awkward
three-step rule the game actually implements.

### 🎴 Card drops — `MODS → CARD DROPS`

Stock, a won duel awards exactly one card. This makes it **1–99**, so grinding a
specific drop stops being a weekend.

It comes with a results screen that stock never had: the cards you won, listed
across three pages you flip with **D-pad Left/Right**, with a yellow **New!**
tag — the game's own label — on anything you didn't already own.

### 💰 Cheats — `CHEATS`

| Row | Range | Notes |
|---|---|---|
| `LIFE POINTS` | 1–9999 | 8000 is stock. Applies to both duellists |
| `STARCHIPS` | 0–99999 | written straight to your save |
| `FREE SPENDING` | on / off | purchases succeed, the deduction is undone |
| `ALL CARDS` | 1, 2 or 3 of each | fills the trunk. Apply with the chest closed |

`LIFE POINTS` is a preference and is restored on every launch. The other three
are live writes to save data and are deliberately *not* re-applied at startup,
so a cheat you tried once cannot quietly clobber a later save.

### From the runtime

Also in the `F10` menu, courtesy of PSXRecomp: save states, rewind (`F8`), an
emulation-speed multiplier, and **`GAME → FAST LOADING`** — which cuts the
disc loads to near-instant. That one ships **off**, so the game loads at
original speed until you turn it on; the setting then persists.

---

## First run

The download is a **setup host** — a small executable plus the recompiler and
the framework source. It has no game code in it until you supply a disc.

1. Run `Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe`.
2. It asks for your disc image and checks it against the CRC32 of the data track
   this build expects. A mismatch is **refused**, naming the release it needs
   and the one you gave it.
3. It downloads a compiler if you have none, translates the game to C from your
   copy, and compiles it.
4. It builds into `build-release/` and starts the game.

You need **Python 3** installed. Everything else the setup fetches or brings
with it.

> ### ⏳ The first run takes a few minutes — let it finish
>
> A compiler download, a whole game translated to C, and a real compile all
> happen before you see anything. A console window will sit there working; that
> is it doing its job, not hanging. **Every run after the first starts
> immediately.**
>
> **That wait is the entire point.** This download contains no game code and no
> game assets — not the executable, not the sprites, not even the font. All of
> it is produced on your machine, from the disc you already own, and never
> leaves it. Shipping a ready-made build would mean shipping Konami's work;
> doing it this way means nobody does.

### Which dump

`.cue` is preferred, with its `.bin` beside it; `.bin`, `.img`, `.iso`, `.car`
and `.chd` also work.

This build is compiled from the USA release, serial **SLUS-01411**. A PAL,
Japanese, or Greatest Hits disc is a different program — this build does not
contain its code and cannot run it. The expected data-track CRC32 is recorded in
`game.toml` as `disc_crc`.

The hash is computed once, when you choose the disc, not on every boot. If the
file moves or changes, the check runs again. To repoint it yourself, use
`FILE → CHANGE GAME DISC` in the `F10` menu.

### Command line

Scripted and headless runs have no picker and must be told:

```bash
Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe --disc "/path/to/game.cue"
```

Also available: `--bios <path>`, `--memcard-dir <path>`, `--no-launcher`.

---

## Building from source

The framework is a submodule at `psxrecomp/`, so clone recursively:

```bash
git clone --recurse-submodules https://github.com/Unchiga/YuGiOhForbiddenMemoriesRecomp.git
```

(Already cloned without it? `git submodule update --init --recursive`.)

Then generate and build. The `generate` step produces **both** the recompiled
BIOS and the game's C — the framework ships `bios/openbios.bin` but not the
recompiled form of it, so a fresh clone has no BIOS backend until this runs:

```bash
python3 psxrecomp/psxrecomp_cli.py generate \
  --config game.toml --project-root . --disc /path/to/your.cue
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target psx-runtime
```

If you would rather not do any of that by hand, the setup host does exactly
these steps for you — see [First run](#first-run).

Both `generated/` and the game's baked sprite and font sources are produced from
**your** disc. They are gitignored and must not be published — see
[NOTICE](NOTICE).

Because the artwork is baked at build time, CMake needs to know where your disc
is. Running `generate` first (as above) is enough — it prepares a working copy
under `disc/` and CMake finds it there. Failing that it looks, in order, at
`-DYGOFM_DISC=<path>` if you pass one, the disc this build directory already
verified, and the one recorded beside the executable. If it finds none,
configuring stops with a message rather than quietly producing a runtime with
no art:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DYGOFM_DISC=/path/to/your.bin
```

For a debug build with the TCP inspection server on `127.0.0.1:4370`, add
`-DPSX_DEBUG_TOOLS=ON`.

### Packaging a release

```bash
cmake -S psxrecomp/recompiler -B build-recompiler -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-recompiler --target psxrecomp-game psxrecomp-bios
cmake -S . -B build-setup -G Ninja -DCMAKE_BUILD_TYPE=Release -DPSXRECOMP_FORCE_SETUP_HOST=ON
cmake --build build-setup --target psx-runtime
scripts/package_setup_release.sh build-setup <artifact-tag>
```

Writes `dist/ygofm-<version>-<tag>.zip`. Needs `objdump` on `PATH` so bundled
MinGW DLLs can be resolved. The build directory must be a **setup host** build —
`PSXRECOMP_FORCE_SETUP_HOST=ON` — not the game.

---

## Framework

`psxrecomp/` is a submodule pinned to the
[`ygofm`](https://github.com/Unchiga/psxrecomp/tree/ygofm) branch of a fork of
[PSXRecomp](https://github.com/mstan/psxrecomp).

It is a fork rather than upstream because this project depends on framework work
that is not upstream yet: the disc-identity gate, registration APIs so a title
can own its debug commands and its guest-space overlays instead of the framework
naming them, a per-vblank game hook, and a first-run setup host that works
without a launcher. Those are additive and intended for upstream; the branch
exists so this repository builds today rather than waiting on that.

---

## Symbols

`symbols.toml` → `python3 tools/sync_symbols.py` → `psx_symbols.h`
(`PSX_FN_*`). See `psxrecomp/docs/SYMBOLS.md`.

---

## Licence and legal

PolyForm Noncommercial License 1.0.0 — see [LICENSE](LICENSE). Noncommercial use
only, and the licence cannot be sublicensed or swapped for a permissive one,
because the framework it builds on is offered on the same terms
(Copyright © 2026 Matthew Stan).

That licence covers this project and the framework. It grants nothing in respect
of the game itself, which is Konami's. Use only a disc image and BIOS you
obtained legally.

Read [NOTICE](NOTICE) before redistributing anything — particularly before
sharing a *compiled build*, which is not the same as sharing this repository.
