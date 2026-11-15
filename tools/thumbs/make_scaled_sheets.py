"""Derive the 2x and 3x cover sheets from the 4x masters and copy the 4x masters unchanged.

usage: python3 -I make_scaled_sheets.py <dir with *_4x.png> <outdir>

Each 320x260 cel of a 4x master is edge-padded by PAD texels on every side (so the filter never
reads a neighbouring cel), resized with Pillow's Lanczos filter (support scaled with the reduction,
i.e. an anti-aliased downscale) to (80k + 2 PAD k/4) x (65k + 2 PAD k/4), and cropped back to its
80k x 65k cel. The game picks the sheet whose scale k is the smallest one at or above the window's
presentation scale, so the GPU only ever minifies a sheet by less than 2x (or magnifies the 4x one).
Output: 8-bit RGB PNG, written with optimize=True (lossless).
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

CW, CH, MASTER = 80, 65, 4
PAD = 16  # texels at 4x; becomes 8 at 2x and 12 at 3x (integers, so the crop is exact)
SHEETS = [("Challenge_Thumbnails", 22), ("Survival_Thumbnails", 11)]
SCALES = [2, 3]


def scaled_sheet(master, n, k):
    a = np.asarray(master)
    assert a.shape == (CH * MASTER, CW * MASTER * n, 3), a.shape
    pk = PAD * k // MASTER
    assert pk * MASTER == PAD * k
    out = np.zeros((CH * k, CW * k * n, 3), np.uint8)
    for i in range(n):
        cel = a[:, i * CW * MASTER:(i + 1) * CW * MASTER]
        padded = Image.fromarray(np.pad(cel, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge"), "RGB")
        small = padded.resize((CW * k + 2 * pk, CH * k + 2 * pk), Image.LANCZOS)
        out[:, i * CW * k:(i + 1) * CW * k] = np.asarray(small)[pk:pk + CH * k, pk:pk + CW * k]
    return Image.fromarray(out, "RGB")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for name, n in SHEETS:
        mpath = os.path.join(src, f"{name}_4x.png")
        master = Image.open(mpath)
        assert master.mode == "RGB" and master.size == (CW * MASTER * n, CH * MASTER), (master.mode, master.size)
        shutil.copyfile(mpath, os.path.join(dst, f"{name}_4x.png"))
        for k in SCALES:
            out = os.path.join(dst, f"{name}_{k}x.png")
            scaled_sheet(master, n, k).save(out, format="PNG", optimize=True)
            chk = Image.open(out)
            print(f"{out}: {chk.mode} {chk.size} {os.path.getsize(out)} bytes")


if __name__ == "__main__":
    main()
