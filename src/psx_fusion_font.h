#ifndef PSX_FUSION_FONT_H
#define PSX_FUSION_FONT_H

/* The game's own text font, baked from VRAM by tools/font_extract.py.
 *
 * This is the font the duel's card-name bar prints with: 8 wide, 12 tall, one
 * byte per pixel holding the source 4-bit value. 0 is transparent, 1 is the
 * dark outline the game draws around every glyph, and the high values are the
 * white core — so ramping the value to grey reproduces the game's own
 * anti-aliased text exactly, with no CLUT to track.
 *
 * Baked rather than read live for the same reason the rank meter's sprites
 * are: a host overlay that reads VRAM at draw time has to know which page and
 * palette the guest happens to have loaded this frame, and gets nothing for it.
 */

#include <stdint.h>

#include "psx_rank_sprites.h"   /* PsxSprite */

#ifdef __cplusplus
extern "C" {
#endif

typedef struct PsxFusionFont {
    const uint8_t *px;   /* cells * w * h, row-major within each cell */
    int w, h;
} PsxFusionFont;

extern const PsxFusionFont psx_fusion_font;

/* The stat icons the game prints beside a card's attack and defence, from
 * the same sheet as the small digits. Real two-tone art, so ARGB. */
extern const PsxSprite psx_fusion_icon_atk;
extern const PsxSprite psx_fusion_icon_def;

#define PSX_FUSION_FONT_CELLS 96

/* ASCII -> cell, or -1 for anything the atlas has no glyph for (space
 * included: it is an advance, not a cell). The atlas runs 0x21..0x5A in cells
 * 0..57, then six non-ASCII symbols, then resumes at 0x60 in cell 64 — which
 * is why the two halves need different offsets. */
static inline int psx_fusion_font_cell(unsigned char c)
{
    if (c >= 0x21u && c <= 0x5Au) return (int)c - 0x21;
    if (c >= 0x60u && c <= 0x7Fu) return (int)c - 0x20;
    return -1;
}

#ifdef __cplusplus
}
#endif

#endif /* PSX_FUSION_FONT_H */
