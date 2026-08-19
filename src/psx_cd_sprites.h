#ifndef PSX_CD_SPRITES_H
#define PSX_CD_SPRITES_H

/* Sprites baked for the CARD DROPS results page. Same scheme as
 * psx_rank_sprites.h: lifted from the game's own VRAM once, ARGB8888 with
 * alpha 0 for the PS1 transparent palette entry, so they composite straight
 * over the frame. */

#include "psx_rank_sprites.h"   /* PsxSprite */

#ifdef __cplusplus
extern "C" {
#endif

/* The deck builder's yellow "New!" label, 24x8. */
extern const PsxSprite psx_spr_newtag;

#ifdef __cplusplus
}
#endif

#endif /* PSX_CD_SPRITES_H */
