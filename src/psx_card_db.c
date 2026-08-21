/* psx_card_db.c — see psx_card_db.h.
 *
 * WHERE THE DATA IS (all measured, none of it from a FAQ)
 * -------------------------------------------------------
 * Card names are a text STREAM, not an array of strings:
 *
 *     stream = 0x801D0000 + u16[0x801D5800 + id*2]      terminated by 0xFF
 *
 * The u16 table reads like a length table because names sit back to back, but
 * it is an offset table into the segment at 0x801D0000. Found 2026-08-17 by
 * forcing a known card to drop and write-tracing the widget that displays its
 * name; the dispatcher that does this lives at 0x8003944C.
 *
 * The bytes are NOT ASCII and NOT the glyph charset — they are a frequency
 * code, so 0x01 is 'e' and 0x02 is 't'. See RAW_ASCII below for the map and,
 * more to the point, for how it is checked; hand-transcribing it is how an
 * earlier pass shipped "<29>aia the Dragon Champion".
 *
 * Stats are one packed word per card:
 *
 *     w = u32 at 0x801D4244 + (id-1)*4
 *     attack  = (w        & 0x1FF) * 10
 *     defence = ((w >> 9) & 0x1FF) * 10
 *     type    = (w >> 26) & 0x1F
 *
 * read off the routine that fills a card record when a hand is dealt
 * (0x80024A94..0x80024B24). psx_fusion_db.c already relies on this and checks
 * out against 614 of the 620 cards a published guide lists, every disagreement
 * being the guide's.
 */

#include "psx_card_db.h"

#include <string.h>

#include "mod_plugins.h"

#define NAME_OFFSETS  0x801D5800u   /* u16 per card id */
#define NAME_SEGMENT  0x801D0000u   /* offsets are relative to here */
#define STATS_BASE    0x801D4244u   /* u32 per card, indexed by id-1 */

#define NAME_MAX  40u               /* longest stock name is well under this */

/* An escape introducer. Card-name streams do not use escapes, but a stream
 * read from a table that is not resident could contain anything, so stop
 * rather than decode 0xF8's operand as a letter. */
#define ESC 0xF8u
#define END 0xFFu

static int  s_ready;
static char s_name[PSX_CARD_DB_COUNT + 1][NAME_MAX];

/* The card table is the cheapest thing to test and the last thing to appear:
 * card 1 is Blue-Eyes and its word is non-zero in every resident copy, while
 * the whole region reads as zeros before the EXE has loaded its data. */
static int table_resident(void)
{
    return psx_mod_read_word(STATS_BASE) != 0u
        && psx_mod_read_half(NAME_OFFSETS + 2u) != 0u;
}

/* Raw code -> ASCII, 0 where nothing is known.
 *
 * This is a FREQUENCY code, which is why it looks arbitrary: 0x01 is 'e' and
 * 0x02 is 't' because those are the commonest letters in the card list. The
 * game's own table at 0x801D9000 is NOT a substitute — its low byte is an
 * index into the game's font, not a character, and reading it that way
 * produced names like "a: v c".
 *
 * Checked, not trusted: all 722 names were decoded against this table before
 * it was used, and anything it does not cover renders as <xx> in the name
 * rather than vanishing from it. That is exactly how the last two missing
 * codes were found — 0x1F in "30,000-Year White Turtle" and 0x55 in
 * "Kuwagata a", where the game draws a Greek alpha an 8x8 ASCII font has no
 * room for. That one card is the only imprecision in the list.
 */
