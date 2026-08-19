/* psx_cd_overlay.c — "New!" tags for the CARD DROPS results page.
 *
 * See psx_cd_overlay.h. Row geometry mirrors the page's text layout, which
 * the composer in main.cpp owns: text rows start at guest y=40 with a 24px
 * pitch (the Special Arts plate pitch), the card number column at x=12, and
 * the tag sits under the 8x12 number digits. */

#include "psx_cd_overlay.h"
#include "psx_cd_sprites.h"

#include <string.h>

/* Layout, guest pixels. The tag rides the UPPER strip of each plate, above
 * the row's text line. Tunable live (psx_cd_overlay_tune) because placing
 * pixel art against the game's own art is a by-eye job and a rebuild per
 * nudge costs the player their results screen. Defaults carry the user's
 * measured corrections from the first widescreen fitting. */
#define CDO_X       4    /* left edge, aligned with the number column */
#define CDO_Y       38   /* first plate's top strip */
#define CDO_PITCH   24   /* plate row pitch */
#define CDO_TAG_DY  12   /* tag top within the row */

static int s_x      = CDO_X;
static int s_y      = CDO_Y;
static int s_tag_dy = CDO_TAG_DY;

#define CDO_W       24   /* newtag width */
/* Canvas height covers the LARGEST tunable tag offset, not the default one:
 * sized to CDO_TAG_DY, raising the offset pushed the last row's tag past the
 * bottom edge and blit() silently clipped it away (one missing "New!"). The
 * slack is transparent, so it costs nothing to draw. */
#define CDO_MAX_DY  64
#define CDO_H       (CDO_PITCH * (PSX_CD_OVERLAY_ROWS - 1) + CDO_MAX_DY + 8)

static uint32_t s_canvas[CDO_W * CDO_H];
static uint8_t  s_rows[PSX_CD_OVERLAY_ROWS];
static int      s_visible;
static int      s_dirty = 1;
static int      s_have_content;

static void blit(const PsxSprite *s, int x, int y) {
    if (!s || !s->px) return;
    for (int row = 0; row < s->h; row++) {
        const int dy = y + row;
        if (dy < 0 || dy >= CDO_H) continue;
        for (int col = 0; col < s->w; col++) {
            const int dx = x + col;
            if (dx < 0 || dx >= CDO_W) continue;
            const uint32_t p = s->px[row * s->w + col];
            if (p >> 24) s_canvas[dy * CDO_W + dx] = p;
        }
    }
}

static void redraw(void) {
    memset(s_canvas, 0, sizeof s_canvas);
    s_have_content = 0;
    for (int r = 0; r < PSX_CD_OVERLAY_ROWS; r++) {
        if (!s_rows[r]) continue;
        blit(&psx_spr_newtag, 0, r * CDO_PITCH + s_tag_dy);
        s_have_content = 1;
    }
    s_dirty = 0;
}

void psx_cd_overlay_tune(int x, int y, int tag_dy) {
    if (x != PSX_CD_OVERLAY_KEEP && x != s_x) s_x = x;
    if (y != PSX_CD_OVERLAY_KEEP && y != s_y) s_y = y;
    if (tag_dy != PSX_CD_OVERLAY_KEEP) {
        if (tag_dy < 0) tag_dy = 0;
        if (tag_dy > CDO_MAX_DY) tag_dy = CDO_MAX_DY;
        if (tag_dy != s_tag_dy) { s_tag_dy = tag_dy; s_dirty = 1; }
    }
}

void psx_cd_overlay_tune_get(int *x, int *y, int *tag_dy) {
    if (x) *x = s_x;
    if (y) *y = s_y;
    if (tag_dy) *tag_dy = s_tag_dy;
}

void psx_cd_overlay_set(int visible, const uint8_t new_rows[PSX_CD_OVERLAY_ROWS]) {
    const uint8_t *rows = new_rows;
    static const uint8_t none[PSX_CD_OVERLAY_ROWS];
    if (!visible || !rows) rows = none;
    if (memcmp(s_rows, rows, sizeof s_rows) != 0) {
        memcpy(s_rows, rows, sizeof s_rows);
        s_dirty = 1;
    }
    s_visible = visible ? 1 : 0;
}

int psx_cd_overlay_image(const uint32_t **pixels, int *w, int *h) {
    if (!s_visible) return 0;
    if (s_dirty) redraw();
    if (!s_have_content) return 0;
    if (pixels) *pixels = s_canvas;
    if (w) *w = CDO_W;
    if (h) *h = CDO_H;
    return 1;
}

void psx_cd_overlay_origin(int *x, int *y) {
    if (x) *x = s_x;
    if (y) *y = s_y;
}

int psx_cd_overlay_needs_present(void) {
    if (!s_visible) return 0;
    if (s_dirty) redraw();
    return s_have_content;
}
