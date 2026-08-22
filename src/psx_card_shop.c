/* CARD SHOP — a fifth row on the campaign shopkeeper's menu (SAVE / BUILD
 * DECK / RETURN TO TITLE / LEAVE SHOP) that opens a pack-buying panel drawn
 * in the game's own font over the game's own shop scene.
 *
 * NO CODE IS PATCHED. The whole feature rides three measured facts about the
 * game's generic menu driver (2026-08-21, all verified live):
 *
 *   - The row COUNT is data: a byte at gp+1085 = 0x8009B345. The driver
 *     (0x8003708C..0x800370D8) clamps the cursor against it, draws a
 *     highlight band for every row it allows, and plays the move blip —
 *     write 5 and a fifth, unlabeled row exists natively.
 *   - The CURSOR is a byte at gp+1093 = 0x8009B34D.
 *   - Pressing X with the cursor on the phantom row does NOTHING: the
 *     dispatcher ignores out-of-range indices (measured: state unchanged,
 *     no crash). So selection is ours to detect and act on host-side.
 *
 * Our overlay paints the row-4 band (covering the game's bare highlight
 * bleed below the panel) with a CARD SHOP label in the game's own baked
 * font, and the pack panel once opened. Purchases move real save data the
 * same way the established cheats do: starchips at 0x801D07E0, trunk
 * counts at save+0x50 (live 0x801D0200 AND mirror 0x801D3200), gated on
 * the 40-card deck signature so a save must actually be resident
 * (ISSUES #5 rule).
 *
 * Screen identity: the campaign overlay state (0x8009B23A == 0xE00D) plus
 * three descriptor bytes measured to differ between this menu and the other
 * campaign menus (0x8009B338 == 0x08, 0x8009B33A == 0xFF, 0x8009B344 ==
 * 0x20), plus a plausible row count. A false positive on some untested
 * 4-row menu would add a harmless CARD SHOP row there — cosmetic, not
 * corrupting — and the signature bytes are debug-tunable to chase that. */

#include "psx_card_shop.h"

#include <stdio.h>
#include <string.h>

#include "mod_plugins.h"
#include "psx_card_db.h"
#include "psx_fusion_font.h"
#include "psx_video_menu.h"

/* ---- measured addresses -------------------------------------------------- */
#define SHOP_STATE_ADDR   0x8009B23Au   /* campaign overlay state: 0xE00D   */
#define SHOP_SIG_A        0x8009B338u   /* == 0x08 on the shopkeeper menu   */
#define SHOP_SIG_B        0x8009B33Au   /* == 0xFF on the shopkeeper menu   */
#define SHOP_SIG_C        0x8009B344u   /* == 0x20 on the shopkeeper menu   */
#define SHOP_COUNT_ADDR   0x8009B345u   /* menu row count (gp+1085)         */
#define SHOP_CURSOR_ADDR  0x8009B34Du   /* menu cursor    (gp+1093)         */
#define SHOP_PAD_NEW_ADDR 0x8009B394u   /* new-press mask, byte-swapped     */
#define SHOP_CHIPS_ADDR   0x801D07E0u   /* starchips word                   */
#define SHOP_SAVE_LIVE    0x801D0200u
#define SHOP_SAVE_MIRROR  0x801D3200u
#define SHOP_TRUNK_OFF    0x50u
#define SHOP_CARD_MAX     722

/* Byte-swapped new-press bits (raw pad halfword swapped, see card_drops). */
#define SHOP_NP_UP      0x1000u
#define SHOP_NP_DOWN    0x4000u
#define SHOP_NP_CROSS   0x0040u
#define SHOP_NP_CIRCLE  0x0020u

#define SHOP_ROW_INDEX  4            /* our row on the shopkeeper menu */

/* ---- packs --------------------------------------------------------------- */
typedef struct { const char *name; int price; int cards; } ShopPack;
static const ShopPack k_packs[] = {
    /* Row text says "N CARDS" beside each, so the names stay short enough
     * for the panel's three columns. */
    { "POTLUCK",  20,  3 },
    { "BRONZE",   50,  5 },
    { "SILVER",  100,  7 },
    { "GOLD",    200, 10 },
};
#define SHOP_PACKS 4
#define SHOP_PULL_MAX 10
/* v1 pool: fully random low-end cards (user: "just choose some low level
 * cards, totally randomize for right now"). A card qualifies at ATK <= this;
 * magic/traps report 0 and qualify, which suits a starter pack fine. */
