/* psx_ygo_overlays.h — this title's guest-space overlays.
 *
 * Registration lives in one file because REGISTRATION ORDER IS DRAW ORDER, and
 * static-initialisation order across translation units is unspecified: letting
 * each overlay register from its own module would leave the back-to-front order
 * up to the linker.
 */
#ifndef PSX_YGO_OVERLAYS_H
#define PSX_YGO_OVERLAYS_H

#ifdef __cplusplus
extern "C" {
#endif

/* The letterbox mapping the rank meter was last drawn with — ten ints:
 * box[4], native[2], dest[4]. All zero before the meter has ever been drawn.
 * Reported by the rank_meter_state debug command, which is how alignment
 * against the game's own art is checked exactly rather than by eye. */
void psx_ygo_rank_placement(int *o);

#ifdef __cplusplus
}
#endif

#endif /* PSX_YGO_OVERLAYS_H */
