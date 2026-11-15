"""Contact sheets: per cell, original (nearest 4x) + bicubic + candidates.

usage: python3 -I contact.py <W> <outdir> <cands,comma,sep> <cell...>
  cell = ch00 / sv05 ...; optional crop suffix @x0,y0,x1,y1 (in 4x coords)
  plus zoom factor :z (e.g. ch11@0,180,160,260:3) to magnify a crop.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

S, CW, CH = 4, 80, 65
NAMES = {"ch": "Challenge_Thumbnails", "sv": "Survival_Thumbnails"}
CELLNAMES = {
    "ch00": "War and Peas", "ch01": "Beghouled", "ch02": "Slot Machine", "ch03": "Raining Seeds",
    "ch04": "Column", "ch05": "Seeing Stars", "ch06": "Wall-nut Bowling", "ch07": "Zombiquarium",
    "ch08": "Invisighoul", "ch09": "Bungee Blitz", "ch10": "Vasebreaker", "ch11": "I, Zombie",
    "ch12": "Little Trouble", "ch13": "Dark Stormy Night", "ch14": "Pogo Party", "ch15": "Portal Combat",
    "ch16": "Whack a Zombie", "ch17": "Bobsled Bonanza", "ch18": "Zombies on Speed", "ch19": "Dr. Zomboss",
    "ch20": "Beghouled Twist", "ch21": "Last Stand",
    "sv00": "Day", "sv01": "Night", "sv02": "Pool", "sv03": "Fog", "sv04": "Roof",
    "sv05": "Day (Hard)", "sv06": "Night (Hard)", "sv07": "Pool (Hard)", "sv08": "Fog (Hard)",
    "sv09": "Roof (Hard)", "sv10": "Endless",
}


def load_sheet(W, cand, key):
    if cand == "original":
        im = Image.open(os.path.join(W, "orig", NAMES[key] + ".jpg")).convert("RGB")
        return im.resize((im.width * S, im.height * S), Image.NEAREST)
    return Image.open(os.path.join(W, "sheets", cand, NAMES[key] + "_4x.png")).convert("RGB")


def main():
    W, outdir, cands = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    cands = ["original"] + cands
    os.makedirs(outdir, exist_ok=True)
    font = ImageFont.load_default(size=18)
    cache = {}
    for spec in sys.argv[4:]:
        zoom = 1
        if ":" in spec:
            spec, z = spec.split(":"); zoom = int(z)
        crop = None
        if "@" in spec:
            spec, c = spec.split("@"); crop = tuple(int(v) for v in c.split(","))
        key, idx = spec[:2], int(spec[2:])
        box = (idx * CW * S, 0, (idx + 1) * CW * S, CH * S)
        if crop:
            box = (box[0] + crop[0], crop[1], box[0] + crop[2], crop[3])
        tw, th = (box[2] - box[0]) * zoom, (box[3] - box[1]) * zoom
        cols = min(5, len(cands))
        rows = (len(cands) + cols - 1) // cols
        lab = 24
        sheet = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + lab + 6) + 6 + 28), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        title = f"{spec} {CELLNAMES.get(spec, '')}" + (f"  crop {crop} x{zoom}" if crop else "")
        d.text((8, 5), title, fill=(255, 255, 255), font=font)
        for j, cand in enumerate(cands):
            if (cand, key) not in cache:
                cache[(cand, key)] = load_sheet(W, cand, key)
            tile = cache[(cand, key)].crop(box)
            if zoom != 1:
                tile = tile.resize((tw, th), Image.NEAREST)
            x = 6 + (j % cols) * (tw + 6)
            y = 34 + (j // cols) * (th + lab + 6)
            d.text((x, y), cand, fill=(255, 230, 120), font=font)
            sheet.paste(tile, (x, y + lab))
        fn = spec + ("_crop" if crop else "") + ".png"
        sheet.save(os.path.join(outdir, fn))
        print(os.path.join(outdir, fn), sheet.size)


if __name__ == "__main__":
    main()
