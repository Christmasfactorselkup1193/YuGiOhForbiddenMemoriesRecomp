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

static void free_spending_tick(void) {
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

/* --- SHOW OPPONENT HAND --------------------------------------------------
 * The duel keeps one 0x20-byte struct per duellist — 0x800E9FF0 for the
 * player, 0x800EA010 for the opponent — and byte +0x1F of each is a SIGNED
 * "keep this hand face down" flag. Nothing here draws anything: the game
 * already knows how to draw their hand exactly like yours, and this only
 * clears the flag that tells it not to.
 *
 * Read three times, all in the card-display path, all testing the SIGN:
 *
 *   0x80017DF0 / 0x80017E20 (func_80017DB4)  hand card -> display byte +103
 *   0x80018058              (func_80018004)  same, single-card path
 *   0x800232C0              (func_80023144)  card tint byte at 0x8009B34E
 *
 * Zero skips the hide path outright; only a NEGATIVE value makes the first two
 * write 255 — the "card back" graphic index — instead of the real artwork
 * index, and makes the third leave the card on its dimmed tint. So clearing
 * the byte both turns the backs into real card sprites (art, name, ATK/DEF)
 * and un-greys them, through the game's own renderer.
 *
 * Duel init seeds both structs from one global (0x8001767C–0x80017690) and
 * then, for a CPU opponent, overwrites the opponent's copy with -1
 * (0x800176A8 `li $v0,-1`; 0x800176AC `sb $v0,-0x5FD1($v1)` => 0x800EA02F).
 * This is the flag the well-known `300EA02F 0000` GameShark code clears.
 *
 * Per frame, not once: a block copy at 0x8007431C rewrites +0x1A..+0x1F as a
 * unit — measured once per opponent turn across a full traced turn — so a
 * single write gets undone. Only a negative value is replaced, so a duel the
 * game itself chose to show face-up is never touched, and switching the row
 * off restores the -1 only if we were the ones who cleared it. */
static const uint32_t PSX_OPP_HAND_FLAG = 0x800EA02Fu;
static int g_show_opp_hand = 0;
static int s_opp_forced = 0;

static void show_opp_hand_tick(void) {
    if (!psx_mod_game_started()) { s_opp_forced = 0; return; }
    const int flag = (int)(int8_t)psx_mod_read_byte(PSX_OPP_HAND_FLAG);
    if (g_show_opp_hand) {
        if (flag < 0) {
            psx_mod_write_byte(PSX_OPP_HAND_FLAG, 0u);
            s_opp_forced = 1;
        }
    } else if (s_opp_forced) {
        if (flag >= 0) psx_mod_write_byte(PSX_OPP_HAND_FLAG, 0xFFu);
        s_opp_forced = 0;
    }
}

/* --- FORCE FACE-UP -------------------------------------------------------
 * The duel keeps one 28-byte record per card in play from 0x801A7AE4:
 * 0-4 player hand, 5-14 player field, 15-19 opponent hand, 20-29 opponent
 * field. Halfword +10 is that card's flags, and **bit 0x1000 is "face down"**.
 *
 * Unlike SHOW OPPONENT HAND, this bit is real game state, not just display.
 * It is read by the display builders (0x80017EA0, 0x800180C0, 0x8001EA20 —
 * each turns it into a sprite attribute byte) AND by the battle routine
 * `func_8001D670` at 0x8001E700, which is what flips a set monster face-up
 * when it is attacked. Clearing it does not merely draw the card face-up; the
 * card genuinely IS face-up, and will not flip when attacked.
 *
 * The placement routine `func_8001BD8C` ORs 0x1000 in as the AI puts a card
 * down (0x8001C3A8, 0x8001CCE4) and the field record inherits it from the hand
 * record. Measured on a specimen where the AI was forced to set a monster: the
 * card lands as 0x9800 (face-down + defense) stock, and as 0x8800 (defense,
 * face-up) with the hand record pre-cleared. Clearing an ALREADY-placed field
 * record works too, but only redraws when something rebuilds the view, so both
 * ranges are swept every frame.
 *
 * This is the well-known `5000051C 0000` + `301A7C93 0080` GameShark pair —
 * a repeat modifier writing 0x80 to +11 (the flags high byte) of records 15-19.
 * We clear the BIT rather than stomping the byte: GameShark had no choice, but
 * the byte also carries 0x0800 (defense position), and stomping it flips a
 * defending monster into attack. Measured — that is a real state change, not a
 * cosmetic one, so it is not something a "show me their cards" row should do.
 *
 * One-way on purpose: switching the row off stops clearing, it does not put
 * 0x1000 back. Re-hiding a card the game has already resolved as face-up would
 * desync the display from what the battle code just used. */
#define PSX_CARD_RECORDS    0x801A7AE4u
#define PSX_CARD_STRIDE     28u
#define PSX_CARD_OFF_FLAGS  10u
#define PSX_CARD_FACEDOWN   0x1000u
#define PSX_OPP_REC_FIRST   15u   /* 15-19 hand, 20-29 field */
#define PSX_OPP_REC_LAST    29u
#define PSX_CARD_ID_MAX     722u

static int g_force_faceup = 0;

static void force_faceup_tick(void) {
    if (!g_force_faceup || !psx_mod_game_started()) return;
    for (uint32_t r = PSX_OPP_REC_FIRST; r <= PSX_OPP_REC_LAST; r++) {
        const uint32_t a = PSX_CARD_RECORDS + r * PSX_CARD_STRIDE;
        /* Only touch a slot holding a real card. Between duels these records
         * keep stale ids with zeroed flags, and this way an uninitialised
         * buffer is never written. */
        const uint32_t id = psx_mod_read_half(a);
        if (id < 1u || id > PSX_CARD_ID_MAX) continue;
        const uint32_t f = psx_mod_read_half(a + PSX_CARD_OFF_FLAGS);
        if (f & PSX_CARD_FACEDOWN)
            psx_mod_write_half(a + PSX_CARD_OFF_FLAGS,
                               (uint16_t)(f & ~PSX_CARD_FACEDOWN));
    }
}

void psx_ygo_cheats_tick(void) {
    show_opp_hand_tick();
    force_faceup_tick();
    free_spending_tick();
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

/* The tick does the guest writes, so these only move a switch.
 *
 * The toast is for a player who just moved the row, not for the settings file.
 * `psx_video_menu_apply_restored()` replays on_change for every restored row as
 * the game starts, so an unguarded toast greets every launch with a setting
 * nobody touched — "Their cards: face up" on startup, even when the restored
 * value was OFF and nothing had changed. psx_video_menu_is_restoring() is set
 * only during that replay, which is the one thing a callback cannot otherwise
 * tell about its own caller. */
static void show_opp_hand_changed(int value) {
    g_show_opp_hand = value ? 1 : 0;
    if (psx_video_menu_is_restoring()) return;
    host_osd_push(g_show_opp_hand ? "Opponent's hand: shown"
                                  : "Opponent's hand: hidden", 900);
}

static void force_faceup_changed(int value) {
    g_force_faceup = value ? 1 : 0;
    if (psx_video_menu_is_restoring()) return;
    host_osd_push(g_force_faceup ? "Their cards: face up"
                                 : "Their cards: as dealt", 900);
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
static const char *const OPPHAND_HINTS[] = {
    "THEIR HAND STAYS FACE DOWN",
    "THEIR HAND IS DRAWN LIKE YOURS"
};
static const char *const FACEUP_HINTS[] = {
    "THEY MAY SET CARDS FACE DOWN",
    "THEIR SET CARDS PLAY FACE UP - NO FLIP ON ATTACK"
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

    /* Also a preference: the per-frame guard writes one duel-display flag and
     * touches no save data, so it carries a settings key too. */
    h = psx_video_menu_add_option(
        PSX_VM_MENU_CHEATS, "SHOW OPPONENT HAND", OPPHAND_HINTS[0],
        ONOFF_LABELS, 2, "show_opponent_hand", 0, show_opp_hand_changed);
    psx_video_menu_set_row_hints(h, OPPHAND_HINTS);

    h = psx_video_menu_add_option(
        PSX_VM_MENU_CHEATS, "FORCE FACE UP", FACEUP_HINTS[0],
        ONOFF_LABELS, 2, "force_face_up", 0, force_faceup_changed);
    psx_video_menu_set_row_hints(h, FACEUP_HINTS);

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
