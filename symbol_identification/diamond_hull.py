#!/usr/bin/env python3
"""
diamond_hull.py – finds diamond symbols via convex‑hull polygon
"""

import cv2, json, math, numpy as np
from pathlib import Path

TEMPLATE = "assembly.png"
PAGE = "page_3.png"
OUT_IMG = "diamonds_hull.png"
OUT_JSON = "diamonds_hull.json"

# ------------------------------------------------------------
# auto‑get template bbox size (thin edges)
# ------------------------------------------------------------
tpl = cv2.imread(TEMPLATE, cv2.IMREAD_GRAYSCALE)
et = cv2.Canny(tpl, 60, 160)
cnts, _ = cv2.findContours(et, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
tpl_cnt = max(cnts, key=cv2.contourArea)
_, _, TPL_W, TPL_H = cv2.boundingRect(tpl_cnt)
BOX_WH = (TPL_W + TPL_H) / 2  # ≈ 94 px

# search tolerance
WH_TOL_PCT = 0.25  # ±25 %
ANGLE_TOL = 10  # deg
SIDE_RATIO = 0.15  # max deviation of side lengths


def is_square(pts, tol=SIDE_RATIO):
    d = []
    for i in range(4):
        p, q = pts[i][0], pts[(i + 1) % 4][0]
        d.append(math.hypot(p[0] - q[0], p[1] - q[1]))
    return max(d) / min(d) - 1 < tol


# ------------------------------------------------------------
# detect diamonds on page
# ------------------------------------------------------------
img = cv2.imread(PAGE)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 60, 160)

cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
diamonds = []
for c in cnts:
    if cv2.contourArea(c) < 200:  # tiny noise
        continue
    hull = cv2.convexHull(c)
    approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
    if len(approx) != 4:  # need 4 hull vertices
        continue
    if not is_square(approx):
        continue

    (cx, cy), (w, h), ang = cv2.minAreaRect(approx)
    long, short = max(w, h), min(w, h)
    if abs(long - short) > BOX_WH * WH_TOL_PCT:
        continue
    if not (BOX_WH * (1 - WH_TOL_PCT) <= long <= BOX_WH * (1 + WH_TOL_PCT)):
        continue
    theta = abs(ang) if w >= h else abs(ang - 90)
    if not (45 - ANGLE_TOL <= theta <= 45 + ANGLE_TOL):
        continue

    bx, by = int(cx - long / 2), int(cy - short / 2)
    diamonds.append(dict(x=bx, y=by, w=int(long), h=int(short)))
    cv2.rectangle(img, (bx, by), (bx + int(long), by + int(short)), (0, 255, 0), 4)

cv2.imwrite(OUT_IMG, img)
Path(OUT_JSON).write_text(json.dumps(diamonds, indent=2))
print(f"✔ {len(diamonds)} diamonds  →  {OUT_IMG}")
for d in diamonds:
    print("  box=", d)
