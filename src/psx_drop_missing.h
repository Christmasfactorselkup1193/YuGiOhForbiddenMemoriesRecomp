/* psx_drop_missing.h — MODS > DROP MISSING CARDS.
 *
 * Yu-Gi-Oh! Forbidden Memories only. 82 of the game's 722 cards are dropped by
 * nobody — Exodia's two legs among them, which is why the set cannot be
 * completed by duelling in stock FM. This gives every one of them a home.
 *
 * Nothing is patched on disc. The duel loads the current opponent's drop
 * weights into RAM; this rewrites that copy, so the game rolls its own tables
 * and the change lasts exactly as long as the duel does.
 *
 * The placement is editable: drop_missing_cards.ini in the player-data folder
 * is written on first run from the built-in defaults, and read back after.
 */
#ifndef PSX_DROP_MISSING_H
#define PSX_DROP_MISSING_H

#ifdef __cplusplus
extern "C" {
#endif

/* Adds the MODS row. Call before the settings file is read so a stored value
 * has a row to land in. */
void psx_drop_missing_register_menu(void);

/* Per-frame guard. Cheap: it samples a few words and only does real work when
 * the resident drop table changes, which is once per duel. */
void psx_drop_missing_tick(void);

/* Debug-server read-back: what the mod thinks is going on. */
int psx_drop_missing_state_json(char *out, unsigned cap);

#ifdef __cplusplus
}
#endif

#endif /* PSX_DROP_MISSING_H */
