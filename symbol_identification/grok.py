import cv2
import numpy as np


def angle_between_points(p1, p2, p3):
    v1 = p1 - p2
    v2 = p3 - p2
    dot = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0
    cos_theta = dot / (norm_v1 * norm_v2)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    angle = np.arccos(cos_theta) * 180 / np.pi
    return angle


# Step 1: Load image
print("Loading image...")
source = cv2.imread("page_3.png")
gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)

# Step 2: Preprocess with Gaussian blur
print("Applying Gaussian blur...")
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Step 3: Canny edge detection
print("Applying Canny edge detection...")
edges = cv2.Canny(blurred, 50, 150)
cv2.imwrite("edges.png", edges)
print("Saved: edges.png")

# Step 4: Find contours
print("Finding contours...")
contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
print(f"Found {len(contours)} contours")

# Step 5: Find quadrilaterals
quads = []
for cnt in contours:
    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) == 4:
        quads.append((cnt, approx))
print(f"Found {len(quads)} quadrilaterals")

# Debug: Print properties of first few quadrilaterals
for i in range(min(5, len(quads))):
    x, y, w, h = cv2.boundingRect(quads[i][0])
    area = cv2.contourArea(quads[i][0])
    print(f"Quad {i}: w={w}, h={h}, area={area}")

# Step 6: Filter by size
size_filtered = []
for cnt, approx in quads:
    x, y, w, h = cv2.boundingRect(cnt)
    area = cv2.contourArea(cnt)
    if 80 < w < 110 and 80 < h < 110 and abs(w - h) < 10 and 3000 < area < 6000:
        size_filtered.append((cnt, approx))
print(f"After size filter: {len(size_filtered)}")

# Step 7: Filter by angles
diamonds = []
for cnt, approx in size_filtered:
    if len(approx) == 4:
        angles = []
        for i in range(4):
            p1 = approx[i][0]
            p2 = approx[(i + 1) % 4][0]
            p3 = approx[(i + 2) % 4][0]
            angle = angle_between_points(p1, p2, p3)
            angles.append(angle)
        if all(80 < a < 100 for a in angles):
            diamonds.append(cnt)
print(f"Detected {len(diamonds)} diamonds")

# Step 8: Draw detected diamonds
print("Drawing detected diamonds...")
for diamond in diamonds:
    cv2.drawContours(source, [diamond], 0, (0, 255, 0), 2)
cv2.imwrite("detected_diamonds.png", source)
print("Saved: detected_diamonds.png")

print("Process complete. Check saved images for debugging.")
