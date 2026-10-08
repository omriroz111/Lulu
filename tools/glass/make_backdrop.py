"""Paints what sits behind the hero glass on the page, in SVG coordinates.

The render shows this through the glass and the drink, so the refracted view
lines up with the real page around it: --ink, the CSS .hero__glow (desktop
size) and the SVG glow circle, blended in sRGB the way the browser does.

    python make_backdrop.py OUT.png [px_per_unit]
"""
import sys
import numpy as np
from PIL import Image

OUT = sys.argv[1]
S = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
W, H = 620, 780

ys, xs = np.mgrid[0:int(H * S), 0:int(W * S)].astype(np.float32)
xs = (xs + 0.5) / S
ys = (ys + 0.5) / S


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0


def over(base, color, alpha):
    a = alpha[..., None]
    return base * (1 - a) + color * a


img = np.broadcast_to(rgb("#0a1416"), (ys.shape[0], xs.shape[1], 3)).copy()

# .hero__glow: 660px circle behind a 500px-wide artwork, centred on it.
# radial-gradient(circle) defaults to farthest-corner, so 62% of r*sqrt(2).
k = 620 / 500
r_el = 330 * k
d = np.hypot(xs - 310, ys - 390)
a = np.clip(1 - d / (0.62 * r_el * np.sqrt(2)), 0, 1) * 0.22
a[d > r_el] = 0
img = over(img, rgb("#e07a2f"), a)

# <circle cx=300 cy=290 r=285 fill=url(#lu-glow)>
t = np.hypot(xs - 300, ys - 290) / 285
c0, c1 = rgb("#e07a2f"), rgb("#c25f22")
u = np.clip(t / 0.52, 0, 1)[..., None]
v = np.clip((t - 0.52) / 0.48, 0, 1)[..., None]
col = np.where(t[..., None] <= 0.52, c0 * (1 - u) + c1 * u, c1 * (1 - v) + c0 * v)
alpha = np.where(t <= 0.52, 0.34 + (0.09 - 0.34) * u[..., 0], 0.09 * (1 - v[..., 0]))
alpha[t > 1] = 0
img = img * (1 - alpha[..., None]) + col * alpha[..., None]

Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT)
print("backdrop", img.shape[1], "x", img.shape[0])
