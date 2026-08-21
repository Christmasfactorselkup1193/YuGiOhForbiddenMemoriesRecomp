/* psx_duelist_icons.h — the FREE DUEL portraits, indexed by duelist.
 *
 * The Drop Table Viewer draws these beside each duelist's name. They are the
 * game's own icons, so like every other piece of Konami art in this project
 * they are BUILD OUTPUT: psx_duelist_icons.c is generated and neither
 * committed nor shipped, and a build without them still links — every entry is
 * simply absent and the viewer draws a plain plate.
 *
 * Indexed by the same duelist number PSX_DROP_DB uses, so a caller that has one
 * has the other. Not every index has an icon: the free-duel list does not
 * include the story-only opponents, and it does not include anyone the player
 * has yet to beat.
 */
#ifndef PSX_DUELIST_ICONS_H
#define PSX_DUELIST_ICONS_H

#include <stdint.h>

#define PSX_DUELIST_ICON_N    39
#define PSX_DUELIST_ICON_W    38
#define PSX_DUELIST_ICON_H    38

/* NULL where no icon was captured. Pixels are 0xAARRGGBB, row-major. */
extern const uint32_t *const PSX_DUELIST_ICONS[PSX_DUELIST_ICON_N];

#endif /* PSX_DUELIST_ICONS_H */
