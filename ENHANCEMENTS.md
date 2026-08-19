# Yu-Gi-Oh! Forbidden Memories — enhancement candidates

Per-game enhancement ideas (framework-wide work lives in
`psxrecomp/ENHANCEMENTS.md`). Written 2026-08-16 after reading the six
GameFAQs guides in `docs/`.

Effort ratings are honest guesses, not commitments. **Risk** means risk to the
player's save or to game correctness, not implementation difficulty.

---

## 0. The unlock: extract the game's OWN data tables

**Almost everything valuable below depends on one foundational task, and they
all share it.** FM keeps its data in tables the game reads at runtime:

| table | contents | used by |
|---|---|---|
| card table | ~722 cards: name, type, ATK/DEF, guardian stars, level | 1, 2, 3, 4, 6 |
| fusion table | which type-pairs and specific cards fuse into what | 1, 2 |
| drop tables | per duelist x 3 rank tiers, as **n-in-2048** | 3, 4, 8 |
| password table | password -> card id + starchip cost | 6 |

Extract these from the game rather than transcribing the guides. The guides are
a **cross-check oracle**, not the source: the drop-rate guide states its numbers
came from the game's internal data, so a correct extraction must reproduce it.
Transcribing 722 cards and hundreds of fusions by hand would inject errors that
then look like emulation bugs.

Method is the one this project already uses: find a known value in RAM
(`read_ram` + intersect across changes), `wtrace_range` to get the reading PC,
grep `generated/` to read the routine and learn the record layout. A card's name
string is an easy anchor.

**Do this first.** It is the difference between "a weekend of UI work" and "a
month of data entry" for every feature in Tier 1.

---

## Tier 1 — Quality-of-life overlays

Host-side only: read guest RAM, draw in the existing F10/OSD layer, never write
to the game. Lowest risk in the project — nothing can corrupt a save.

### 1. Fusion helper (live) — **the headline feature**
Read the cards currently in hand and show which pairs fuse, and into what.
FM's fusion system is its core mechanic and is completely opaque in-game: the
guide runs to 461 KB and players keep it open on a second screen. Making it
native is the single biggest change to how the game feels to play.

Note the rule is not a flat lookup — `[Dragon] + [Zombie]` yields Dragon Zombie,
Skelgon *or* Curse of Dragon depending on the higher parent's ATK, and fails
entirely above a threshold. So the helper must evaluate the real rule, which is
another reason to extract the game's table rather than a guide's prose.

*Effort: medium-high (after §0). Risk: none. Value: very high.*

### 2. Fusion browser (offline)
Searchable list: "what does X fuse with", "what makes Y". No RAM reading, so it
works from the menu at any time and is a strict subset of feature 1 — a
sensible first milestone that proves the extracted table is right.

*Effort: low (after §0). Risk: none. Value: high.*

### 3. Drop-table overlay
For the current opponent, show what they drop and at what probability, split by
the three rank tiers. Answers "is this duelist worth farming" without alt-tab.

*Effort: low-medium (after §0). Risk: none. Value: high.*

### 4. Collection tracker / "where do I farm this"
Cross-reference cards owned against the drop tables: "you are missing N cards;
the best source for each is duelist D at rank R, p%". This is the feature that
actually attacks the grind — not by changing rates, but by removing the wasted
farming of the wrong opponent.

*Effort: medium (after §0). Risk: none. Value: very high.*

### 5. Live rank meter (POW / TEC) — **DONE 2026-08-16**
Shipped as `F10 > VIEW > DUEL RANK` (OFF / IN GAME / OVERLAY TEXT). Full
write-up in `ISSUES.md`; the "genuine RE risk" below did not materialise.

The estimate is not an estimate: the game keeps every input counter live in a
per-player block and `func_80021598` merely sums them through a coefficient
table at `0x801798A8`, so the meter runs the game's own arithmetic and matched
its oracle exactly on two duels. IN GAME draws the game's own POW/TEC badge,
rank letter and card-stat digits, anchored to the FIELD box so it rides the
HUD's tween.

**The formula was found by one grep, not by RAM diffing.** The published rules
say the score "starts at 50", so `li reg, 50` across the recompiled output gave
15 sites, one inside the scoring routine — and the table address, all ten
counter addresses and the results-screen display array fell out of reading that
one function. Grep for the ALGORITHM's constants, not the DATA's: the formula's
thresholds live in a disc-loaded table that is all zeros in the EXE image.

*Was: effort high. Actually: one session, and it left behind `tools/vram_dump.py`,
`tools/gp0_decode.py` and `tools/sprite_extract.py`, which are exactly the
toolchain §0 needs.*

### 6. Password catalogue with auto-entry
List every password with its starchip cost, filterable, and enter the selected
one for the player. Removes a guide dependency and a lot of controller typing.

*Effort: low-medium (after §0). Risk: low — it drives the game's own password
screen, so the game validates everything.*