#define SHOP_MAX_ATK 1400

/* ---- state --------------------------------------------------------------- */
static int      s_enabled = 1;       /* MODS > CARD SHOP row */
static int      s_row;               /* menu row handle */
static int      s_screen;            /* signature matched this frame */
static int      s_open;              /* pack panel is up */
static int      s_sel;               /* selected pack 0..3 */
static int      s_dirty = 1;
static uint32_t s_rng = 0x5EEDCA5Du;
static int      s_pull[SHOP_PULL_MAX];
static int      s_pull_n;
static char     s_msg[28];           /* status line under the packs */
/* Observability (card_shop debug command). */
static unsigned s_buys, s_denied, s_opens;

/* ---- tiny helpers -------------------------------------------------------- */
static uint32_t rng_next(void) {
    /* xorshift32, reseeded by frame entropy on every open so two visits do
     * not replay the same pulls. */
    s_rng ^= s_rng << 13; s_rng ^= s_rng >> 17; s_rng ^= s_rng << 5;
    return s_rng;
}

static int deck_resident(uint32_t base) {
    /* The save struct's own signature: 40 non-decreasing u16 ids in 1..722.
     * Same gate the save-writing CHEATS rows use (ISSUES #5). */
    int prev = 0;
    for (int i = 0; i < 40; i++) {
        const int id = (int)psx_mod_read_half(base + (uint32_t)i * 2u);
        if (id < 1 || id > SHOP_CARD_MAX || id < prev) return 0;
        prev = id;
    }
    return 1;
}
static int save_live(void) {
    return deck_resident(SHOP_SAVE_LIVE) && deck_resident(SHOP_SAVE_MIRROR);
}

static int screen_match(void) {
    if (psx_mod_read_half(SHOP_STATE_ADDR) != 0xE00Du) return 0;
    if (psx_mod_read_byte(SHOP_SIG_A) != 0x08u) return 0;
    if (psx_mod_read_byte(SHOP_SIG_B) != 0xFFu) return 0;
    if (psx_mod_read_byte(SHOP_SIG_C) != 0x20u) return 0;
    const uint8_t n = psx_mod_read_byte(SHOP_COUNT_ADDR);
    return n == 4u || n == 5u;
}

/* ---- canvas -------------------------------------------------------------- */
/* One buffer serves both looks; origin/size switch with the mode. */
#define ROW_W 132
#define ROW_H 18
#define ROW_X 12
#define ROW_Y 111
#define PANEL_W 200
#define PANEL_H 132
#define PANEL_X 60
#define PANEL_Y 44
#define CV_W PANEL_W
#define CV_H PANEL_H
static uint32_t s_px[CV_W * CV_H];
static int s_img_w, s_img_h;

#define C_PANEL   0xE60E1424u   /* deep blue-black, like the dialog boxes */
#define C_BAND    0xEE060606u   /* menu wedge black */
#define C_GOLD    0xFFE0B84Cu
#define C_GOLD_D  0xFF8A6E24u
#define C_WHITE   0xFFF0F0F0u
#define C_GREY    0xFFB0B4C0u
#define C_RED     0xFFE06858u

static void px_fill(int x0, int y0, int w, int h, uint32_t c) {
    if (x0 < 0) { w += x0; x0 = 0; }
    if (y0 < 0) { h += y0; y0 = 0; }
    for (int y = y0; y < y0 + h && y < CV_H; y++)
        for (int x = x0; x < x0 + w && x < CV_W; x++)
            s_px[y * CV_W + x] = c;
}

/* Glyphs at the font's native 8x12; value 0 clear, 1 outline, high = core —
 * ramp the core to the tint exactly like the fusion overlay does. */
