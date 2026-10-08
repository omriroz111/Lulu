"""Seamless plaster texture shared by the rendered block and the CSS column.

A grey multiplier near 1.0: soft trowel mottling plus a fine grain. Built by
filtering white noise in the frequency domain, which makes it periodic, so it
tiles with no seam. One tile covers TILE SVG units; the render samples it in
screen space and the column repeats it at the same scale and origin, which is
what lets the two meet without a visible join.

    python make_tile.py OUT_DIR
"""
import sys
import pathlib
import numpy as np
from PIL import Image

TILE_UNITS = 200
N = 512
out = pathlib.Path(sys.argv[1])
rng = np.random.default_rng(7)

f = np.fft.fftfreq(N)
fr = np.hypot(*np.meshgrid(f, f))
fr[0, 0] = 1


def band(beta, lo, hi):
    w = rng.standard_normal((N, N))
    spec = np.fft.fft2(w) / fr ** beta
    spec *= (fr > lo) & (fr < hi)
    x = np.real(np.fft.ifft2(spec))
    return (x - x.mean()) / x.std()


mottle = band(1.6, 1 / 260, 1 / 18)       # trowel clouds, 20-90 units across
mid = band(1.0, 1 / 30, 1 / 5)            # the patchiness inside them
grain = band(0.0, 1 / 5, 0.5)             # sand in the plaster

t = 0.94 + 0.017 * mottle + 0.009 * mid + 0.015 * grain
t = np.clip(t, 0.80, 1.0)
img = Image.fromarray((t * 255 + 0.5).astype(np.uint8), "L")
img.save(out / "plaster.png")
img.save(out / "plaster.webp", quality=82, method=6)
print("tile", N, "px =", TILE_UNITS, "units; mean %.3f min %.3f" % (t.mean(), t.min()))