---

## Tier 2 — Grind reduction (changes the game; opt-in, default off)

### 7. Duel speed
Speed up duel animations and sequencing while music, sound and logic stay at
normal rate. **This is the feature most wanted and the least certain.** It is
not the SPEED multiplier (that speeds the whole machine, music included) and not
the CPU overclock (that changes no timing at all). It requires finding the
counters that advance duel animation state — real reverse engineering, with a
genuine chance there is no single lever and the pacing is distributed across
many per-object timers.

Cheap first probe: hunt a game-owned per-frame tick and bump it with the
existing `frame_gate` debug command (it accepts any address). If animations
speed up while music holds, the feature is basically done.

*Effort: unknown, medium-high. Risk: medium. Value: very high.*

### 8. Drop-rate options
The rates are `n`-in-2048 and many desirable cards sit at 2/2048 (0.10%). Three
possible shapes, increasingly invasive:

- **No-duplicate reroll** — if the roll gives a card already owned, roll again
  (bounded). Preserves the game's own distribution and rank incentives while
  removing the most demoralising part of the grind. *Recommended.*
- **Rate multiplier** — scale `n`, e.g. 2x/5x.
- **Guaranteed new card** on S-rank wins.

*Effort: medium (needs the drop roll site, which §0 finds anyway). Risk: medium
— it writes to the reward path. Value: high.*

### 9. Skip duel intro / instant card reveal
Cut the fixed animation preamble each duel. Overlaps feature 7 and may fall out
of it for free.

*Effort: unknown. Risk: low-medium.*

### 10. Starchip multiplier
Partly present already via CHEATS > STARCHIPS (a live write) and FREE SPENDING.
A per-duel multiplier would be the honest version of the same thing.

*Effort: low. Risk: low. Value: medium.*

---

## Tier 3 — Presentation

### 11. Smoother animation via CPU overclock — **prototyped, works**
FM drops roughly one frame in four during active play (~49/s of an attempted
60) because its loop overruns the budget on real hardware. `cpu_clock mult=12`
recovers them: **49 -> 58 fps at unchanged game speed**, measured with an
interleaved paired protocol over 80 s of normal play (framework §F2).

Remaining work: a GAME menu row (OFF / 4x / 8x / 12x, default off, honest hint),
fix the `sio_quantum_cycles` telemetry which still reports the unscaled value,
and compatibility testing — memory card writes especially, since SIO is the
subsystem this technique already broke once.

**Ceiling is 60 fps**, permanently: that is one image per vblank, and going
above it means changing the game's own update rate.

*Effort: low (the mechanism exists). Risk: medium — deliberately unfaithful
timing. Value: medium.*

### 12. Internal resolution — **done**
F10 > VIDEO > RESOLUTION, NATIVE/2X/3X/4X, restart to apply. 60 fps holds at 2x
and 3x. Currently defaults to 1x; picking a shipping default is still open.

### 13. Widescreen
The framework has a native-wide layer. FM is mostly 2D with a 3D duel field, so
the payoff is uncertain and 2D backgrounds are the usual failure point. Worth a
timeboxed experiment, no more, and note geometry correction stays OFF here
(framework §G1.10 — it cracks the arena floor).

*Effort: medium. Risk: low (presentation only). Value: unknown.*

### 14. Save states and rewind
Save states exist in the framework. Rewind is currently off because the
`retcomm-rbengine` submodule is empty. For a game with this much RNG, a save
state immediately before a drop roll is a very large lever — worth deciding
deliberately whether that is desirable or whether it trivialises the game.

*Effort: low (states) / unknown (rewind). Risk: low.*

---

## Tier 4 — Larger / speculative

### 15. True 60 fps at normal speed
Beyond feature 11's recovery of dropped frames, this needs the game's update
rate changed — i.e. patching its frame gate and halving every per-frame delta.
This is what "60 fps patches" for that class of game actually are. Large,
breakage-prone, and it interacts with feature 7.

### 16. Deck editor / trunk quality of life
Sorting and filtering in the trunk UI. Attractive, but it means modifying the
game's own UI code rather than overlaying it — a different and much harder class
of work than Tier 1.

### 17. Content mods
Randomiser, rebalance, drop-table rewrites. Everything in §0 makes these
possible; whether they belong in a "definitive edition" is a taste question.

---

## Suggested order

1. **§0 table extraction** — unlocks Tier 1 entirely, and features 7 and 8 need
   the same RE skills and landmarks.
2. **Feature 2 (fusion browser)** — proves the extracted data against the guides
   before anything depends on it.
3. **Feature 1 (live fusion helper)** — the headline.
4. **Feature 4 (collection tracker)** — attacks the grind without changing rules.
5. Then choose between **7 (duel speed)** and **8 (drop options)** depending on
   whether the grind's problem is time-per-duel or duels-per-card.

Features 11-14 are presentation polish that can land at any point; none of them
block anything else.
