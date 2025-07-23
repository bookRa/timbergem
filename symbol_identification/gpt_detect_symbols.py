#!/usr/bin/env python3
"""
Step‑by‑step diagnostic: see exactly why diamonds are skipped.
• Writes debug images (threshold, closed, contour overlay)
• Dumps CSV of contour stats
"""

import cv2, csv, json, numpy as np
from pathlib import Path
from collections import defaultdict

TEMPLATE = "assembly.png"
PAGE = "page_3.png"

# ---------- parameters you can tweak ----------
ADAPT_BLOCKSIZE = 11  # odd, e.g. 11 or 15
ADAPT_C = 2
CLOSE_ITER = 2  # how aggressively to close gaps
SIZE_RANGE = (60, 140)  # minW/H , maxW/H
ASPECT_RANGE = (0.80, 1.25)
HU_THRESH = 0.06  # matchShapes threshold
# ----------------------------------------------


def adaptive_close(gray):
    thr = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPT_BLOCKSIZE,
        ADAPT_C,
    )
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=CLOSE_ITER)
    return thr, closed


def main():
    # 1) template contour
    tpl = cv2.imread(TEMPLATE, cv2.IMREAD_GRAYSCALE)
    _, thr_tpl = cv2.threshold(tpl, 200, 255, cv2.THRESH_BINARY_INV)

    cnts, _ = cv2.findContours(thr_tpl, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tpl_cnt = max(cnts, key=cv2.contourArea)

    # 2) preprocess page
    page = cv2.imread(PAGE)
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    thr, closed = adaptive_close(gray)

    cv2.imwrite("thr_raw.png", thr)
    cv2.imwrite("thr_closed.png", closed)

    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    stats = []
    survivors = []
    stages = defaultdict(int)

    for idx, c in enumerate(cnts):
        stages["total"] += 1
        area = cv2.contourArea(c)
        if area < 300:  # tiny noise
            continue
        stages["area"] += 1

        x, y, w, h = cv2.boundingRect(c)
        aspect = w / h
        if not (
            SIZE_RANGE[0] <= w <= SIZE_RANGE[1] and SIZE_RANGE[0] <= h <= SIZE_RANGE[1]
        ):
            continue
        if not (ASPECT_RANGE[0] <= aspect <= ASPECT_RANGE[1]):
            continue
        stages["size/aspect"] += 1

        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if not (4 <= len(approx) <= 8):
            continue
        stages["poly"] += 1

        score = cv2.matchShapes(tpl_cnt, c, cv2.CONTOURS_MATCH_I3, 0.0)
        if score > HU_THRESH:
            continue
        stages["hu"] += 1

        survivors.append((x, y, w, h))
        stats.append(
            {
                "idx": idx,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "verts": len(approx),
                "hu": score,
            }
        )

    # 3) draw survivors
    out = page.copy()
    for x, y, w, h in survivors:
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 4)
    cv2.imwrite("detected_diamonds_debug.png", out)

    # 4) CSV dump
    with open("contour_stats.csv", "w", newline="") as f:
        wcsv = csv.DictWriter(f, fieldnames=["idx", "x", "y", "w", "h", "verts", "hu"])
        wcsv.writeheader()
        wcsv.writerows(stats)

    print("\n--- pipeline counts ---")
    for k, v in stages.items():
        print(f"{k:12}: {v}")
    print(f"Saved debug img -> detected_diamonds_debug.png")
    print(f"Saved CSV       -> contour_stats.csv")


if __name__ == "__main__":
    main()
