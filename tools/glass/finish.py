"""Turns the render into assets/img/coupe.webp and places it in index.html.

    python tools/glass/finish.py RENDER.png [px_per_unit]

- clears the denoiser's 1-3/255 alpha haze from the empty frame and crops;
- over the last BAND units above the SVG's foot, eases the block's faces into
  exactly what the CSS column paints there (its top colour times the shared
  plaster tile, multiplied the way the browser does), so the column carries
  on from the render with no seam;
- points <image id="lu-coupe"> at the matching SVG box.
"""
import pathlib
import re
import sys

import numpy as np
from PIL import Image

X0, Y0 = 80.0, 60.0                       # must match make_glass.py
TILE = 200.0                              # SVG units per plaster tile
BAND = (665.0, 780.0)                     # SVG y range of the hand-over: long, so the slope eases out
src = pathlib.Path(sys.argv[1])
PPU = float(sys.argv[2]) if len(sys.argv) > 2 else 2.6
site = pathlib.Path(__file__).resolve().parents[2]

px = np.asarray(Image.open(src).convert("RGBA")).astype(np.float32)
px[px[..., 3] <= 3] = 0

# --- hand the faces over to the CSS column
css = (site / "assets/css/style.css").read_text(encoding="utf-8")
def first_stop(child):
    m = re.search(r"\.plinth span:%s \{.*?linear-gradient\(to bottom, #(\w{6}) 0" % child, css, re.S)
    return np.array([int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
left_c, right_c = first_stop("first-child"), first_stop("last-child")
tile = np.asarray(Image.open(site / "assets/img/plaster.webp").convert("L")).astype(np.float32) / 255

h, w = px.shape[:2]
ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
sx = X0 + (xs + 0.5) / PPU
sy = Y0 + (ys + 0.5) / PPU
tu = ((sx % TILE) / TILE * tile.shape[1]).astype(int) % tile.shape[1]
tv = ((sy % TILE) / TILE * tile.shape[0]).astype(int) % tile.shape[0]
target = np.where((sx < 305)[..., None], left_c, right_c) * tile[tv, tu][..., None]
t = np.clip((sy - BAND[0]) / (BAND[1] - BAND[0]), 0, 1)
wgt = (t * t * (3 - 2 * t)) * ((sx > 85) & (sx < 525) & (px[..., 3] >= 254))
px[..., :3] = px[..., :3] * (1 - wgt[..., None]) + target * wgt[..., None]

im = Image.fromarray(np.clip(px + 0.5, 0, 255).astype(np.uint8), "RGBA")
a = np.asarray(im)[..., 3]
yy, xx = np.nonzero(a > 0)
pad = 3
left, top = max(xx.min() - pad, 0), max(yy.min() - pad, 0)
right, bottom = min(xx.max() + pad + 1, w), min(yy.max() + pad + 1, h)
crop = im.crop((left, top, right, bottom))

out = site / "assets/img/coupe.webp"
crop.save(out, "WEBP", quality=88, alpha_quality=100, method=6)

box = dict(x=X0 + left / PPU, y=Y0 + top / PPU, width=crop.width / PPU, height=crop.height / PPU)
attrs = " ".join('%s="%.2f"' % (k, v) for k, v in box.items())
idx = site / "index.html"
s = idx.read_text(encoding="utf-8")
s, n = re.subn(r'(<image id="lu-coupe" href="assets/img/coupe\.webp")[^/]*/>', r"\1 %s/>" % attrs, s)
assert n == 1, "no <image id=lu-coupe> in index.html"
idx.write_text(s, encoding="utf-8")
print("coupe.webp %dx%d, %d KB; svg box %s" % (crop.width, crop.height, out.stat().st_size // 1024, attrs))
