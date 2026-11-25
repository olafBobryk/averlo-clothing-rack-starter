"""Cut a one-colour print out of a shirt photo onto a transparent PNG, locally and for free.

Usage (needs numpy, pillow and scipy):
  python3 scripts/cut-print.py PHOTO OUT.png --torso X0 Y0 X1 Y1 --panel LEFT TOP WIDTH HEIGHT

--torso   pixel box to search: the shirt body and sleeves, below the collar and hanger
--panel   the shirt panel in the photo, in pixels: left and width at the shoulder seams (sleeves excluded), top at
          the shoulder line, height down to the hem (it can run past the photo). Only used to print the
          [x, y, width, height] fractions for rack.json.

How: the shirt's silhouette (fabric-coloured pixels, holes filled, shrunk by --edge so the soft outline against the
background never counts) limits the search. The fabric is the median colour inside it, the ink the median of the
pixels furthest from the fabric. Each pixel's alpha is how far it sits along the fabric -> ink line, so soft edges
stay soft, and its colour is the pure ink. Blobs under --speck pixels are dropped. Prints with several ink colours
need a different method.
"""

import argparse
import json

import numpy as np
from PIL import Image
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument("photo")
ap.add_argument("out")
ap.add_argument("--torso", nargs=4, type=int, required=True)
ap.add_argument("--panel", nargs=4, type=float, required=True)
ap.add_argument("--pad", type=int, default=6)
ap.add_argument("--edge", type=int, default=14, help="pixels kept clear of the shirt's outline")
ap.add_argument("--speck", type=int, default=12, help="smallest ink blob kept, in pixels")
a = ap.parse_args()

img = np.asarray(Image.open(a.photo).convert("RGB")).astype(np.float32)
x0, y0, x1, y1 = a.torso
region = img[y0:y1, x0:x1]
fabric = np.median(region.reshape(-1, 3), axis=0)
# only inside the shirt: its silhouette (fabric pixels, holes filled, so the print inside counts), shrunk away from
# the soft edge where the shirt meets the background (that blend can look like ink too)
on_fabric = np.linalg.norm(region - fabric, axis=2) < 30
inside = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_closing(on_fabric, iterations=3)), iterations=a.edge)
fabric = np.median(region[inside & on_fabric], axis=0)
dist = np.linalg.norm(region - fabric, axis=2)
far = inside & (dist > 0.75 * np.percentile(dist[inside], 99.9))
ink = np.median(region[far], axis=0)

axis = ink - fabric
t = ((region - fabric) @ axis) / float(axis @ axis)
# perpendicular error: shadows or anything else that is not on the fabric -> ink line
perp = np.linalg.norm((region - fabric) - t[..., None] * axis, axis=2)
alpha = np.clip((t - 0.12) / 0.7, 0, 1)
alpha[(perp > 45) | ~inside] = 0
# drop specks: ink blobs smaller than --speck pixels
labels, n = ndimage.label(alpha > 0.3)
sizes = ndimage.sum(np.ones_like(alpha), labels, range(1, n + 1))
keep = np.isin(labels, 1 + np.nonzero(sizes >= a.speck)[0])
alpha[~ndimage.binary_dilation(keep, iterations=2)] = 0

mask = alpha > 0.02
ys, xs = np.nonzero(mask)
if len(xs) == 0:
    raise SystemExit("no print found")
bx0, bx1 = max(xs.min() - a.pad, 0), min(xs.max() + a.pad + 1, region.shape[1])
by0, by1 = max(ys.min() - a.pad, 0), min(ys.max() + a.pad + 1, region.shape[0])

out = np.zeros((by1 - by0, bx1 - bx0, 4), np.uint8)
out[..., :3] = np.clip(ink, 0, 255).astype(np.uint8)
out[..., 3] = (alpha[by0:by1, bx0:bx1] * 255).round().astype(np.uint8)
Image.fromarray(out, "RGBA").save(a.out, optimize=True)

pl, pt, pw, ph = a.panel
gx0, gy0 = x0 + bx0, y0 + by0
rect = [round(float(gx0 - pl) / pw, 3), round(float(gy0 - pt) / ph, 3), round(float(bx1 - bx0) / pw, 3), round(float(by1 - by0) / ph, 3)]
hexc = lambda c: "#%02x%02x%02x" % tuple(int(round(v)) for v in c)
print(json.dumps({"out": a.out, "fabric": hexc(fabric), "ink": hexc(ink), "rect": rect, "size": [int(bx1 - bx0), int(by1 - by0)]}))
