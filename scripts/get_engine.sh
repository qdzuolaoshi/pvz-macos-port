#!/bin/zsh
# Fetch upstream PvZ-Portable at the commit the macOS patch was made against and apply the patch.
# usage: scripts/get_engine.sh [target_dir]      (default <repo>/PvZ-Portable)
set -euo pipefail
ROOT="${0:A:h:h}"
DST="${1:-$ROOT/PvZ-Portable}"
BASE=1e1742e
[[ -d "$DST/.git" ]] || git clone https://github.com/wszqkzqk/PvZ-Portable.git "$DST"
git -C "$DST" checkout -B pvz-macos "$BASE"
git -C "$DST" apply --index "$ROOT/patches/pvz-portable-macos.patch"
echo "Patched engine ready in $DST (branch pvz-macos, changes staged)."