static int put_glyph(int cell, int x0, int y0, uint32_t tint) {
    const PsxFusionFont *f = &psx_fusion_font;
    if (cell < 0) return 4;
    const uint8_t *g = f->px + (size_t)cell * (size_t)f->w * (size_t)f->h;
    int hi = 0;
    for (int y = 0; y < f->h; y++)
        for (int x = 0; x < f->w; x++) {
            const uint8_t v = g[y * f->w + x];
            if (!v) continue;
            if (x > hi) hi = x;
            const int px = x0 + x, py = y0 + y;
            if (px < 0 || py < 0 || px >= CV_W || py >= CV_H) continue;
            if (v == 1) { s_px[py * CV_W + px] = 0xFF101010u; continue; }
            const uint32_t k = v * 17u > 255u ? 255u : v * 17u;
            const uint32_t r = ((tint >> 16 & 0xFFu) * k) / 255u;
            const uint32_t gg = ((tint >> 8 & 0xFFu) * k) / 255u;
            const uint32_t b = ((tint & 0xFFu) * k) / 255u;
            s_px[py * CV_W + px] = 0xFF000000u | r << 16 | gg << 8 | b;
        }
    return hi + 1;
}
static int put_text(const char *s, int x, int y, uint32_t tint) {
    for (; *s; s++) {
        if (*s == ' ') { x += 4; continue; }
        const int w = put_glyph(psx_fusion_font_cell((unsigned char)*s), x, y, tint);
        x += (w > 2 ? w : 4) + 1;
    }
    return x;
}

static void draw_row(void) {
    /* Stride == CV_W always: the renderer reads the buffer row-major at the
     * width we report, so reporting ROW_W while writing at CV_W stride
     * sheared every row (measured as garbled text on first light-up). The
     * unused right margin stays transparent and costs nothing. */
    s_img_w = CV_W; s_img_h = ROW_H;
    memset(s_px, 0, sizeof s_px);
    const int sel = (int)psx_mod_read_byte(SHOP_CURSOR_ADDR) == SHOP_ROW_INDEX;
    /* Band with the wedge's slanted edges, tall enough to fully cover the
     * game's own bare row-4 highlight (it bleeds below the panel starting a
     * few lines above where the label wants to sit). */
    for (int y = 0; y < ROW_H; y++) {
        const int indent = 6 + y / 2;                  /* left slant */
        const int right  = ROW_W - 2 - y / 3;          /* slight right slant */
        for (int x = indent; x < right; x++)
            s_px[y * CV_W + x] = C_BAND;
    }
    if (sel)
        for (int y = 3; y < ROW_H - 2; y++) {
            /* Gold bar shaded like the game's: bright core, darker rim. */
            const uint32_t c = (y <= 4 || y >= ROW_H - 4) ? C_GOLD_D : C_GOLD;
            for (int x = 9 + y / 2; x < ROW_W - 5 - y / 3; x++)
                s_px[y * CV_W + x] = c;
        }
    put_text("CARD SHOP", 34, 3, C_WHITE);
}

static void draw_panel(void) {
    s_img_w = PANEL_W; s_img_h = PANEL_H;
    memset(s_px, 0, sizeof s_px);
    px_fill(0, 0, PANEL_W, PANEL_H, C_PANEL);
    px_fill(0, 0, PANEL_W, 1, C_GOLD_D);  px_fill(0, PANEL_H - 1, PANEL_W, 1, C_GOLD_D);
    px_fill(0, 0, 1, PANEL_H, C_GOLD_D);  px_fill(PANEL_W - 1, 0, 1, PANEL_H, C_GOLD_D);

    put_text("CARD SHOP", 8, 3, C_GOLD);
    char line[32];
    snprintf(line, sizeof line, "CHIPS %u",
             (unsigned)psx_mod_read_word(SHOP_CHIPS_ADDR));
    put_text(line, 128, 3, C_WHITE);
    px_fill(4, 16, PANEL_W - 8, 1, C_GOLD_D);

    for (int i = 0; i < SHOP_PACKS; i++) {
        const int y = 20 + i * 13;
        if (i == s_sel) px_fill(3, y - 1, PANEL_W - 6, 13, 0xFF283048u);
        put_text(i == s_sel ? ">" : " ", 6, y, C_GOLD);
        put_text(k_packs[i].name, 14, y, C_WHITE);
        snprintf(line, sizeof line, "%d CARDS", k_packs[i].cards);
        put_text(line, 92, y, C_GREY);
        snprintf(line, sizeof line, "%d", k_packs[i].price);
        put_text(line, 168, y, C_GOLD);
    }
    px_fill(4, 73, PANEL_W - 8, 1, C_GOLD_D);

    if (s_msg[0]) put_text(s_msg, 6, 76, s_pull_n ? C_GREY : C_RED);
    /* Last pull, one card per line, newest visit only. */
    for (int i = 0; i < s_pull_n && i < 3; i++) {
        const char *nm = psx_card_db_name(s_pull[i]);
        /* The panel fits ~21 glyphs; a clipped name reads as a bug where a
         * shortened one reads as a list. */
        snprintf(line, sizeof line, "%.21s", nm ? nm : "?");
        if (nm && strlen(nm) > 21) { line[20] = '.'; line[21] = 0; }
        put_text(line, 10, 89 + i * 12, C_WHITE);
    }
    if (s_pull_n > 3) {
        snprintf(line, sizeof line, "+%d MORE IN TRUNK", s_pull_n - 3);
        put_text(line, 10, 89 + 3 * 12, C_GREY);
    }
    if (!s_pull_n && !s_msg[0])
        put_text("X BUY   O CLOSE", 40, 96, C_GREY);
}

