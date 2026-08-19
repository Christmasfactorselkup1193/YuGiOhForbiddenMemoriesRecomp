# Yu-Gi-Oh! Forbidden Memories — Recompiled

A static recompilation of **Yu-Gi-Oh! Forbidden Memories** (USA, SLUS-01411):
the game's MIPS code is translated to C ahead of time and compiled into a
native executable, rather than interpreted by an emulator.

Built on [PSXRecomp](https://github.com/mstan/psxrecomp).

**You bring your own disc.** Nothing here contains the game.

| | |
|---|---|
| Serial | SLUS-01411 (USA / NTSC-U) |
| Players | 2 |
| Publisher | Konami, 1999 |
| BIOS | OpenBIOS, bundled — a retail dump is optional |

---

## First launch

Run the executable. It asks once for your disc image, then remembers it:

1. A dialog explains what is needed, then opens a file picker.
2. Pick your dump — `.cue` (preferred, with its `.bin` beside it), or `.bin`,
   `.img`, `.iso`, `.car`, `.chd`.
3. The dump is checked against the CRC32 of the data track this build was
   compiled from. A mismatch is **refused**, with a message naming the release
   that is needed and the one you supplied.
4. The answer is stored beside the executable (`disc.cfg`, `disc_verified.cfg`)
   and later launches start straight into the game.

The content hash is computed once, when you choose the disc, and not on every
boot. If the file changes, moves, or is replaced, the check runs again.

If your dump moves later, either let the next launch ask you again, or point at
it yourself from **FILE → CHANGE GAME DISC** in the in-game menu (`F10`). That
stores the new location and takes effect on the next launch.

### Which dump

This build is compiled from the USA release, serial **SLUS-01411**. A PAL,
Japanese, or Greatest Hits disc is a different program — this build does not
contain its code and cannot run it. The expected data-track CRC32 is recorded
in `game.toml` as `disc_crc`.

### Command line

Scripted and headless runs have no picker and must be told:

```bash
Yu_Gi_Oh_Forbidden_Memories_Recompiled.exe --disc "/path/to/game.cue"
```

Also available: `--bios <path>`, `--memcard-dir <path>`, `--no-launcher`.

---

## Building from source

The framework is expected at `psxrecomp/`. This checkout links it by junction
to a local clone rather than tracking it as a submodule, so `psxrecomp/` is
gitignored — see **Framework** below before building.

```bash
python3 psxrecomp/psxrecomp_cli.py generate \
  --config game.toml --project-root . --disc /path/to/your.cue
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target psx-runtime
```

`generated/` is produced from **your** disc. It is gitignored and must not be
published — see NOTICE.

For a debug build with the TCP inspection server on `127.0.0.1:4370`, add
`-DPSX_DEBUG_TOOLS=ON`. `PSX_RECOMP_UI` is off in this project: there is no
launcher, and the runtime asks for the BIOS and disc itself.

### Packaging a release

```bash
cmake -S psxrecomp/recompiler -B build-recompiler -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-recompiler --target psxrecomp-game psxrecomp-bios
scripts/package_setup_release.sh build <artifact-tag>
```

Writes `dist/ygofm-<version>-<tag>.zip`. Needs `objdump` on `PATH` so bundled
MinGW DLLs can be resolved.

---

## Framework

`psxrecomp/` is a junction to a local checkout, **not** a submodule, and it is
gitignored. Cloning this repository therefore does not bring the framework with
it, and the build will not work until you provide one.

This project also depends on framework changes that are not upstream, including
the disc-identity gate described above. Point `psxrecomp/` at a checkout that
contains them.

---

## Symbols

`symbols.toml` → `python3 tools/sync_symbols.py` → `psx_symbols.h`
(`PSX_FN_*`). See `psxrecomp/docs/SYMBOLS.md`.

---

## Licence and legal

PolyForm Noncommercial License 1.0.0 — see [LICENSE](LICENSE). Noncommercial
use only, and the licence cannot be sublicensed or swapped for a permissive
one, because the framework it builds on is offered on the same terms
(Copyright (c) 2026 Matthew Stan).

That licence covers this project and the framework. It grants nothing in
respect of the game itself, which is Konami's. Use only a disc image and BIOS
you obtained legally.

Read [NOTICE](NOTICE) before redistributing anything — particularly before
sharing a *compiled build*, which is not the same as sharing this repository.
