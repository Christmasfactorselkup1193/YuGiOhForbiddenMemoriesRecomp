#ifndef PSX_CD_OVERLAY_H
#define PSX_CD_OVERLAY_H

/* "New!" tags for the CARD DROPS results page.
 *
 * The page's rows are drawn by the game's own text engine, but the yellow
 * New! label is a sprite the engine cannot emit, so it is composited by the
 * host exactly like the rank meter: a small ARGB canvas authored in GUEST
 * pixels (the 320x240 space), mapped into the letterboxed game rect by the
 * renderer. Pure state + rasterisation; no guest memory, no GL.
 */

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PSX_CD_OVERLAY_ROWS 7

/* Which of the page's rows carry the tag this frame. visible = 0 hides the
 * whole overlay (also the off-screen / stock-page state). Cheap to call every
 * frame: the canvas re-rasterises only on change. */
void psx_cd_overlay_set(int visible, const uint8_t new_rows[PSX_CD_OVERLAY_ROWS]);

/* 1 + fills the ARGB canvas when something should be drawn. Guest pixels. */
int  psx_cd_overlay_image(const uint32_t **pixels, int *w, int *h);

/* Top-left corner in guest pixels. */
void psx_cd_overlay_origin(int *x, int *y);

/* 1 while the overlay has content on screen, so a present can be forced. */
int  psx_cd_overlay_needs_present(void);

/* Live layout tuning over the debug server, same rationale as the rank
 * meter's: pixel placement against the game's art is a by-eye job. ABSOLUTE
 * values; pass PSX_CD_OVERLAY_KEEP to leave a field alone. */
#define PSX_CD_OVERLAY_KEEP (-100000)
void psx_cd_overlay_tune(int x, int y, int tag_dy);
void psx_cd_overlay_tune_get(int *x, int *y, int *tag_dy);

#ifdef __cplusplus
}
#endif

#endif /* PSX_CD_OVERLAY_H */
