#!/usr/bin/env python3
"""
diamond_finder.py  – detect diamond symbols (rotated squares) in page_3.png
Produces:
    • detected_diamonds.png     – page with green boxes drawn
    • diamond_boxes.json        – list of {x,y,w,h,angle,score}
"""

import cv2, json, numpy as np
from pathlib import Path

# -----------------------------------------------------------
# parameters (adjust only if needed)
# -----------------------------------------------------------
TEMPLATE = "assembly.png"
PAGE = "page_3.png"
OUT_IMG = "detected_diamonds.png"
OUT_JSON = "diamond_boxes.json"

CANNY_T1, CANNY_T2 = 60, 160  # edge thresholds
DILATE_KERN = (3, 3)  # dilate kernel
CLOSE_ITER = 2  # how aggressively to close gaps
EXPECTED_WH = 95  # nominal bbox size (pixels) from your measurement
SIZE_TOL = 0.30  # ±30 % size tolerance
ANGLE_TOL = 10  # degrees around 45°
HU_THRESH = 0.05  # Hu‑moment cutoff (optional)


# -----------------------------------------------------------
# helper: get Hu‑moment shape for template once
# -----------------------------------------------------------
def template_hu(template_path=TEMPLATE):
    t = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    _, tbin = cv2.threshold(t, 200, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(tbin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tcnt = max(cnts, key=cv2.contourArea)
    return tcnt


TPL_CNT = template_hu()


# -----------------------------------------------------------
# main
# -----------------------------------------------------------
def main():
    page = cv2.imread(PAGE)
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)

    # 1 – edges
    edges = cv2.Canny(gray, CANNY_T1, CANNY_T2)

    # 2 – dilate & close gaps
    dil = cv2.dilate(edges, np.ones(DILATE_KERN, np.uint8), iterations=1)
    closed = cv2.morphologyEx(
        dil, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=CLOSE_ITER
    )

    # 3 – connected components on closed mask
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(
        closed, connectivity=8
    )

    cv2.imwrite("dbg_edges.png", edges)
    cv2.imwrite("dbg_closed.png", closed)

    matches = []
    for cid in range(1, num):  # skip background id 0
        x, y, w, h, area = stats[cid]
        # coarse size filter (square-ish)
        if not (
            EXPECTED_WH * (1 - SIZE_TOL) <= w <= EXPECTED_WH * (1 + SIZE_TOL)
            and EXPECTED_WH * (1 - SIZE_TOL) <= h <= EXPECTED_WH * (1 + SIZE_TOL)
        ):
            continue

        # 4 – minAreaRect for rotation angle
        mask = (labels == cid).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = max(cnts, key=cv2.contourArea)
        r = cv2.minAreaRect(cnt)  # ((cx,cy), (W,H), angle)
        (cx, cy), (rw, rh), angle = r
        long, short = max(rw, rh), min(rw, rh)

        # ensure square-ish long:short ratio
        if long / short > 1.25:
            continue
        # angle normalization: minAreaRect angle can be −45↔+45 depending on W/H
        ang = abs(angle) if long == rw else abs(angle - 90)
        if not (45 - ANGLE_TOL <= ang <= 45 + ANGLE_TOL):
            continue

        # 5 – optional Hu‑moment verification
        score = cv2.matchShapes(TPL_CNT, cnt, cv2.CONTOURS_MATCH_I3, 0.0)
        if score > HU_THRESH:
            continue

        # accepted
        bx, by = int(cx - long / 2), int(cy - short / 2)
        matches.append(
            dict(
                x=bx,
                y=by,
                w=int(long),
                h=int(short),
                angle=float(angle),
                score=float(score),
            )
        )
        cv2.rectangle(page, (bx, by), (bx + int(long), by + int(short)), (0, 255, 0), 4)

    cv2.imwrite(OUT_IMG, page)
    Path(OUT_JSON).write_text(json.dumps(matches, indent=2))

    print(f"✔ {len(matches)} diamonds  → {OUT_IMG}")
    for m in matches:
        print(f"   box={m['x']},{m['y']},{m['w']}x{m['h']}  score={m['score']:.4f}")


if __name__ == "__main__":
    main()
