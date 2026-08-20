# Reveal the opponent's hand — SOLVED (2026-08-20)

Shipped as **`CHEATS → SHOW OPPONENT HAND`**. Implementation and the full
address reasoning live in the comment block in
[src/psx_ygo_cheats.c](src/psx_ygo_cheats.c) (`--- SHOW OPPONENT HAND ---`).

This file used to be a hunt brief. Keeping the brief would send the next
session after a problem that does not exist, so it now records the answer
instead.

---

## The answer

The game already draws the opponent's hand exactly the way it draws yours.
**One signed byte decides face-up or face-down**, and nothing else was needed —
no VRAM staging, no emitted primitives, no overlay.

    0x800E9FF0   player   duellist struct, 0x20 bytes
    0x800EA010   opponent duellist struct, 0x20 bytes
    +0x1F        SIGNED "keep this hand face down" flag
                 => the opponent's copy is 0x800EA02F

Negative hides, zero (or any non-negative) shows. Duel init seeds both structs
from one global at `0x8001767C`–`0x80017690`, then overwrites the opponent's
copy with `-1` for a CPU opponent:

    0x800176A8  li  $v0, -1
    0x800176AC  sb  $v0, -0x5FD1($v1)      ; $v1 = 0x800F0000  =>  0x800EA02F

This is the flag the well-known `300EA02F 0000` GameShark code clears — the
user supplied that code, and it is what cracked this open.

### Where it is read — three sites, all display

| PC | Function | Effect when the flag is negative |
|---|---|---|
| `0x80017DF0` / `0x80017E20` | `func_80017DB4` | writes **255** — the card-back graphic index — to display byte `+103` instead of the card's real artwork index |
| `0x80018058` | `func_80018004` | same, single-card path |
| `0x800232C0` | `func_80023144` | leaves the card on its dimmed tint (tint byte `0x8009B34E`) |

The third one is the "grayed out" in the original request: clearing the flag
un-greys them as well as turning the backs into real cards.

`0x80017DF8` is `beq $v0,$zero` and `0x80017E28` is `bgez $v0` — hence *signed*,
and hence 0 is the value to write.

### Why it must be per frame

A block copy at `0x8007431C` rewrites `+0x1A..+0x1F` as a unit. Measured over a
full traced opponent turn (`wtrace` on `0x800E9FF0..0x800EA030`): exactly one
such write per turn. A one-shot write would be undone, so the guard runs in the
existing per-frame `psx_ygo_cheats_tick()` and only ever replaces a **negative**
value — a duel the game itself chose to show face-up is never touched.

---

## Corrections to the old brief

- **The opponent's card art is already available to the renderer.** The old
  brief assumed no art was staged for them and planned to build a second VRAM
  strip. Not so: with the flag cleared, their cards draw with correct, distinct
  artwork immediately. The opponent's struct even carries the same per-slot
  bytes the player's does (`+0x1A..+0x1E`: opponent `28 2a 2c 2f ff` against
  player `12 13 14 15 16`).
- **The `v=192 -> 128` swirl was a dead end for the right reason** — but the
  reason is not "the art was never staged", it is that the backing texture is
  the whole sprite and the reveal is a decision taken *upstream*, in the display
  builder, not in the packet.
- **"Secret hands"**: the duel reserves five hand records per side (15–19) and
  five per-slot bytes in the duellist struct, so the structures hold at most
  five. With the row on, whatever a duellist is actually holding is on screen —
  that is now the cheapest way to settle it, by watching.

---

## Harness

`python tools/opp_watch.py --replay 0` still works and is still the way to
catch an opponent turn: slot 0 is a state saved at the player's turn end, Start
hands the turn over ~1.4 s later, and the opponent's turn runs ~11–12 s.

The tooling gotchas from the old brief all still apply — active-low `press`,
savestates in the player-data dir, `savestate op=save` acking before it writes,
`pause`/`step` removed by design. `rtrace` is **MMIO only**; it cannot trace a
RAM read, so a reader hunt goes through the generated C, not the runtime.

---

# Force face-up — SOLVED (2026-08-20)

Shipped as **`CHEATS → FORCE FACE UP`**, same file. A second GameShark pair the
user supplied:

    5000051C 0000      ; repeat the next line 5 times, address += 0x1C
    301A7C93 0080      ; write byte 0x80 to 0x801A7C93

`0x1C` is 28 — the card-record stride — so this is `0x80` into offset **+11** of
records **15–19** (the opponent's hand). +10 is the flags halfword, so +11 is
its high byte.

## The record array, settled

Base `0x801A7AE4`, stride 28:

| records | owner |
|---|---|
| 0–4 | player hand |
| 5–14 | player field |
| 15–19 | opponent hand |
| 20–29 | opponent field |

Confirmed live rather than assumed: the opponent's drawn card appeared in record
19 and was then copied into record 20 as it was played. **flags == 0 means an
empty slot** — the id left in the record is stale, which is what makes a swept
field look occupied.

## Flags vocabulary (halfword at +10)

| bit | meaning | evidence |
|---|---|---|
| `0x8000` | in hand | cleared as the card lands on the field |
| `0x4000` | draw dimmed | display+12 colour word `0x00404040` vs `0x00808080` (`0x80017EE0`) |
| `0x2000` | artwork index forced to 0 | `0x80017E5C`; set by `0x80018030` |
| `0x1000` | **face down** | `0x80017EA0`, `0x800180C0`, `0x8001EA20`, and the battle flip at `0x8001E700` |
| `0x0800` | defense position | display+34 = 192 (`0x80017EBC`) |
| `0x0400` | on the field | appears as a card is placed |

`0x1000` is **not** display-only. `func_8001D670` reads it at `0x8001E700` —
that is the routine that flips a set monster when it is attacked. A card
revealed by clearing it is genuinely face-up and will not flip on attack.

## What the cheat does

It is **prophylactic, not a reveal**. `func_8001BD8C` ORs `0x1000` in as the AI
puts a card down (`0x8001C3A8`, `0x8001CCE4`), inheriting it from the hand
record. Pre-clearing the hand record means the card is placed face-up.

Measured on a specimen where the AI was forced to set a monster (Key Mace,
id 192, savestate slot 2):

| | field record 20 |
|---|---|
| stock | `0x9800` — face-down, defense |
| cheat on | `0x8800` — face-up, still defense |

Clearing an **already-placed** field record works too, but only shows once
something rebuilds the view, so the shipped row sweeps records 15–29 every frame.

## Why the shipped row clears the BIT, not the byte

GameShark can only write a byte, so `0080` stomps `0x4000/0x2000/0x1000/0x0800`
together. On a hand record that is harmless. On a **field** record it also
clears `0x0800` — measured: `0x9800 -> 0x8000` — which silently flips a
defending monster into attack position. That is a real state change, not a
cosmetic one, so the row clears only `0x1000`.

The row is one-way by design: switching it off stops clearing, it does not put
`0x1000` back. Re-hiding a card the battle code has already resolved as face-up
would desync display from logic.