static const char RAW_ASCII[128] = {
    /* 00 */ ' ',   'e',   't',   'a',   'o',   'i',   'n',   's',
    /* 08 */ 'r',   'h',   'l',   '.',   'd',   'u',   'm',   'c',
    /* 10 */ 'g',   'y',   'w',   'f',   'p',   'b',   'k',   0,
    /* 18 */ 'A',   'v',   'I',   '\'',  'T',   'S',   'M',   ',',
    /* 20 */ 'D',   'O',   'W',   'H',   'Y',   'E',   'R',   0,
    /* 28 */ 0,     'G',   'L',   'C',   'N',   'B',   0,     'P',
    /* 30 */ '-',   'F',   'z',   'K',   'j',   'U',   'x',   'q',
    /* 38 */ '0',   'V',   '2',   'J',   '#',   '1',   'Q',   'Z',
    /* 40 */ 0,     '3',   '5',   '&',   0,     '7',   'X',   0,
    /* 48 */ 0,     0,     '4',   0,     0,     0,     '6',   0,
    /* 50 */ 0,     0,     0,     0,     0,     'a',   0,     '8',
    /* 58 */ 0,     '9',   0,     0,     0,     0,     0,     0,
    /* 60 */ 0,     0,     0,     0,     0,     0,     0,     0,
    /* 68 */ 0,     0,     0,     0,     0,     0,     0,     0,
    /* 70 */ 0,     0,     0,     0,     0,     0,     0,     0,
    /* 78 */ 0,     0,     0,     0,     0,     0,     0,     0,
};

static char raw_to_ascii(unsigned raw)
{
    if (raw >= 128u) return 0;
    return RAW_ASCII[raw];
}

static void decode_name(int id, char *out, unsigned cap)
{
    out[0] = '\0';
    if (id < 1 || id > PSX_CARD_DB_COUNT) return;
    const uint32_t off = psx_mod_read_half(NAME_OFFSETS + (uint32_t)id * 2u);
    const uint32_t a = NAME_SEGMENT + off;
    unsigned n = 0;
    for (unsigned i = 0; i < NAME_MAX * 2u && n + 1u < cap; i++) {
        const unsigned raw = psx_mod_read_byte(a + i);
        if (raw == END || raw == ESC) break;
        const char g = raw_to_ascii(raw);
        if (g) {
            out[n++] = g;
        } else if (n + 5u < cap) {
            /* Say what was there. A dropped letter is a name that reads fine
             * and is wrong; <2f> is a name that reads oddly and can be fixed. */
            static const char HEX[] = "0123456789abcdef";
            out[n++] = '<';
            out[n++] = HEX[(raw >> 4) & 0xFu];
            out[n++] = HEX[raw & 0xFu];
            out[n++] = '>';
        }
    }
    /* Trailing spaces come from the stream's own padding, not from us. */
    while (n && out[n - 1] == ' ') n--;
    out[n] = '\0';
}

static void ensure(void)
{
    if (s_ready) {
        if (table_resident()) return;
        s_ready = 0;                /* the game went away under us */
    }
    if (!table_resident()) return;
    for (int id = 1; id <= PSX_CARD_DB_COUNT; id++)
        decode_name(id, s_name[id], NAME_MAX);
    s_name[0][0] = '\0';
    s_ready = 1;
}

int psx_card_db_ready(void)
{
    ensure();
    return s_ready;
}

const char *psx_card_db_name(int id)
{
    ensure();
    if (!s_ready || id < 1 || id > PSX_CARD_DB_COUNT) return "";
    return s_name[id];
}

int psx_card_db_stats(int id, int *atk, int *def, int *type)
{
    if (id < 1 || id > PSX_CARD_DB_COUNT) return 0;
    const uint32_t w = psx_mod_read_word(STATS_BASE + ((uint32_t)id - 1u) * 4u);
    if (!w) return 0;
    if (atk)  *atk  = (int)(w & 0x1FFu) * 10;
    if (def)  *def  = (int)((w >> 9) & 0x1FFu) * 10;
    if (type) *type = (int)((w >> 26) & 0x1Fu);
    return 1;
}

/* Type codes as the game numbers them. The mapping was checked by psx_fusion_db
 * against 614 cards; the strays were the guide's errors, not these. */
static const char *const TYPE_NAMES[] = {
    "Dragon", "Spellcaster", "Zombie", "Warrior", "Beast-Warrior",
    "Beast", "Winged Beast", "Fiend", "Fairy", "Insect", "Dinosaur",
    "Reptile", "Fish", "Sea Serpent", "Machine", "Thunder", "Aqua",
    "Pyro", "Rock", "Plant", "Magic", "Trap", "Ritual", "Equip"
};

const char *psx_card_db_type_name(int type)
{
    if (type < 0 || (unsigned)type >= sizeof(TYPE_NAMES) / sizeof(TYPE_NAMES[0]))
        return "?";
    return TYPE_NAMES[type];
}

void psx_card_db_invalidate(void)
{
    s_ready = 0;
}
