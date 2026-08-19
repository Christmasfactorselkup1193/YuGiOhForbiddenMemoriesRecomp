/* psx_ygo_cheats.c — see psx_ygo_cheats.h.
 *
 * Lifted out of main.cpp and the shared overlay menu unchanged: the addresses,
 * the reasoning that found them and the ordering constraints are all as they
 * were when they were measured. What changed is only where they live and how
 * the rows reach them — each row now calls its own handler directly instead of
 * being relayed through a menu-state struct the framework had to carry fields
 * for.
 */

#include "psx_ygo_cheats.h"

#include <stddef.h>
#include <stdint.h>

#include "host_osd.h"
#include "mod_plugins.h"
#include "psx_game_hooks.h"
#include "psx_video_menu.h"

/* --- Free spending -------------------------------------------------------
 * The StarChip total is a read-modify-write: `$v0 = $v0 + $v1` at 0x80021EE0
 * then `sw $v0, 0x5E0($a0)`. A single patched instruction cannot express
 * "ignore negative deltas but keep positive ones" — freezing the add would
 * block earnings too. So this watches the live field once per frame and puts
 * back any DECREASE, while letting increases through. The purchase itself
 * still succeeds (the game has already granted the item); only the deduction
 * is undone. */
static const uint32_t PSX_STARCHIPS_ADDR = 0x801D07E0u;
static int      g_free_spending = 0;
static uint32_t s_sc_last = 0;
static int      s_sc_tracking = 0;

void psx_ygo_cheats_tick(void) {
    if (!g_free_spending || !psx_mod_game_started()) {
        s_sc_tracking = 0;
        return;
    }
    uint32_t cur = psx_mod_read_word(PSX_STARCHIPS_ADDR);
    /* Ignore obvious garbage: the field is small in practice, and a wild value
     * means we are mid-load or looking at an uninitialised buffer. */
    if (cur > 9999999u) { s_sc_tracking = 0; return; }
    if (!s_sc_tracking) { s_sc_last = cur; s_sc_tracking = 1; return; }
    if (cur < s_sc_last)
        psx_mod_write_word(PSX_STARCHIPS_ADDR, s_sc_last);   /* refund */
    else
        s_sc_last = cur;                                     /* keep earnings */
}

/* --- LIFE POINTS ---------------------------------------------------------
 * The stock EXE loads the constant with `addiu $v0, $zero, 0x1F40` (8000)
 * at two sites: 0x800175D0 stores it as a halfword pair on the stack (both
 * duellists), 0x8002DC70 stores it to the global at 0x8009B236. Rewriting
 * the whole instruction as `addiu $v0, $zero, <lp>` covers both.
 *
 * psx_mod_write_code_word (not write_word) routes the address through the
 * executable-RAM path, so the text guard revokes the statically recompiled
 * block and the interpreter picks up the new immediate — and a restored save
 * state cannot leave a stale compiled instruction behind.
 *
 * addiu sign-extends its 16-bit immediate, so keep values under 32768. */
static void lp_changed(int value) {
    if (!psx_mod_game_started()) return;
    if (value < 1) value = 1;
    if (value > 32767) value = 32767;
    psx_mod_write_code_word(0x800175D0u, 0x24020000u | (uint32_t)value);
    psx_mod_write_code_word(0x8002DC70u, 0x24020000u | (uint32_t)value);
}

/* --- STARCHIPS -----------------------------------------------------------
 * Located by RAM scan + write trace: a 32-bit field at offset 0x5E0 in a
 * 0x680-byte game-state struct, live copy at 0x801D0200 => 0x801D07E0. The
 * award/spend routine at 0x80021EE0 does `$v0 = $v0 + $v1` then
 * `sw $v0, 0x5E0($a0)`, which is what confirmed the offset.
 *
 * Two mirrors exist (0x801D37E0, 0x801D3E60) but they are memcpy'd FROM the
 * live block, so writing the live copy is what propagates — writing a mirror
 * would display correctly and then be overwritten. */
static void starchips_changed(int value) {
    if (!psx_mod_game_started() || value <= 0) return;
    psx_mod_write_word(PSX_STARCHIPS_ADDR, (uint32_t)value);
    s_sc_tracking = 0;   /* re-baseline so the guard does not refund this */
    host_osd_push("StarChips set", 1200);
}

