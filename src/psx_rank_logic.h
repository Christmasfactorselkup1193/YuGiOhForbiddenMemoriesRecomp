/* Live duel-rank logic: reads the game's own per-duel score counters every
 * frame and drives the rank meter overlay (psx_rank_meter.c) and the OSD status
 * line from them.
 *
 * The game grades every duel 0-99 but only shows the result on the RESULTS OF
 * DUEL screen, after it is too late to steer. It keeps the input counters live
 * for the whole duel though, so the same arithmetic runs every frame -- see the
 * derivation in psx_rank_logic.c. */
#ifndef PSX_RANK_LOGIC_H
#define PSX_RANK_LOGIC_H

#ifdef __cplusplus
extern "C" {
#endif

/* Per-frame update. Cheap and self-gating: returns immediately unless the
 * player has switched the meter on and a duel is actually running. */
void psx_rank_logic_tick(void);

/* Apply a menu choice (PSX_VM_RANK_*). Out-of-range values mean OFF. Handles
 * the teardown when switching off, so callers need only pass the new value. */
/* Duel-rank meter modes. Owned here rather than by the shared menu: no other
 * title has a duel rank. */
enum { PSX_VM_RANK_OFF = 0, PSX_VM_RANK_INGAME = 1,
       PSX_VM_RANK_INGAME_SCORE = 2, PSX_VM_RANK_TEXT = 3 };

void psx_rank_logic_set_mode(int mode);

/* Adds VIEW > DUEL RANK to the overlay menu. */
void psx_rank_logic_register_menu(void);

/* Arm the GPU sprite watch the meter anchors to. Call once, after the renderer
 * exists. Harmless when the meter is off -- it costs two compares per textured
 * rect -- so it is armed unconditionally rather than on the menu path. */
void psx_rank_logic_arm_sprite_watch(void);

/* Debug-server surface; names predate the split (see psx_rank_logic.c). */
/* `show_hold` counts consecutive unoccluded frames; the meter only draws once
 * it reaches the hold, which is what stops a fusion strobing it. */
void psx_rank_meter_debug(int *mode, int *active, int *anchor,
                          int *occluded, int *x, int *y, int *show_hold);
void psx_rank_meter_fade_debug(int *fade, int *fade_t);

#ifdef __cplusplus
}
#endif

#endif /* PSX_RANK_LOGIC_H */
