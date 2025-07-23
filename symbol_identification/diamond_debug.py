import cv2, csv, numpy as np

# --- load the binary mask you already saved ----------------
closed = cv2.imread("thr_closed.png", cv2.IMREAD_GRAYSCALE)  # white = symbol blobs
page = cv2.imread("page_3.png")  # colour page for overlay

num, labels, stats, centroids = cv2.connectedComponentsWithStats(closed, 8)
rows = []

font = cv2.FONT_HERSHEY_SIMPLEX
for cid in range(1, num):  # skip background 0
    x, y, w, h, area = stats[cid]
    cx, cy = centroids[cid]
    cnt_mask = (labels == cid).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(cnt_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = cnts[0]

    # rotated bbox + angle
    rect = cv2.minAreaRect(cnt)
    ((rcx, rcy), (rw, rh), theta) = rect
    long, short = max(rw, rh), min(rw, rh)
    angle_norm = abs(theta) if rw >= rh else abs(theta - 90)  # 0–90°, 45°≈diamond

    # draw overlay with ID
    cv2.rectangle(page, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(page, f"{cid}", (int(cx), int(cy)), font, 0.7, (0, 0, 255), 2)

    rows.append(
        dict(
            id=cid,
            x=x,
            y=y,
            w=w,
            h=h,
            aspect=round(w / h, 3),
            area=area,
            long=round(long, 1),
            short=round(short, 1),
            angle_deg=round(angle_norm, 1),
        )
    )

# --- save + print ------------------------------------------------------------
cv2.imwrite("cc_overlay.png", page)
with open("cc_stats.csv", "w", newline="") as f:
    csv.DictWriter(f, rows[0].keys()).writerows(rows)

print(f"📝  Wrote cc_stats.csv  ({len(rows)} blobs)")
print("📷  Overlay image  ->  cc_overlay.png")
