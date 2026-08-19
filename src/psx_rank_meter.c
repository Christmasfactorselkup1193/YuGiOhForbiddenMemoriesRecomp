/* Live duel-rank meter — see psx_rank_meter.h.
 *
 * Composites the game's own DUEL SKILL badge, rank letter and card-stat digits
 * into a small ARGB canvas authored in GUEST pixels, so the renderer can drop
 * it into the letterboxed game rect beside the FIELD box at any window size.
 */

#include "psx_rank_meter.h"
#include "psx_rank_sprites.h"

#include <string.h>

/* Canvas is a fixed upper bound rather than a fit-to-content allocation: the
 * meter's widest form is badge + letter + two digits, and a static buffer keeps
 * this module allocation-free like the rest of the overlay code. */
#define RM_MAX_W 96
#define RM_MAX_H 32

/* Fallback origin, used until the host anchors the meter to the live FIELD box.
 * The box is five sprites spanning x 12..68, y 24..48 (measured off the GP0
 * stream), so this clears it to the right. */
#define RM_ORIGIN_X 74
#define RM_ORIGIN_Y (24 - RM_LETTER_Y)

/* The POW/TEC badge is half size and sits BEHIND the letter at the upper left,
 * reading as a tag ON the rank rather than a second icon beside it. These are
 * the letter's offsets within the canvas; the badge is always at (0,0). Kept
 * small so the badge and letter overlap hard and the whole widget stays
 * compact next to the FIELD box. */
#define RM_LETTER_X 2
#define RM_LETTER_Y 3

/* px between the letter and the number. NEGATIVE is legal and normal: the rank
 * letter is an area-downscale of a 40x40 glyph and carries padding inside its
 * 24x24 cell, so the number has to tuck back into that cell to sit against the
 * letter rather than floating away from it. */
#define RM_GAP (-1)

/* Live-tunable copies. Placing pixel art next to the game's own art is a
 * by-eye job, and rebuilding the runtime to move something two pixels costs
 * the player their duel — so the debug server can nudge these while the game
 * runs (`rank_meter_tune`). The #defines above stay the shipped defaults. */
static int s_letter_x = RM_LETTER_X;
static int s_letter_y = RM_LETTER_Y;
static int s_gap      = RM_GAP;
/* Nudge applied to the anchor the host reports, so the widget can be shifted
 * relative to the FIELD box without rebuilding. */
static int s_anchor_dx, s_anchor_dy;
/* Vertical refinement in HALF guest pixels, applied by the renderer rather than
 * here: the canvas is authored in whole guest pixels, but the picture is
 * magnified by an integer factor, so half a guest pixel is a real and
 * addressable distance on screen (2-3 device pixels at typical scales). */
static int s_anchor_dy2;

static uint32_t s_canvas[RM_MAX_W * RM_MAX_H];
static int s_w, s_h;
static int s_visible;
static int s_score = -1, s_pow = -1, s_letter = -1, s_show_score = -1;
static int s_dirty = 1;
static int s_ready;
/* Set when the meter goes from shown to hidden: one more present is needed to
 * paint it out, or the last frame drawn with it stays on screen. */
static int s_hide_pending;
/* 0..255 fade, followed from the game's own HUD brightness. */
static int s_fade = 255;

