import cv2
import numpy as np
import json
import os

# --- Configuration ---
SOURCE_IMAGE_PATH = "page_3.png"
TEMPLATE_IMAGE_PATH = "assembly.png"
OUTPUT_JSON_PATH = "detected_diamonds_v2.json"
OUTPUT_IMAGE_PATH = "detection_overlay_v2.png"

# The target size (width, height) of the diamond on the main page.
TEMPLATE_TARGET_SIZE = (94, 94)

# Canny edge detection thresholds.
CANNY_THRESHOLD_1 = 50
CANNY_THRESHOLD_2 = 200

# Confidence threshold for a match (0.0 to 1.0). For edge matching, this is usually lower.
MATCH_THRESHOLD = 0.35

# Minimum distance (in pixels) between detections to be considered unique.
NMS_DISTANCE_THRESHOLD = 50


def group_close_points(points, min_distance):
    """Filters a list of points to remove those that are too close to each other."""
    if not points:
        return []

    unique_points = []
    for point in points:
        is_close = False
        for unique_point in unique_points:
            dist = np.sqrt(
                (point[0] - unique_point[0]) ** 2 + (point[1] - unique_point[1]) ** 2
            )
            if dist < min_distance:
                is_close = True
                break
        if not is_close:
            unique_points.append(point)
    return unique_points


def main():
    """Main function to run the edge-based template matching process."""
    print(f"Loading source image: {SOURCE_IMAGE_PATH}")
    if not os.path.exists(SOURCE_IMAGE_PATH):
        print(f"❌ ERROR: Source image not found at '{SOURCE_IMAGE_PATH}'")
        return
    source_image = cv2.imread(SOURCE_IMAGE_PATH)
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)

    print(f"Loading template image: {TEMPLATE_IMAGE_PATH}")
    if not os.path.exists(TEMPLATE_IMAGE_PATH):
        print(f"❌ ERROR: Template image not found at '{TEMPLATE_IMAGE_PATH}'")
        return
    template_image = cv2.imread(TEMPLATE_IMAGE_PATH, cv2.IMREAD_GRAYSCALE)

    # 1. Resize the template to match the scale in the source image.
    print(f"Resizing template to {TEMPLATE_TARGET_SIZE} pixels.")
    resized_template = cv2.resize(template_image, TEMPLATE_TARGET_SIZE)
    template_h, template_w = resized_template.shape

    # 2. Apply Canny Edge Detection to both images.
    print("Applying Canny edge detection to source and template...")
    source_edges = cv2.Canny(source_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)
    template_edges = cv2.Canny(resized_template, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)

    # 3. Perform template matching on the edge maps.
    print(f"Performing template matching with threshold: {MATCH_THRESHOLD}...")
    result = cv2.matchTemplate(source_edges, template_edges, cv2.TM_CCOEFF_NORMED)

    # 4. Find all locations exceeding the match threshold.
    locations = np.where(result >= MATCH_THRESHOLD)
    points = list(zip(*locations[::-1]))
    print(f"Found {len(points)} potential match points before filtering.")

    # 5. Filter overlapping detections.
    unique_points = group_close_points(points, NMS_DISTANCE_THRESHOLD)
    print(f"✅ Found {len(unique_points)} unique diamonds.")

    # 6. Prepare and save results.
    detected_diamonds_data = []
    overlay_image = source_image.copy()

    for x, y in unique_points:
        diamond_info = {
            "x": int(x),
            "y": int(y),
            "width": int(template_w),
            "height": int(template_h),
            "confidence": float(result[y, x]),
        }
        detected_diamonds_data.append(diamond_info)
        cv2.rectangle(
            overlay_image, (x, y), (x + template_w, y + template_h), (0, 255, 0), 3
        )

    print(f"Saving detection data to: {OUTPUT_JSON_PATH}")
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(detected_diamonds_data, f, indent=4)

    print(f"Saving visual overlay to: {OUTPUT_IMAGE_PATH}")
    cv2.imwrite(OUTPUT_IMAGE_PATH, overlay_image)

    print("\n--- Process Complete ---")


if __name__ == "__main__":
    main()
