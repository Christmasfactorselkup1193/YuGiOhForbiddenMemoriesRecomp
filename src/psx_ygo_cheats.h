/* psx_ygo_cheats.h — the CHEATS menu and the guest writes behind it.
 *
 * Yu-Gi-Oh! Forbidden Memories only. These rows used to live inside the
 * shared overlay menu and their guest writes inside main.cpp, which meant every
 * other title built on this framework compiled a CHEATS menu offering
 * StarChips. They register themselves here instead.
 *
 * Three of the six are LIVE SAVE DATA, not preferences: StarChips, ALL CARDS
 * and the free-spending refund all touch the player's actual collection. They
 * are applied only when the row changes and are never persisted or re-applied
 * at startup, because restoring them would overwrite a real save. The other
 * three are preferences and carry settings keys: LIFE POINTS patches a code
 * constant, SHOW OPPONENT HAND clears one duel-display flag per frame, and
 * FORCE FACE UP clears the face-down bit on the opponent's cards. None can
 * damage a save, so all three are safe to restore at startup.
 */
#ifndef PSX_YGO_CHEATS_H
#define PSX_YGO_CHEATS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Stock starting life points. The duel loads this constant from two sites. */
#define PSX_VM_LIFE_POINTS_DEFAULT 8000

/* Adds the CHEATS rows to the overlay menu. Call before the settings file is
 * read, so a stored LIFE POINTS value has a row to land in. */
void psx_ygo_cheats_register_menu(void);

/* Per-frame guard for FREE SPENDING, SHOW OPPONENT HAND and FORCE FACE UP.
 * Cheap and self-disabling when the rows are off or no game is running. */
void psx_ygo_cheats_tick(void);

#ifdef __cplusplus
}
#endif

#endif /* PSX_YGO_CHEATS_H */