static void blit(const PsxSprite *s, int x, int y) {
    if (!s || !s->px || s->w <= 0 || s->h <= 0) return;
    for (int row = 0; row < s->h; row++) {
        int dy = y + row;
        if (dy < 0 || dy >= s_h) continue;
        for (int col = 0; col < s->w; col++) {
            int dx = x + col;
            if (dx < 0 || dx >= s_w) continue;
            uint32_t p = s->px[row * s->w + col];
            uint32_t a = p >> 24;
            if (!a) continue;
            if (s_fade < 255) {
                a = a * (uint32_t)s_fade / 255u;
                if (!a) continue;
                p = (a << 24) | (p & 0x00FFFFFFu);
            }
            if (a == 0xFF) {
                s_canvas[dy * s_w + dx] = p;
            } else {
                /* Every sprite currently baked is 1-bit alpha, matching the
                 * PS1's own art, so this path does not run today. It is kept
                 * because it is the correct thing to do if a future sprite ever
                 * carries partial coverage — the downscaled letters DID until
                 * alpha_cut was added, and their soft edges read as a grey haze
                 * against the duel's black background. */
                uint32_t d = s_canvas[dy * s_w + dx];
                uint32_t da = d >> 24;
                uint32_t oa = a + da * (255 - a) / 255;
                if (!oa) { s_canvas[dy * s_w + dx] = 0; continue; }
                uint32_t out = oa << 24;
                for (int sh = 16; sh >= 0; sh -= 8) {
                    uint32_t sc = (p >> sh) & 0xFF, dc = (d >> sh) & 0xFF;
                    uint32_t c = (sc * a + dc * da * (255 - a) / 255) / oa;
                    out |= (c > 255 ? 255 : c) << sh;
                }
                s_canvas[dy * s_w + dx] = out;
            }
        }
    }
}

static int sprite_h(const PsxSprite *s) { return (s && s->px) ? s->h : 0; }
static int sprite_w(const PsxSprite *s) { return (s && s->px) ? s->w : 0; }

static void redraw(void) {
    const PsxSprite *badge = s_pow ? &psx_spr_pow : &psx_spr_tec;
    const PsxSprite *letter = (s_letter >= 0 && s_letter <= 4)
                                  ? &psx_spr_rank[s_letter] : NULL;
    const int d1 = (s_score / 10) % 10;
    const int d0 = s_score % 10;
    const PsxSprite *dig1 = &psx_spr_digit[d1];
    const PsxSprite *dig0 = &psx_spr_digit[d0];

    const int lx = sprite_w(letter) ? s_letter_x : 0;
    const int ly = sprite_h(letter) ? s_letter_y : 0;
    const int digits_x = lx + sprite_w(letter) + s_gap;

    int w = s_show_score ? digits_x + sprite_w(dig1) + sprite_w(dig0)
                         : lx + sprite_w(letter);
    if (sprite_w(badge) > w) w = sprite_w(badge);
    if (sprite_w(&psx_spr_plate) > w) w = sprite_w(&psx_spr_plate);

    int h = ly + sprite_h(letter);
    if (sprite_h(badge) > h) h = sprite_h(badge);
    if (sprite_h(&psx_spr_plate) > h) h = sprite_h(&psx_spr_plate);

    if (w > RM_MAX_W) w = RM_MAX_W;
    if (h > RM_MAX_H) h = RM_MAX_H;
    if (w < 1 || h < 1) { s_ready = 0; s_dirty = 0; return; }

    s_w = w;
    s_h = h;
    memset(s_canvas, 0, (size_t)s_w * s_h * sizeof(s_canvas[0]));

    /* Plate, then badge, then letter. The results screen draws the rank letter
     * on this stone plate and the art's anti-aliased edges were authored
     * against it — on a bare background those soft edges read as a grey haze.
     * Restoring the plate is what makes the sprites look right; thresholding
     * their alpha only hid the symptom. */
    blit(&psx_spr_plate, 0, 0);
    blit(badge, 0, 0);
    blit(letter, lx, ly);

    /* Digits centred on the letter, not on the canvas: the badge makes the
     * canvas taller at the top, and centring on that would sit the number
     * visibly high of the rank it belongs to. */
    if (s_show_score) {
        const int dy = ly + (sprite_h(letter) - sprite_h(dig1)) / 2;
        blit(dig1, digits_x, dy);
        blit(dig0, digits_x + sprite_w(dig1), dy);
    }

    s_ready = 1;
    s_dirty = 0;
}

void psx_rank_meter_set(int visible, int score, int pow, int letter,
                        int show_score) {
    if (score < 0) score = 0;
    if (score > 99) score = 99;
    show_score = show_score ? 1 : 0;
    if (visible == s_visible && score == s_score && pow == s_pow &&
        letter == s_letter && show_score == s_show_score)
        return;
    s_show_score = show_score;
    if (s_visible && !visible) s_hide_pending = 1;
    s_visible = visible;
    s_score = score;
    s_pow = pow;
    s_letter = letter;
    s_dirty = 1;
}

