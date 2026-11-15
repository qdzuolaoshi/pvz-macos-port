#!/bin/zsh
# Run every upscaling candidate on the padded cells in $W/pad -> $W/up/<candidate>/
# usage: zsh run_all.sh [gpu-id]   (default auto GPU; pass -1 for CPU)
set -eu
W="${THUMBS_WORK:-$PWD/work}"   # work folder: pad/, up/, x_realcugan/, x_waifu2x/, tools/
R="$W/x_realcugan/realcugan-ncnn-vulkan-20220728-macos"
F="$W/x_waifu2x/waifu2x-ncnn-vulkan-20250915-macos"
G=(); [[ $# -ge 1 ]] && G=(-g "$1")
IN="$W/pad"; UP="${UP_DIR:-$W/up}"; mkdir -p "$UP"
cd "$W/tools"   # never run from inside the extracted dirs

cugan() {  # name model scale noise [extra...]
  local name=$1 model=$2 s=$3 n=$4; shift 4
  mkdir -p "$UP/$name"
  "$R/realcugan-ncnn-vulkan" -i "$IN" -o "$UP/$name" -s $s -n $n -m "$R/$model" "${G[@]}" "$@" >/dev/null 2>&1
  echo "done $name"
}
cugan2x2() {  # name model noise1 noise2 [extra...]: 2x then 2x
  local name=$1 model=$2 n1=$3 n2=$4; shift 4
  mkdir -p "$UP/_p1_$name" "$UP/$name"
  "$R/realcugan-ncnn-vulkan" -i "$IN" -o "$UP/_p1_$name" -s 2 -n $n1 -m "$R/$model" "${G[@]}" "$@" >/dev/null 2>&1
  "$R/realcugan-ncnn-vulkan" -i "$UP/_p1_$name" -o "$UP/$name" -s 2 -n $n2 -m "$R/$model" "${G[@]}" "$@" >/dev/null 2>&1
  echo "done $name"
}
w2x() {  # name model noise [extra...]: tool's -s 4 (= 2x+2x, noise model on both passes)
  local name=$1 model=$2 n=$3; shift 3
  mkdir -p "$UP/$name"
  "$F/waifu2x-ncnn-vulkan" -i "$IN" -o "$UP/$name" -s 4 -n $n -m "$F/$model" "${G[@]}" "$@" >/dev/null 2>&1
  echo "done $name"
}
w2x_gentle() {  # name model noise: 2x with noise, then 2x scale-only (-n -1)
  local name=$1 model=$2 n=$3; shift 3
  mkdir -p "$UP/_p1_$name" "$UP/$name"
  "$F/waifu2x-ncnn-vulkan" -i "$IN" -o "$UP/_p1_$name" -s 2 -n $n -m "$F/$model" "${G[@]}" "$@" >/dev/null 2>&1
  "$F/waifu2x-ncnn-vulkan" -i "$UP/_p1_$name" -o "$UP/$name" -s 2 -n -1 -m "$F/$model" "${G[@]}" "$@" >/dev/null 2>&1
  echo "done $name"
}

# Real-CUGAN models-se, native 4x
cugan cugan_se_cons   models-se 4 -1
cugan cugan_se_n0     models-se 4 0
cugan cugan_se_dn3    models-se 4 3
# Real-CUGAN models-pro has only 2x/3x -> two 2x passes.
# Always on CPU: on the M2 GPU the 2nd pass corrupted whole cells (ch_11, ch_00, ch_18).
# (CPU output still shows magenta glitch blobs on ch_11/ch_18 -> pro rejected anyway.)
G_SAVE=("${G[@]}"); G=(-g -1)
cugan2x2 cugan_pro_cons_x2_cpu     models-pro -1 -1
cugan2x2 cugan_pro_dn3cons_x2_cpu  models-pro 3 -1
G=("${G_SAVE[@]}")
# waifu2x-ncnn-vulkan 20250915 segfaults with -g -1 (CPU) on this Mac -> GPU only
if [[ ${1:-auto} == -1 ]]; then echo "skip waifu2x on CPU"; exit 0; fi
# waifu2x cunet
w2x cunet_n0 models-cunet 0
w2x cunet_n1 models-cunet 1
w2x cunet_n2 models-cunet 2
w2x cunet_n3 models-cunet 3
w2x_gentle cunet_n2_then_n-1 models-cunet 2
# refinements of the leading candidates (TTA = 8 flips/rotations averaged)
w2x cunet_n1_tta models-cunet 1 -x
w2x cunet_n2_tta models-cunet 2 -x
w2x_gentle cunet_n1_then_n-1 models-cunet 1
w2x_gentle cunet_n1_then_n-1_tta models-cunet 1 -x
# waifu2x upconv_7_anime_style_art_rgb
w2x upconv_n1 models-upconv_7_anime_style_art_rgb 1
w2x upconv_n2 models-upconv_7_anime_style_art_rgb 2
w2x upconv_n3 models-upconv_7_anime_style_art_rgb 3