static void free_spending_changed(int value) {
    g_free_spending = value ? 1 : 0;
    if (!g_free_spending) s_sc_tracking = 0;
    host_osd_push(g_free_spending ? "Free spending: on" : "Free spending: off", 900);
}

/* --- ALL CARDS -----------------------------------------------------------
 * The trunk is a 722-byte array of per-card counts, card N at +(N-1), at
 * save-struct +0x50. Located 2026-08-16 by known-value search against three
 * counts read off the chest screen (Horn Imp #25 = 1, Griffore #46 = 1, Aqua
 * Snake #446 = 0). Exactly three regions in RAM match the signature and ALL
 * THREE must be written:
 *
 *   0x801D0250  live save struct (+0x50)
 *   0x801D3250  the known mirror (+0x3000)
 *   0x80105D98  third copy — the chest UI's working buffer
 *
 * Writing only the live copy does NOT stick: the chest screen rebuilds from
 * its own buffer and puts the old values straight back (measured — the first
 * attempt was reverted in full). Apply with the chest CLOSED, which is what
 * the row's hint tells the player. */
static void all_cards_changed(int value) {
    if (!psx_mod_game_started() || value <= 0) return;
    static const uint32_t kTrunkBases[] = {
        0x801D0250u, 0x801D3250u, 0x80105D98u
    };
    const uint8_t n = (uint8_t)(value > 3 ? 3 : value);
    for (size_t b = 0; b < sizeof(kTrunkBases) / sizeof(kTrunkBases[0]); b++)
        for (uint32_t i = 0; i < 722u; i++)
            psx_mod_write_byte(kTrunkBases[b] + i, n);
    host_osd_push("All cards granted", 1500);
}

/* --- the rows ------------------------------------------------------------ */

static const char *const ONOFF_LABELS[] = { "OFF", "ON" };
static const char *const ONOFF_HINTS[]  = {
    "REFUND ANY STARCHIP SPEND",
    "PURCHASES REFUNDED - EARNINGS STILL COUNT"
};
static const char *const ALLCARDS_LABELS[] = {
    "OFF", "1 OF EACH", "2 OF EACH", "3 OF EACH"
};
static const char *const ALLCARDS_HINTS[] = {
    "FILL THE TRUNK WITH EVERY CARD",
    "APPLY WITH THE CHEST CLOSED",
    "APPLY WITH THE CHEST CLOSED",
    "APPLY WITH THE CHEST CLOSED"
};

PSX_MOD_CONSTRUCTOR(psx_ygo_cheats_install) {
    psx_ygo_cheats_register_menu();
    (void)psx_game_add_frame_hook(psx_ygo_cheats_tick);
}

void psx_ygo_cheats_register_menu(void) {
    int h;

    /* A preference: it patches a code constant, not save data, so it carries a
     * settings key and is restored at startup like any other setting. The
     * slider spans 1..9999 because the game's LP display is four digits, even
     * though the patched addiu would allow up to 32767. */
    h = psx_video_menu_add_number(
        PSX_VM_MENU_CHEATS, "LIFE POINTS", "8000 IS STOCK. ENTER TO TYPE",
        1, 9999, /*slider*/1, "life_points",
        PSX_VM_LIFE_POINTS_DEFAULT, lp_changed);
    psx_video_menu_set_row_mark(h, PSX_VM_LIFE_POINTS_DEFAULT);

    /* The remaining three are live save writes: NULL settings key, so they are
     * never written to the file and never re-applied at startup. */
    h = psx_video_menu_add_number(
        PSX_VM_MENU_CHEATS, "STARCHIPS", "ENTER TO TYPE A VALUE",
        0, 99999, /*slider*/0, NULL, 0, starchips_changed);
    (void)h;

    h = psx_video_menu_add_option(
        PSX_VM_MENU_CHEATS, "FREE SPENDING", ONOFF_HINTS[0],
        ONOFF_LABELS, 2, NULL, 0, free_spending_changed);
    psx_video_menu_set_row_hints(h, ONOFF_HINTS);

    h = psx_video_menu_add_option(
        PSX_VM_MENU_CHEATS, "ALL CARDS", ALLCARDS_HINTS[0],
        ALLCARDS_LABELS, 4, NULL, 0, all_cards_changed);
    psx_video_menu_set_row_hints(h, ALLCARDS_HINTS);
}
