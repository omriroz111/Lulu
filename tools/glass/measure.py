"""Prints the render's colour at fixed SVG points next to the targets."""
import sys
import numpy as np
from PIL import Image

im = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(float)
PPU = float(sys.argv[2])
X0, Y0 = 80.0, 60.0
POINTS = {  # name: (svg x, svg y, target sRGB)
    "top": (360, 600, (232, 148, 68)),
    "left@660": (180, 660, (200, 112, 40)),
    "left@770": (180, 770, (101, 48, 11)),
    "right@660": (430, 660, (118, 54, 16)),
    "right@770": (430, 770, (46, 18, 4)),
}
for k, (x, y, tgt) in POINTS.items():
    cx, cy = int((x - X0) * PPU), int((y - Y0) * PPU)
    r = max(2, int(4 * PPU))
    c = im[cy - r:cy + r, cx - r:cx + r].reshape(-1, 3).mean(0)
    print("%-10s got %3d %3d %3d   want %3d %3d %3d   ratio %.2f" % (k, *c, *tgt, c.sum() / sum(tgt)))
