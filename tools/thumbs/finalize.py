"""Copy the chosen candidate to final/, verify it, and draw summary comparison images.

usage: python3 -I finalize.py <W> <candidate>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

S, CW, CH = 4, 80, 65
SHEETS = [("Challenge_Thumbnails", 22, (7040, 260)), ("Survival_Thumbnails", 11, (3520, 260))]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contact import CELLNAMES  # noqa: E402  (own script in tools/)


def main():
    W, cand = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(W, "final"), exist_ok=True)
    os.makedirs(os.path.join(W, "compare"), exist_ok=True)
    font = ImageFont.load_default(size=18)
    for name, n, size in SHEETS:
        src = Image.open(os.path.join(W, "sheets", cand, f"{name}_4x.png"))
        assert src.mode == "RGB" and src.size == size, (src.mode, src.size)
        dst = os.path.join(W, "final", f"{name}_4x.png")
        Image.fromarray(np.asarray(src), "RGB").save(dst, format="PNG", optimize=True)
        chk = Image.open(dst)
        a = np.asarray(chk).astype(np.float64)
        o = np.asarray(Image.open(os.path.join(W, "orig", f"{name}.jpg")).convert("RGB")).astype(np.float64)
        down = a.reshape(CH, S, CW * n, S, 3).mean(axis=(1, 3))
        print(f"{dst}: {chk.format} {chk.mode} {chk.size} bytes={os.path.getsize(dst)} "
              f"sheet PSNR(box-down vs orig)={peak_signal_noise_ratio(o, down, data_range=255):.2f} "
              f"SSIM={structural_similarity(o, down, data_range=255, channel_axis=2):.4f} "
              f"identical_to_candidate={np.array_equal(np.asarray(chk), np.asarray(src))}")
        # overview: final cells in rows of 11 at full resolution, with labels
        key = "ch" if name.startswith("Ch") else "sv"
        cols = 11 if n == 22 else 6
        rows = (n + cols - 1) // cols
        ov = Image.new("RGB", (cols * 326 + 6, rows * 290 + 6), (40, 40, 40))
        d = ImageDraw.Draw(ov)
        for i in range(n):
            x, y = 6 + (i % cols) * 326, 6 + (i // cols) * 290
            d.text((x, y), f"{key}{i:02d} {CELLNAMES[f'{key}{i:02d}']}", fill=(255, 230, 120), font=font)
            ov.paste(chk.crop((i * 320, 0, (i + 1) * 320, 260)), (x, y + 24))
        ov.save(os.path.join(W, "compare", f"final_overview_{key}.png"))

    # key comparison: rows = representative cells, cols = methods
    cells = ["ch00", "ch03", "ch06", "ch11", "ch19", "sv05", "sv10"]
    methods = ["original", "bicubic", "cugan_se_cons", "cunet_n0", cand]
    labels = ["original (nearest)", "bicubic", "Real-CUGAN se cons", "waifu2x cunet n0", f"CHOSEN {cand}"]
    sheets = {}
    for m in methods:
        for nm, n, _ in SHEETS:
            k = "ch" if nm.startswith("Ch") else "sv"
            if m == "original":
                im = Image.open(os.path.join(W, "orig", f"{nm}.jpg")).convert("RGB")
                sheets[(m, k)] = im.resize((im.width * S, im.height * S), Image.NEAREST)
            else:
                sheets[(m, k)] = Image.open(os.path.join(W, "sheets", m, f"{nm}_4x.png")).convert("RGB")
    out = Image.new("RGB", (150 + len(methods) * 326, 30 + len(cells) * 266), (40, 40, 40))
    d = ImageDraw.Draw(out)
    for j, lab in enumerate(labels):
        d.text((150 + j * 326, 6), lab, fill=(255, 230, 120), font=font)
    for r, c in enumerate(cells):
        k, i = c[:2], int(c[2:])
        y = 30 + r * 266
        d.text((6, y + 110), f"{c}\n{CELLNAMES[c]}", fill=(255, 255, 255), font=font)
        for j, m in enumerate(methods):
            out.paste(sheets[(m, k)].crop((i * 320, 0, (i + 1) * 320, 260)), (150 + j * 326, y))
    out.save(os.path.join(W, "compare", "key_comparison.png"))
    print("wrote compare/key_comparison.png, final_overview_ch.png, final_overview_sv.png")


if __name__ == "__main__":
    main()