int psx_rank_meter_image(const uint32_t **pixels, int *w, int *h) {
    if (!s_visible) {
        s_hide_pending = 0;   /* this present is the one that paints it out */
        if (pixels) *pixels = 0;
        if (w) *w = 0;
        if (h) *h = 0;
        return 0;
    }
    if (s_dirty) redraw();
    if (!s_ready) return 0;
    if (pixels) *pixels = s_canvas;
    if (w) *w = s_w;
    if (h) *h = s_h;
    return 1;
}

static int s_org_x = RM_ORIGIN_X, s_org_y = RM_ORIGIN_Y;

void psx_rank_meter_origin(int *x, int *y) {
    if (x) *x = s_org_x;
    if (y) *y = s_org_y;
}

void psx_rank_meter_set_fade(int fade) {
    if (fade < 0) fade = 0;
    if (fade > 255) fade = 255;
    /* Only a visible step matters: re-rasterising on every 1/255 tick would
     * redraw the canvas every frame of a fade for no visible gain. */
    if (fade == s_fade || (fade < 255 && s_fade < 255 &&
                           (fade > s_fade ? fade - s_fade : s_fade - fade) < 6))
        return;
    s_fade = fade;
    s_dirty = 1;
}

void psx_rank_meter_set_origin(int letter_x, int letter_y) {
    /* Caller gives where the LETTER should land; the canvas starts above and
     * left of that so the half-size badge can overhang it. */
    s_org_x = letter_x - s_letter_x + s_anchor_dx;
    s_org_y = letter_y - s_letter_y + s_anchor_dy;
}

void psx_rank_meter_letter_offset(int *x, int *y) {
    if (x) *x = s_letter_x;
    if (y) *y = s_letter_y;
}

int psx_rank_meter_subpixel_y(void) { return s_anchor_dy2; }

void psx_rank_meter_tune_sub(int dy2) { s_anchor_dy2 = dy2; }

void psx_rank_meter_tune(int letter_x, int letter_y, int gap,
                         int anchor_dx, int anchor_dy) {
    /* KEEP rather than a negative sentinel: `gap` is legitimately negative
     * (the number tucks into the letter's padding), so "-1 means leave alone"
     * silently ignored the exact value most worth setting. */
    if (letter_x != PSX_RANK_TUNE_KEEP) s_letter_x = letter_x;
    if (letter_y != PSX_RANK_TUNE_KEEP) s_letter_y = letter_y;
    if (gap      != PSX_RANK_TUNE_KEEP) s_gap      = gap;
    if (anchor_dx != PSX_RANK_TUNE_KEEP) s_anchor_dx = anchor_dx;
    if (anchor_dy != PSX_RANK_TUNE_KEEP) s_anchor_dy = anchor_dy;
    s_dirty = 1;
}

void psx_rank_meter_tune_get(int *letter_x, int *letter_y, int *gap,
                             int *anchor_dx, int *anchor_dy) {
    if (letter_x)  *letter_x  = s_letter_x;
    if (letter_y)  *letter_y  = s_letter_y;
    if (gap)       *gap       = s_gap;
    if (anchor_dx) *anchor_dx = s_anchor_dx;
    if (anchor_dy) *anchor_dy = s_anchor_dy;
}

void psx_rank_meter_extent(int *x, int *y, int *w, int *h) {
    if (s_dirty) redraw();
    if (x) *x = s_org_x;
    if (y) *y = s_org_y;
    if (w) *w = s_ready ? s_w : 0;
    if (h) *h = s_ready ? s_h : 0;
}

/* Deliberately NOT "1 whenever visible": the renderer skips a swap when the
 * game's frame is unchanged, and FM's duel field sits still whenever it is
 * waiting for input. Claiming a present every frame would disable that skip for
 * the whole duel. Only an actual change to what the meter shows — or its
 * removal — has to force one; once drawn, a skipped present simply leaves the
 * correct image on screen. */
int psx_rank_meter_needs_present(void) {
    return (s_dirty && s_visible) || s_hide_pending;
}
