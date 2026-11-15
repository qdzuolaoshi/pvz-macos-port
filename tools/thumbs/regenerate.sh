#!/bin/zsh
# Regenerate the HD cover sheets used from overrides/images/ (see README.md in this folder).
#
# usage: regenerate.sh <workdir> <waifu2x-ncnn-vulkan dir>
#        UPSCALED=<dir> regenerate.sh <workdir>
#   <waifu2x-ncnn-vulkan dir>  the extracted waifu2x-ncnn-vulkan-20250915-macos release (binary + models-cunet)
#   UPSCALED                   skip the upscaler and use ch_NN.png / sv_NN.png cells it produced earlier
# Output: <workdir>/out/{Challenge,Survival}_Thumbnails_{2,3,4}x.png and their sha256.
set -euo pipefail
HERE="${0:A:h}"
ROOT="${HERE:h:h}"                    # repository root
W="${1:?usage: regenerate.sh <workdir> [waifu2x dir]}"
W2X="${2:-}"
CAND=cunet_n1_then_n-1_tta
mkdir -p "$W/orig" "$W/pad" "$W/up/$CAND"

# 1. The original sheets from the user's main.pak (images\Challenge_Thumbnails.jpg, images\Survival_Thumbnails.jpg).
python3 -I "$HERE/pak_list.py" "${PVZ_GAME_DIR:-$ROOT/game}/main.pak" _thumbnails "$W/pak"
cp "$W/pak/images__Challenge_Thumbnails.jpg" "$W/orig/Challenge_Thumbnails.jpg"
cp "$W/pak/images__Survival_Thumbnails.jpg" "$W/orig/Survival_Thumbnails.jpg"

# 2. 80x65 cells, edge-padded by 8 px (96x81), so the upscaler never sees a neighbouring cell.
python3 -I "$HERE/split_pad.py" "$W/orig/Challenge_Thumbnails.jpg" "$W/pad" ch 8
python3 -I "$HERE/split_pad.py" "$W/orig/Survival_Thumbnails.jpg" "$W/pad" sv 8

# 3. waifu2x cunet: 2x with noise level 1, then 2x scale-only (noise -1), both with TTA (-x). GPU (auto).
if [[ -n "${UPSCALED:-}" ]]; then
  cp "$UPSCALED"/ch_*.png "$UPSCALED"/sv_*.png "$W/up/$CAND/"
else
  [[ -x "$W2X/waifu2x-ncnn-vulkan" ]] || { echo "waifu2x-ncnn-vulkan not found in '$W2X'"; exit 1; }
  mkdir -p "$W/up/_p1_$CAND"
  "$W2X/waifu2x-ncnn-vulkan" -i "$W/pad" -o "$W/up/_p1_$CAND" -s 2 -n 1 -m "$W2X/models-cunet" -x
  "$W2X/waifu2x-ncnn-vulkan" -i "$W/up/_p1_$CAND" -o "$W/up/$CAND" -s 2 -n -1 -m "$W2X/models-cunet" -x
fi

# 4. Crop the 32-px (8 px x 4) padding and assemble the 4x sheets (also writes metrics/ and the bicubic and
#    Lanczos reference sheets used for the evaluation).
python3 -I "$HERE/assemble_eval.py" "$W"

# 5. Ship the 4x sheets unchanged and derive the 2x and 3x sheets per cel (Lanczos, edge-padded).
python3 -I "$HERE/make_scaled_sheets.py" "$W/sheets/$CAND" "$W/out"
shasum -a 256 "$W/out/"*.png
