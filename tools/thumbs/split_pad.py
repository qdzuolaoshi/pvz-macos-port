"""Split a horizontal thumbnail sheet into 80x65 cells and pad each cell.

usage: python3 -I split_pad.py <sheet.jpg> <outdir> <prefix> [pad=8]
Writes <outdir>/<prefix>_NN.png (RGB, (80+2*pad) x (65+2*pad)), padding by
edge replication so an upscaler never sees neighbouring cells.
"""
import os
import sys

import numpy as np
from PIL import Image

CW, CH = 80, 65


def main():
    sheet, outdir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    pad = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    im = Image.open(sheet).convert("RGB")
    w, h = im.size
    assert h == CH and w % CW == 0, im.size
    os.makedirs(outdir, exist_ok=True)
    a = np.asarray(im)
    for i in range(w // CW):
        cell = a[:, i * CW:(i + 1) * CW]
        padded = np.pad(cell, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        Image.fromarray(padded, "RGB").save(os.path.join(outdir, f"{prefix}_{i:02d}.png"))
    print(f"{w // CW} cells -> {outdir}")


if __name__ == "__main__":
    main()
