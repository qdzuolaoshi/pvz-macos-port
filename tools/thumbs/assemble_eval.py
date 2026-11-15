"""Assemble upscaled padded cells into 4x sheets and evaluate every candidate.

usage: python3 -I assemble_eval.py <W>
  reads  <W>/orig/{Challenge,Survival}_Thumbnails.jpg, <W>/up/<cand>/{ch,sv}_NN.png
  writes <W>/sheets/<cand>/{Challenge,Survival}_Thumbnails_4x.png,
         <W>/metrics/summary.csv, <W>/metrics/percell.csv
Baselines (bicubic, lanczos) are generated here from the same padded cells.
"""
import csv
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

S, PAD, CW, CH = 4, 8, 80, 65
SHEETS = {"ch": ("Challenge_Thumbnails", 22), "sv": ("Survival_Thumbnails", 11)}


def luma(a):
    a = a.astype(np.float64)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def box_down(a, s=S):
    h, w = a.shape[0] // s, a.shape[1] // s
    return a.astype(np.float64).reshape(h, s, w, s, -1).mean(axis=(1, 3))


def blockiness(l1):
    """Ratio of mean |horizontal+vertical step| on 8-px JPEG grid lines vs elsewhere (1x luma)."""
    dx = np.abs(np.diff(l1, axis=1))  # dx[:, x-1] = step between x-1 and x
    dy = np.abs(np.diff(l1, axis=0))
    bx = np.zeros(dx.shape[1], bool); bx[7::8] = True
    by = np.zeros(dy.shape[0], bool); by[7::8] = True
    on = np.concatenate([dx[:, bx].ravel(), dy[by, :].ravel()])
    off = np.concatenate([dx[:, ~bx].ravel(), dy[~by, :].ravel()])
    return on.mean() / max(off.mean(), 1e-6)


def overshoot(up, orig):
    """Fraction of 4x pixels whose luma lies >10 levels outside the 3x3 min/max of the source."""
    lo = ndimage.minimum_filter(luma(orig), size=3)
    hi = ndimage.maximum_filter(luma(orig), size=3)
    lo4 = np.repeat(np.repeat(lo, S, 0), S, 1)
    hi4 = np.repeat(np.repeat(hi, S, 0), S, 1)
    l = luma(up)
    ex = np.maximum(lo4 - l, 0) + np.maximum(l - hi4, 0)
    return (ex > 10).mean() * 100.0


def sharp(up):
    l = luma(up)
    return np.hypot(ndimage.sobel(l, 0), ndimage.sobel(l, 1)).mean()


def baseline_cell(padded, method):
    im = Image.fromarray(padded)
    big = im.resize((im.width * S, im.height * S), method)
    return np.asarray(big)


