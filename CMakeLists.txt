cmake_minimum_required(VERSION 3.20)
project(YuGiOhForbiddenMemoriesRecomp LANGUAGES C CXX)

set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")

# --- Opt-in product surfaces (OFF by default in the framework) -------------
# Scaffold prompts / flags fill these. Without recomp-ui, PSX_RECOMP_UI is OFF.
# Setup-host CI requires WIZARD_CMAKE_BLOCK / ENABLE_SETUP_WIZARD (FORCE_SETUP_HOST
# alone does not open first-run / Generate & rebuild).
set(PSX_RECOMP_UI OFF CACHE BOOL
    "No recomp-ui submodule in this scaffold" FORCE)
# Full netplay UI -- enable after adding recomp-ui + testing:
# if(EXISTS "${PSXRECOMP_ROOT}/lib/recomp-net/CMakeLists.txt")
#     set(PSX_NETPLAY ON CACHE BOOL "..." FORCE)
# endif()
# First-run setup wizard -- enable after testing:
# set(PSX_SETUP_WIZARD ON CACHE BOOL "..." FORCE)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

# Everything specific to Yu-Gi-Oh! Forbidden Memories lives here, not in the
# framework: the fusion assistant, the duel-rank meter, card drops and the
# cheats. They register themselves at static-init time through mod_plugins.h
# constructors, the overlay menu's row API and psx_game_hooks, so the runtime
# never names them and no other title compiles them.
file(GLOB YGOFM_GAME_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.c")

# --- Konami artwork is BUILD OUTPUT, not source ----------------------------
# Three sources are the game's own art -- the duel-rank badges and letters, the
# CARD DROPS "New!" label, and the game's text font. They are derived from the
# disc exactly the way generated/ is derived from the EXE, so like generated/
# they are gitignored and rebuilt from the PLAYER'S disc. Nothing Konami-derived
# is committed or shipped.
#
# The disc is found the same way the runtime finds it, so the ordinary dev loop
# needs no new flag: an explicit -DYGOFM_DISC wins, otherwise the disc this
# build directory already verified is reused. With neither, configure FAILS --
# a build that quietly produced a runtime with no art would look like a broken
# feature rather than a missing input.
if(NOT YGOFM_DISC AND EXISTS "${CMAKE_BINARY_DIR}/disc_verified.cfg")
    file(STRINGS "${CMAKE_BINARY_DIR}/disc_verified.cfg" _YGOFM_DISC_CFG
         REGEX "^path=")
    if(_YGOFM_DISC_CFG)
        string(REGEX REPLACE "^path=" "" YGOFM_DISC "${_YGOFM_DISC_CFG}")
    endif()
endif()
if(NOT YGOFM_DISC OR NOT EXISTS "${YGOFM_DISC}")
    message(FATAL_ERROR
        "No disc image. The rank sprites, the New! label and the game font are "
        "baked from your own copy of the disc and are not distributed.\n"
        "Pass -DYGOFM_DISC=<path to the .bin>, or run the setup host, which "
        "asks for it once and remembers it.")
endif()
message(STATUS "ygofm: baking sprites/font from ${YGOFM_DISC}")

find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(YGOFM_ART_DIR "${CMAKE_BINARY_DIR}/game-assets")
set(YGOFM_ART_SOURCES
    "${YGOFM_ART_DIR}/psx_rank_sprites.c"
    "${YGOFM_ART_DIR}/psx_cd_sprites.c"
    "${YGOFM_ART_DIR}/psx_fusion_font.c")
add_custom_command(
    OUTPUT ${YGOFM_ART_SOURCES}
    COMMAND ${Python3_EXECUTABLE}
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/disc_assets.py"
            "${YGOFM_DISC}" "${YGOFM_ART_DIR}"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/tools/disc_assets.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/sprite_extract.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/font_extract.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/sprite_spec.json"
    COMMENT "Baking sprites and font from the disc"
    VERBATIM)
list(APPEND YGOFM_GAME_SOURCES ${YGOFM_ART_SOURCES})

psxrecomp_add_game_runtime(psx-runtime
    # ENABLE_NETPLAY_IF_PRESENT
    # NETPLAY_LOBBY_URL ws://netplay.retcomm.net:8765
    # ENABLE_SETUP_WIZARD
    WINDOW_TITLE "Yu-Gi-Oh Forbidden Memories Recompiled"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 2
    # LAUNCHER_BOXART "${CMAKE_CURRENT_SOURCE_DIR}/launcher_assets/img/boxart.tga"
    APP_ICON "${CMAKE_CURRENT_SOURCE_DIR}/assets/psxrecomp.ico"
    GEN_MARKER "generated/SLUS_014.11_dispatch.c"
    GEN_FULL_GLOB "generated/SLUS_014.11_full_*.c"
    CODEGEN_SETUP_SOURCES ${YGOFM_GAME_SOURCES}
)

# The game's own headers sit beside its sources.
target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")

# Stage runtime configs next to the exe for direct build/ launches. Only copy
# files that exist — never fail when game_options.toml is absent.
#
# This is its own always-run target rather than a POST_BUILD on psx-runtime,
# because POST_BUILD only fires when the exe RELINKS. Editing only game.toml
# left the staged copy stale, so the runtime kept reading the previous config
# while the build reported success — a config change that silently does nothing
# reads exactly like a feature that does nothing. copy_if_different makes the
# unconditional run free when nothing changed.
add_custom_target(psx-stage-configs ALL)
add_dependencies(psx-runtime psx-stage-configs)
foreach(_PSX_RUNTIME_CONFIG game.toml game_options.toml)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}")
        add_custom_command(TARGET psx-stage-configs POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}"
                "$<TARGET_FILE_DIR:psx-runtime>/${_PSX_RUNTIME_CONFIG}"
            COMMENT "Staging ${_PSX_RUNTIME_CONFIG}"
            VERBATIM)
    endif()
endforeach()

