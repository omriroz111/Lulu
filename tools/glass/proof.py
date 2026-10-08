"""Composites a render over a stand-in of the hero so it can be judged without
touching the site: the page backdrop, and below the SVG the CSS column as
style.css paints it (flat face colours multiplied by the plaster tile).

    python proof.py BACKDROP.png PLASTER.png RENDER.png OUT.png [px_per_unit] [left_hex right_hex]
"""
import sys
import numpy as np
from PIL import Image

bd, tile_p, rnd, out = sys.argv[1:5]
PPU = float(sys.argv[5]) if len(sys.argv) > 5 else 2.6
LEFT, RIGHT = (sys.argv[6], sys.argv[7]) if len(sys.argv) > 7 else ("#65300b", "#2e1204")
X0, Y0, CW, CH = 80.0, 60.0, 450.0, 720.0
TILE = 200.0
H_TOTAL = 1000

back = Image.open(bd).convert("RGB").resize((round(620 * PPU), round(780 * PPU)), Image.LANCZOS)
canvas = Image.new("RGB", (round(620 * PPU), round(H_TOTAL * PPU)), (10, 20, 22))
canvas.paste(back, (0, 0))

# the CSS column below the SVG
tile = np.asarray(Image.open(tile_p).convert("L")).astype(np.float32) / 255
px = np.asarray(canvas).astype(np.float32) / 255
ys, xs = np.mgrid[round(780 * PPU):px.shape[0], round(85 * PPU):round(525 * PPU)]
u = (xs / PPU / TILE * tile.shape[1]).astype(int) % tile.shape[1]
v = (ys / PPU / TILE * tile.shape[0]).astype(int) % tile.shape[0]
hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
col = np.where((xs / PPU < 305)[..., None], hexrgb(LEFT), hexrgb(RIGHT))
px[ys, xs] = col * tile[v, u][..., None]
canvas = Image.fromarray((np.clip(px, 0, 1) * 255 + 0.5).astype(np.uint8))

r = Image.open(rnd).convert("RGBA").resize((round(CW * PPU), round(CH * PPU)), Image.LANCZOS)
base = canvas.convert("RGBA")
base.alpha_composite(r, (round(X0 * PPU), round(Y0 * PPU)))
base.convert("RGB").save(out)
print("proof", base.size)