/* ---- purchase ------------------------------------------------------------ */
static void grant_card(int id) {
    const uint32_t off = SHOP_TRUNK_OFF + (uint32_t)(id - 1);
    const uint8_t cur = psx_mod_read_byte(SHOP_SAVE_LIVE + off);
    const uint8_t nxt = cur < 250u ? (uint8_t)(cur + 1u) : cur;
    psx_mod_write_byte(SHOP_SAVE_LIVE + off, nxt);
    psx_mod_write_byte(SHOP_SAVE_MIRROR + off, nxt);
}

static int pick_card(void) {
    /* Random low-end card: ATK <= cap (magic/traps report 0 and qualify).
     * The db always answers for 1..722, so the loop terminates fast. */
    for (int tries = 0; tries < 64; tries++) {
        const int id = (int)(rng_next() % SHOP_CARD_MAX) + 1;
        int atk = 0, def = 0, type = 0;
        if (!psx_card_db_stats(id, &atk, &def, &type)) continue;
        if (atk <= SHOP_MAX_ATK) return id;
    }
    return 1 + (int)(rng_next() % SHOP_CARD_MAX);
}

static void buy(int pack) {
    const ShopPack *p = &k_packs[pack];
    if (!save_live()) {
        snprintf(s_msg, sizeof s_msg, "NO SAVE LOADED");
        s_pull_n = 0; s_denied++; return;
    }
    const uint32_t chips = psx_mod_read_word(SHOP_CHIPS_ADDR);
    if (chips < (uint32_t)p->price) {
        snprintf(s_msg, sizeof s_msg, "NOT ENOUGH CHIPS");
        s_pull_n = 0; s_denied++; return;
    }
    psx_mod_write_word(SHOP_CHIPS_ADDR, chips - (uint32_t)p->price);
    s_pull_n = 0;
    for (int i = 0; i < p->cards && i < SHOP_PULL_MAX; i++) {
        const int id = pick_card();
        grant_card(id);
        s_pull[s_pull_n++] = id;
    }
    snprintf(s_msg, sizeof s_msg, "%s PACK:", p->name);
    s_buys++;
}

