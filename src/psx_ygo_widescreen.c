#include "mod_plugins.h"

static void ygo_widescreen_activate(void) {
    (void)psx_mod_set_fixed_display_aspect(16u, 9u);
}

PSX_MOD_CONSTRUCTOR(psx_register_ygo_widescreen_plugin) {
    (void)psx_mod_register_activation_plugin(
        "psx.widescreen", ygo_widescreen_activate);
}