def main():
    W = sys.argv[1]
    cands = sorted(d for d in os.listdir(os.path.join(W, "up")) if not d.startswith("_"))
    cands = ["bicubic", "lanczos"] + cands
    os.makedirs(os.path.join(W, "metrics"), exist_ok=True)
    origs = {k: np.asarray(Image.open(os.path.join(W, "orig", f"{v[0]}.jpg")).convert("RGB")) for k, v in SHEETS.items()}
    percell = []
    summary = []
    bic_sharp = {}
    for cand in cands:
        rows = []
        for key, (name, n) in SHEETS.items():
            sheet = np.zeros((CH * S, CW * S * n, 3), np.uint8)
            for i in range(n):
                orig = origs[key][:, i * CW:(i + 1) * CW]
                if cand in ("bicubic", "lanczos"):
                    padded = np.pad(orig, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
                    up = baseline_cell(padded, Image.BICUBIC if cand == "bicubic" else Image.LANCZOS)
                else:
                    up = np.asarray(Image.open(os.path.join(W, "up", cand, f"{key}_{i:02d}.png")).convert("RGB"))
                assert up.shape == ((CH + 2 * PAD) * S, (CW + 2 * PAD) * S, 3), (cand, key, i, up.shape)
                up = up[PAD * S:PAD * S + CH * S, PAD * S:PAD * S + CW * S]
                sheet[:, i * CW * S:(i + 1) * CW * S] = up
                down = box_down(up)
                o = orig.astype(np.float64)
                psnr = peak_signal_noise_ratio(o, down, data_range=255)
                ssim = structural_similarity(o, down, data_range=255, channel_axis=2)
                # colour / content change: CIEDE2000 between lightly blurred 1x images
                ob = ndimage.gaussian_filter(o, (1.0, 1.0, 0)) / 255.0
                db = ndimage.gaussian_filter(down, (1.0, 1.0, 0)) / 255.0
                de = deltaE_ciede2000(rgb2lab(ob), rgb2lab(db))
                # local content error: blurred |luma diff|, 99th percentile
                le = ndimage.gaussian_filter(np.abs(luma(o) - luma(down)), 1.0)
                mean_shift = (down.mean(axis=(0, 1)) - o.mean(axis=(0, 1)))
                row = dict(cand=cand, sheet=key, cell=i, psnr=psnr, ssim=ssim,
                           de_mean=de.mean(), de_p99=np.percentile(de, 99),
                           lerr_p99=np.percentile(le, 99),
                           shift_r=mean_shift[0], shift_g=mean_shift[1], shift_b=mean_shift[2],
                           overshoot_pct=overshoot(up, orig), sharp=sharp(up),
                           block=blockiness(luma(down)), block_orig=blockiness(luma(o)))
                if np.isinf(psnr):
                    row["psnr"] = 99.0
                rows.append(row)
            out = os.path.join(W, "sheets", cand)
            os.makedirs(out, exist_ok=True)
            Image.fromarray(sheet, "RGB").save(os.path.join(out, f"{name}_4x.png"), optimize=True)
        if cand == "bicubic":
            for r in rows:
                bic_sharp[(r["sheet"], r["cell"])] = r["sharp"]
        for r in rows:
            r["sharp_vs_bicubic"] = r["sharp"] / max(bic_sharp[(r["sheet"], r["cell"])], 1e-6)
        percell += rows
        nz = [r for r in rows if not (r["sheet"] == "ch" and r["cell"] == 13)]  # cell 13 is solid black
        summary.append(dict(
            cand=cand,
            psnr_mean=np.mean([r["psnr"] for r in nz]),
            psnr_min=min(r["psnr"] for r in nz),
            ssim_mean=np.mean([r["ssim"] for r in nz]),
            ssim_min=min(r["ssim"] for r in nz),
            de_mean=np.mean([r["de_mean"] for r in nz]),
            de_p99_max=max(r["de_p99"] for r in nz),
            lerr_p99_max=max(r["lerr_p99"] for r in nz),
            overshoot_pct=np.mean([r["overshoot_pct"] for r in nz]),
            sharp_vs_bicubic=np.mean([r["sharp_vs_bicubic"] for r in nz]),
            block=np.mean([r["block"] for r in nz]),
        ))
    keys = list(percell[0].keys())
    with open(os.path.join(W, "metrics", "percell.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(percell)
    with open(os.path.join(W, "metrics", "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    print(f"{'cand':24s} {'PSNR':>6s} {'PSNRmin':>7s} {'SSIM':>6s} {'SSIMmin':>7s} {'dE':>5s} {'dE99mx':>6s} {'Lerr99mx':>8s} {'ovsh%':>6s} {'sharp':>6s} {'block':>6s}")
    for s in summary:
        print(f"{s['cand']:24s} {s['psnr_mean']:6.2f} {s['psnr_min']:7.2f} {s['ssim_mean']:6.4f} {s['ssim_min']:7.4f} "
              f"{s['de_mean']:5.2f} {s['de_p99_max']:6.2f} {s['lerr_p99_max']:8.2f} {s['overshoot_pct']:6.2f} {s['sharp_vs_bicubic']:6.2f} {s['block']:6.3f}")
    ob = np.mean([blockiness(luma(origs[k][:, i * CW:(i + 1) * CW].astype(float))) for k, (nme, n) in SHEETS.items() for i in range(n) if not (k == 'ch' and i == 13)])
    print(f"original blockiness (1x): {ob:.3f}")


if __name__ == "__main__":
    main()
