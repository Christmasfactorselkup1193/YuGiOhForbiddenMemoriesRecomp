#ifndef PSX_FUSION_ASSIST_H
#define PSX_FUSION_ASSIST_H

/* In-duel fusion assistant — Yu-Gi-Oh! Forbidden Memories.
 *
 * Reads the live duel's hand out of guest RAM and works out what it can make,
 * using psx_fusion_db for every "what does X + Y give?" question. The guest
 * addresses for the duel side of that live here; the fusion data's addresses
 * live in psx_fusion_db.c.
 *
 * No UI yet: this is the logic half, plus the debug-server surface that makes
 * it checkable before a single pixel is drawn.
 */

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PSX_FUSION_HAND_MAX 5

typedef struct PsxFusionCard {
    uint16_t id;
    uint16_t atk;
    uint16_t def;
    uint16_t flags;   /* record+10; reported for inspection, not trusted as
                       * hand membership -- see the .c file on why */
    uint8_t  slot;    /* index into the guest's card-record array */
} PsxFusionCard;

/* Snapshot the hand. Returns the number of cards written (0 when no duel is in
 * progress, which is also what a non-duel screen reads as). */
int psx_fusion_assist_hand(PsxFusionCard *out, int cap);

/* ---- debug-server surface ---------------------------------------------- */

/* `fusion_hand`: the raw card-record window the hand is read from, so the
 * "which slots are the hand" rule can be checked against live data rather
 * than assumed. Writes a JSON array; returns bytes written. */
int psx_fusion_assist_hand_json(char *out, unsigned cap);

/* `fusion_list`: every pair in the current hand that combines, with what it
 * makes, best first by the result's attack. Writes a JSON object; returns
 * bytes written. */
int psx_fusion_assist_list_json(char *out, unsigned cap);

/* `fusion_try`: what the game would make of these two card ids, independent of
 * the hand. The direct read-back for psx_fusion_db. */
int psx_fusion_assist_try_json(char *out, unsigned cap, int a, int b);

/* The cards the player has picked so far, in PICK order (which is the order
 * the game folds them in), and what would stand if they summoned now. Writes
 * up to `cap` steps and returns how many; `out_result` is the standing card,
 * 0 when nothing is picked. This is the chain preview's whole logic half. */
int psx_fusion_assist_chain(PsxFusionCard *steps, int cap, uint16_t *out_result);

/* `fusion_chain`: the above as JSON, with the running result after each pick. */
int psx_fusion_assist_chain_json(char *out, unsigned cap);

/* Rank the best line by defence instead of attack. */
void psx_fusion_assist_set_rank(int by_defence);
int  psx_fusion_assist_get_rank(void);

/* The best monster this hand can make, using as few cards as
 * possible. Writes the slots to pick, in the order to pick them, and returns
 * how many. 0 means the hand makes nothing. Any pointer may be NULL. */
int psx_fusion_assist_best(uint16_t *result, int *atk, int *def, int *cards,
                           uint8_t *pick, int pick_cap);

/* `fusion_best`: the above as JSON. */
int psx_fusion_assist_best_json(char *out, unsigned cap);

/* The hand gate: which slots the game currently treats as pickable, its own
 * selection count, and whose turn it is (0 player, 1 opponent). Any pointer
 * may be NULL. */
void psx_fusion_assist_hand_source(int *mask, int *sel_count, int *turn);

#ifdef __cplusplus
}
#endif

#endif /* PSX_FUSION_ASSIST_H */