/* ---- per-frame driver ---------------------------------------------------- */
void psx_card_shop_tick(void) {
    const int match = s_enabled && screen_match();
    if (match != s_screen) { s_screen = match; s_dirty = 1; }
    if (!match) { if (s_open) { s_open = 0; s_dirty = 1; } return; }

    /* Keep the fifth row alive: the menu init rewrites the count to 4 every
     * time the screen re-enters, so this is a standing correction, not a
     * one-shot. */
    if (psx_mod_read_byte(SHOP_COUNT_ADDR) == 4u)
        psx_mod_write_byte(SHOP_COUNT_ADDR, 5u);

    const uint16_t np = psx_mod_read_half(SHOP_PAD_NEW_ADDR);
    const int on_row = (int)psx_mod_read_byte(SHOP_CURSOR_ADDR) == SHOP_ROW_INDEX;

    if (!s_open) {
        static int prev_row = -1;
        if (on_row != prev_row) { prev_row = on_row; s_dirty = 1; }
        if (on_row && (np & SHOP_NP_CROSS)) {
            s_open = 1; s_sel = 0; s_msg[0] = 0; s_pull_n = 0; s_opens++;
            s_rng ^= (uint32_t)psx_mod_read_word(0x8009B0C4u) * 2654435761u;
            s_dirty = 1;
        }
        return;
    }

    /* Panel open: the game's menu is still live underneath, so pin its
     * cursor to our (inert) row and EAT every press we act on — X on row 4
     * is a measured no-op, but D-pad would move the game's cursor and O
     * would leave the whole shop screen. Clearing the new-press mask is the
     * card_drops trick; if a race ever lets one through, the pinned cursor
     * limits the damage to a cursor blip. */
    psx_mod_write_byte(SHOP_CURSOR_ADDR, SHOP_ROW_INDEX);
    uint16_t eat = 0;
    if (np & SHOP_NP_UP)    { s_sel = (s_sel + SHOP_PACKS - 1) % SHOP_PACKS; eat |= SHOP_NP_UP; s_dirty = 1; }
    if (np & SHOP_NP_DOWN)  { s_sel = (s_sel + 1) % SHOP_PACKS;              eat |= SHOP_NP_DOWN; s_dirty = 1; }
    if (np & SHOP_NP_CROSS) { buy(s_sel); eat |= SHOP_NP_CROSS; s_dirty = 1; }
    if (np & SHOP_NP_CIRCLE){ s_open = 0; eat |= SHOP_NP_CIRCLE; s_dirty = 1; }
    if (eat)
        psx_mod_write_half(SHOP_PAD_NEW_ADDR, (uint16_t)(np & ~eat));
    /* Chips readout changes with duels/purchases elsewhere too. */
    static uint32_t last_chips;
    const uint32_t chips = psx_mod_read_word(SHOP_CHIPS_ADDR);
    if (chips != last_chips) { last_chips = chips; s_dirty = 1; }
}

/* ---- overlay contract ---------------------------------------------------- */
int psx_card_shop_image(const uint32_t **px, int *w, int *h) {
    if (!s_screen) return 0;
    if (s_open) draw_panel(); else draw_row();
    *px = s_px; *w = s_img_w; *h = s_img_h;
    return 1;
}
void psx_card_shop_origin(int *x, int *y) {
    if (s_open) { *x = PANEL_X; *y = PANEL_Y; }
    else        { *x = ROW_X;   *y = ROW_Y;   }
}
int psx_card_shop_needs_present(void) {
    const int d = s_dirty; s_dirty = 0; return d;
}

/* ---- menu + debug -------------------------------------------------------- */
static void shop_changed(int v) { s_enabled = v ? 1 : 0; s_dirty = 1; }

void psx_card_shop_register_menu(void) {
    static const char *const ONOFF[] = { "OFF", "ON" };
    static const char *const HINTS[] = {
        "A CARD SHOP ROW ON THE SHOPKEEPER MENU",
        "BUY PACKS WITH STARCHIPS AT THE SHOPKEEPER",
    };
    s_row = psx_video_menu_add_option(
        PSX_VM_MENU_MODS, "CARD SHOP", HINTS[0],
        ONOFF, 2, "card_shop", 1, shop_changed);
    psx_video_menu_set_row_hints(s_row, HINTS);
}

int psx_card_shop_state_json(char *out, unsigned cap) {
    return snprintf(out, cap,
        "\"enabled\":%d,\"screen\":%d,\"open\":%d,\"sel\":%d,"
        "\"count_byte\":%u,\"cursor\":%u,\"chips\":%u,"
        "\"buys\":%u,\"denied\":%u,\"opens\":%u,\"last_pull\":%d",
        s_enabled, s_screen, s_open, s_sel,
        (unsigned)psx_mod_read_byte(SHOP_COUNT_ADDR),
        (unsigned)psx_mod_read_byte(SHOP_CURSOR_ADDR),
        (unsigned)psx_mod_read_word(SHOP_CHIPS_ADDR),
        s_buys, s_denied, s_opens, s_pull_n ? s_pull[0] : 0);
}
