# HD challenge and survival covers: provenance

> In this repository the upscaled sheets are **not included** (they are derived from the game's art). Generate them
> from your own copy of the game with `regenerate.sh`, then place them in `overrides/images/` before running
> `scripts/build_apps.sh`. Without them the game simply uses its original covers.

The mini-game, puzzle, survival and Limbo pages show 80x65 covers cut from two small JPEG sheets. On a
magnified presentation (Retina windows, larger windows, fullscreen) they looked blurry, so the game now draws
them from AI-upscaled sheets with the same cel layout. This folder records how those sheets were made and how to
regenerate them.

## Shipped files

`overrides/images/` (copied into `build/res/images/` and into both apps by `scripts/build_apps.sh`).
All are 8-bit RGB PNG (lossless), one row of cels in the original order.

| File | Size | Cel | Bytes | sha256 |
|---|---|---|---|---|
| Challenge_Thumbnails_2x.png | 3520x130 | 160x130 | 570148 | 125281aec35a562acfa1ef6797f5e5d3ec00d947633d14c27d1900fff50317fa |
| Challenge_Thumbnails_3x.png | 5280x195 | 240x195 | 1065753 | f489f85912c51dea40d960308c5933eef8f2339425956f0c211627a042525411 |
| Challenge_Thumbnails_4x.png | 7040x260 | 320x260 | 1570096 | 2735c3b4501d6a2bd8cb90fe78281167dba49bea459e125518533f8421faa680 |
| Survival_Thumbnails_2x.png | 1760x130 | 160x130 | 335227 | e2a293b214b6c4946581c5234803d5af6beb57025c7b7877a772992a8560a421 |
| Survival_Thumbnails_3x.png | 2640x195 | 240x195 | 628184 | e3ad3985f92a29a61aac335aae1c35c82b8dbbccdd44b56235869c29a6929ca8 |
| Survival_Thumbnails_4x.png | 3520x260 | 320x260 | 938421 | 24e19b6be119c4de555f3286ff4211e19cbca603ca2839a461823f54cdc8d8ab |

## Sources

Both editions use the same originals, entries of your game's `main.pak` (the translation has no loose copies):

| Entry | Size | Bytes | sha256 |
|---|---|---|---|
| `images\Challenge_Thumbnails.jpg` | 1760x65, 22 cels of 80x65 | 36789 | 5861036fc51c38441b609974687be9006528609a512ff0a919e18c236b7027c8 |
| `images\Survival_Thumbnails.jpg` | 880x65, 11 cels of 80x65 | 22252 | afcd7b2ff4d2247588f7ab35377aa5c313e03afd0957cb58f8a9a752193dc9c0 |

## Upscaler

waifu2x-ncnn-vulkan, release 20250915 for macOS (https://github.com/nihui/waifu2x-ncnn-vulkan/releases, MIT
licence), run on the Mac's GPU (Vulkan, device auto-selected). Neither the binary nor the models are stored in the
project.

| Item | sha256 |
|---|---|
| waifu2x-ncnn-vulkan-20250915-macos.zip | a5b58b239eb3aa030db5464f6759637fe412d8c07891a4346ea57f708b514d42 |
| waifu2x-ncnn-vulkan (binary) | 1be8cd5976ac5fbda399b1b87a9f711e430689936bdd9d6514c49fca47507005 |
| models-cunet/noise1_scale2.0x_model.param | ccc3b2f1c9fad829ecdda40cac8dc853fcddf14917170efba888b256fbf9074a |
| models-cunet/noise1_scale2.0x_model.bin | 862c0e40f3df956ff57bd4d168c85dea5d375b614077fdddd3ac8cfdb9a686da |
| models-cunet/scale2.0x_model.param | ccc3b2f1c9fad829ecdda40cac8dc853fcddf14917170efba888b256fbf9074a |
| models-cunet/scale2.0x_model.bin | d82ed30207fd07e1c16726a9ca838ce44e6e25a105b0278c7ca681516ee0e18e |

## Method

1. `split_pad.py`: cut each sheet into 80x65 cells and pad every cell by 8 px with edge replication (96x81), so
   the network never sees a neighbouring cell.
2. waifu2x model `models-cunet`, pass 1: `-s 2 -n 1 -x` (2x with noise level 1, TTA: the 8 flips/rotations
   averaged) -> 192x162.
3. Pass 2 on the pass-1 output: `-s 2 -n -1 -x` (2x, no denoising, TTA) -> 384x324.
4. `assemble_eval.py`: crop the 32-px border (8 px x 4) back to 320x260 and assemble the 4x sheets in the
   original cel order. The same script computes the evaluation metrics (it also writes bicubic and Lanczos
   reference sheets, which are not shipped).
5. `make_scaled_sheets.py`: the 4x sheets are shipped unchanged; the 2x and 3x sheets are derived per cel (cel
   edge-padded by 16 px at 4x, Pillow Lanczos resize, i.e. an anti-aliased downscale, then cropped), so no cel
   bleeds into its neighbour.

Candidate selection (exploratory scripts kept for the record: `run_all.sh` ran every candidate; `contact.py` and
`finalize.py` drew the comparison sheets): Real-CUGAN se/pro, waifu2x cunet noise 0-3 and two-pass/TTA variants,
and waifu2x upconv_7 were compared by metrics and by eye; Real-CUGAN pro was rejected because its output had
corrupted or glitched cells. The chosen candidate is `cunet_n1_then_n-1_tta` (steps 2-3). Its 4x cells,
box-downscaled to 1x and compared with the original JPEG over the 32 non-black cels: PSNR 31.27 dB mean (27.11 min),
SSIM 0.910 mean, CIEDE2000 1.28 mean, 8-px JPEG block-edge ratio 1.031 (original 1.114).

`run_all.sh` reproduces that candidate run (work directory `THUMBS_WORK`, default `./work`); `regenerate.sh` is
the self-contained version of the chosen pipeline.

## How the game uses them

`ChallengeScreen::DrawThumbnail` (`PvZ-Portable/src/Lawn/Widget/ChallengeScreen.cpp` after the patch) draws each cover into
the original logical rect (button x + 13, y + 4, 80x65) with the original cel index. With a presentation scale s
above 1.02 it uses the sheet whose scale k is the smallest of 2, 3, 4 at or above s (4 beyond that), so the GPU
minifies it by less than 2x or magnifies the 4x sheet. At s <= 1.02, and when a sheet is missing or does not
measure k times the original sheet, it draws the original JPEG cel as before.

Sheet lifetime: a sheet loads on first use (8 bits per channel) into one cache shared by all challenge screens, so
while the presentation scale stays the same it is decoded and uploaded once per process, not on every page open. When a challenge screen closes, only the
sheets for the scale k of the current presentation are kept (none at s <= 1.02); a dropped sheet loads again if a
later page needs it. The cache is freed in `~LawnApp`, while the GL interface still exists. In LOW_MEMORY builds,
which also release the original sheets with the screen, the whole cache is freed whenever a challenge screen
closes. A failed load (missing or wrong-size file) is not retried, except after such a LOW_MEMORY free.

## Regenerating

```sh
# full run (needs the extracted waifu2x-ncnn-vulkan-20250915-macos release; Vulkan/MoltenVK GPU)
zsh tools/thumbs/regenerate.sh <empty workdir> <path to waifu2x-ncnn-vulkan-20250915-macos>
# re-assemble from upscaled cells kept from an earlier run (skips the upscaler)
UPSCALED=<dir with ch_NN.png and sv_NN.png> zsh tools/thumbs/regenerate.sh <empty workdir>
cp <workdir>/out/*.png overrides/images/
```

Python 3 with numpy, Pillow, scipy and scikit-image; run scripts with `python3 -I`.

Check (2026-11-06): with `UPSCALED` set to the cells of the original run, `regenerate.sh` reproduced all 33
padded input cells and all six shipped files byte for byte. The upscaler step was not re-run; GPU inference may
differ slightly on other GPUs or driver versions.

## Files in this folder

- `regenerate.sh`: the chosen pipeline end to end (steps 1-5).
- `pak_list.py`: read-only main.pak lister/extractor (writes entries with `\` and `/` flattened to `__`).
- `split_pad.py`, `assemble_eval.py`, `make_scaled_sheets.py`: steps 1, 4 and 5.
- `run_all.sh`, `contact.py`, `finalize.py`: the original candidate run and comparison images.
