/* psx_card_db.h — the game's own card list, read out of the running game.
 *
 * Names, ATK and DEF all live in the game EXE's data and are resident from the
 * moment it starts, so nothing here is baked from the disc: the viewer asks
 * the machine. That also means the answers are the game's answers, including
 * the handful of places the published FAQs are wrong.
 *
 * Everything is cached on first use — 722 names decoded a glyph at a time is
 * not something to redo per frame — and the cache is dropped when the table
 * stops looking resident, so a savestate load or a fresh boot re-reads it.
 */
#ifndef PSX_CARD_DB_H
#define PSX_CARD_DB_H

#include <stdint.h>

#define PSX_CARD_DB_COUNT 722

/* 0 until the game EXE is resident. Everything below returns empty/zero until
 * this is true, so a caller can render an "waiting for the game" state rather
 * than a table of blanks. */
int psx_card_db_ready(void);

/* Decoded ASCII, never NULL — an unknown id gives "". Owned by this module. */
const char *psx_card_db_name(int id);

/* The game's own values: attack, defence, and its 5-bit type code. Returns 0
 * and leaves the outputs alone if the card table is not resident. */
int psx_card_db_stats(int id, int *atk, int *def, int *type);

/* Human name for a type code, "?" if it is one nothing has been seen to use. */
const char *psx_card_db_type_name(int type);

/* Re-read everything on the next call. Cheap; call it when the game may have
 * been replaced under us (savestate load, disc change). */
void psx_card_db_invalidate(void);

#endif /* PSX_CARD_DB_H */
