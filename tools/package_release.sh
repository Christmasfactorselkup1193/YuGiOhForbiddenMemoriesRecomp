#!/usr/bin/env bash
# package_release.sh — build this title's setup-host zip.
#
# The framework packager is generic and its defaults assume the older layout,
# where codegen_setup.c sat at the repo root and there was no src/ or tools/.
# Getting the argument list wrong does not fail the build: it produces a zip
# that unpacks, generates, and then fails partway through the player's build --
# or worse, builds a game that quietly lacks a feature. Both happened while
# this was being worked out, which is why the invocation lives here instead of
# in someone's shell history.
#
#   tools/package_release.sh [--build-dir DIR] [--artifact NAME]
#
# The build dir must hold a SETUP HOST build (configured with
# -DPSXRECOMP_FORCE_SETUP_HOST=ON), not the game.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="build-setup"
ARTIFACT="win-x64"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-dir) BUILD_DIR="${2:?}"; shift 2 ;;
    --artifact)  ARTIFACT="${2:?}";  shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

cd "${ROOT}"

# Every path the PLAYER'S build needs, and nothing derived from the disc.
#
#   src/        the title's features + codegen_setup.c. The three baked art
#               sources are absent by design -- disc_assets.py remakes them.
#   tools/      disc_assets.py and the two decoders it drives, plus
#               sprite_spec.json. Without these the product build cannot bake
#               the art and will not configure.
#   seeds/      function seeds the recompiler reads during generate.
#   assets/     the app icon named by CMakeLists. A missing icon does not fail
#               the build, so leaving it out ships a game with the wrong icon
#               and no error anywhere -- caught only by looking.
#   game_options.toml
#               NOT optional in practice: without it the product build loses
#               "menu fast loading = instant", i.e. the accelerated loads, with
#               nothing in the log to say why. Caught by diffing a cold
#               install's boot log against a dev build's.
exec bash psxrecomp/tools/package_setup_host.sh \
  --build-dir "${BUILD_DIR}" \
  --artifact "${ARTIFACT}" \
  --zip-prefix ygofm \
  --exe-name Yu_Gi_Oh_Forbidden_Memories_Recompiled \
  --display-name "Yu-Gi-Oh! Forbidden Memories Recompiled" \
  --disc-hint "your own Yu-Gi-Oh! Forbidden Memories (USA) disc" \
  --project-file CMakeLists.txt \
  --project-file game.toml \
  --project-file game_options.toml \
  --project-file VERSION \
  --project-file README.md \
  --project-file LICENSE \
  --project-file NOTICE \
  --project-dir src \
  --project-dir tools \
  --project-dir seeds \
  --project-dir assets
