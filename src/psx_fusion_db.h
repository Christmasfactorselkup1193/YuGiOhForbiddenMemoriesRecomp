#ifndef PSX_FUSION_DB_H
#define PSX_FUSION_DB_H

/* The game's own fusion data — Yu-Gi-Oh! Forbidden Memories.
 *
 * Answers "what do these two cards make?" by running the guest's own lookup
 * over the guest's own tables, read live out of guest RAM. No baked table, no
 * reimplemented rules: every address and every step below was read off the
 * recompiled routines the game calls when a fusion resolves, so this stays
 * correct for any build of the game whose data lives at those addresses, and
 * fails closed (`psx_fusion_db_ready` returns 0) when it does not.
 *
 * This file is data and queries only. Nothing here knows about a duel, a hand
 * or a screen — psx_fusion_assist.c owns that.
 */

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* How a pair resolved, so a caller can tell a real fusion from an equip. */
enum {
    PSX_FUSION_NONE  = 0,   /* the two cards do not combine */
    PSX_FUSION_PAIR  = 1,   /* the fusion table produced a new card */
    PSX_FUSION_EQUIP = 2    /* an equip attached; the surviving monster is the
                             * result, powered up rather than replaced */
};

#define PSX_FUSION_CARD_ID_MAX 722

/* Are the guest's fusion tables present and sane? Cheap to call; the answer is
 * re-derived whenever it was previously false, so this goes true on its own
 * once the game's data segment is in place. */
int psx_fusion_db_ready(void);

/* The result of putting `second` onto `first`, exactly as the duel would
 * resolve it. Returns the resulting card id, or 0 when they do not combine.
 * `out_kind` (optional) receives one of the PSX_FUSION_* values.
 *
 * The ORDER matters for equips only: the surviving card is the monster, so
 * (monster, equip) and (equip, monster) both yield the monster. It never
 * matters for the fusion table, which sorts its two arguments itself. */
uint16_t psx_fusion_db_result(uint16_t first, uint16_t second, int *out_kind);

/* A card's printed stats, from the game's own card table. Returns 1 on
 * success, 0 if the id is out of range or the table is not resident. `atk` and
 * `def` come back in points (not the table's tens), `type` is the game's 5-bit
 * type code: 0 Dragon, 1 Spellcaster, 2 Zombie, 3 Warrior, 4 Beast-Warrior,
 * 5 Beast, 6 Winged Beast, 7 Fiend, 8 Fairy, 9 Insect, 10 Dinosaur,
 * 11 Reptile, 12 Fish, 13 Sea Serpent, 14 Machine, 15 Thunder, 16 Aqua,
 * 17 Pyro, 18 Rock, 19 Plant, and above that the non-monster kinds. Any
 * pointer may be NULL. */
int psx_fusion_db_stats(uint16_t id, int *atk, int *def, int *type);

/* ---- debug-server surface ---------------------------------------------- */

/* Table geometry and the validation verdict, for `fusion_db`. Any pointer may
 * be NULL. `pairs` and `equips` are full walks, so this is a diagnostic, not
 * something to call every frame. */
void psx_fusion_db_debug(int *ready, uint32_t *pair_base, uint32_t *equip_base,
                         int *cards_with_fusions, int *pairs,
                         int *equip_groups, int *equip_members);

#ifdef __cplusplus
}
#endif

#endif /* PSX_FUSION_DB_H */
