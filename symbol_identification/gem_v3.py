import cv2
import numpy as np
import json
import os

# --- Configuration ---
SOURCE_IMAGE_PATH = "page_3.png"
TEMPLATE_IMAGE_PATH = "assembly.png"
OUTPUT_JSON_PATH = "detected_diamonds_v3.json"
OUTPUT_IMAGE_PATH = "detection_overlay_v3.png"
DEBUG_HEATMAP_PATH = "debug_confidence_heatmap.png"

# 💡 --- Key Tuning Parameters --- 💡

# 1. Scale Variability: Search for diamonds from 88px to 102px wide.
SCALE_RANGE = (88, 102)
SCALE_STEP = 2  # Check every 2 pixels in size.

# 2. Rotation Variability: Check rotations from -6 to +6 degrees.
ROTATION_RANGE = (-6, 6)
ROTATION_STEP = 2  # Check every 2 degrees.

# 3. Canny Edge Detection Thresholds.
CANNY_THRESHOLD_1 = 50
CANNY_THRESHOLD_2 = 200

# 4. Confidence threshold for a match (0.0 to 1.0).
MATCH_THRESHOLD = 0.35

# 5. Non-Maximum Suppression (NMS) distance to merge overlapping boxes.
NMS_DISTANCE_THRESHOLD = 50


def group_close_points(points_data, min_distance):
    """
    Groups close points based on confidence score, keeping the one with the highest confidence.
    'points_data' should be a list of dictionaries, each with 'point' and 'confidence'.
    """
    if not points_data:
        return []

    # Sort by confidence in descending order to process best matches first
    points_data.sort(key=lambda p: p["confidence"], reverse=True)

    unique_detections = []
    for data in points_data:
        point = data["point"]
        is_close = False
        for unique_data in unique_detections:
            unique_point = unique_data["point"]
            dist = np.sqrt(
                (point[0] - unique_point[0]) ** 2 + (point[1] - unique_point[1]) ** 2
            )
            if dist < min_distance:
                is_close = True
                break
        if not is_close:
            unique_detections.append(data)

    return unique_detections


def main():
    """Main function to run the advanced detection process."""
    print(f"Loading source image: {SOURCE_IMAGE_PATH}")
    source_image = cv2.imread(SOURCE_IMAGE_PATH)
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    source_edges = cv2.Canny(source_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)

    print(f"Loading template image: {TEMPLATE_IMAGE_PATH}")
    template_image = cv2.imread(TEMPLATE_IMAGE_PATH, cv2.IMREAD_GRAYSCALE)

    all_detections_raw = []
    # This will store the highest confidence score for each pixel for debugging.
    max_confidence_map = np.zeros(source_gray.shape, dtype=np.float32)

    # --- Main Loop for Scale and Rotation ---
    print("\nStarting multi-scale and multi-rotation matching...")
    for scale_px in range(SCALE_RANGE[0], SCALE_RANGE[1] + 1, SCALE_STEP):
        target_size = (scale_px, scale_px)
        scaled_template = cv2.resize(template_image, target_size)

        for angle in range(ROTATION_RANGE[0], ROTATION_RANGE[1] + 1, ROTATION_STEP):
            print(f"  Matching with template: size={target_size}, angle={angle}°")

            # Rotate the scaled template
            h, w = scaled_template.shape
            center = (w // 2, h // 2)
            rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated_template = cv2.warpAffine(
                scaled_template, rot_mat, (w, h), borderValue=255
            )  # Fill with white

            # Get edges of the final transformed template
            template_edges = cv2.Canny(
                rotated_template, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2
            )

            # Perform matching
            result = cv2.matchTemplate(
                source_edges, template_edges, cv2.TM_CCOEFF_NORMED
            )

            # Update the master confidence map for the heatmap
            # We need to pad 'result' to match the source image size
            h_res, w_res = result.shape
            max_confidence_map[0:h_res, 0:w_res] = np.maximum(
                max_confidence_map[0:h_res, 0:w_res], result
            )

            # Collect all points above the threshold for this specific template
            locations = np.where(result >= MATCH_THRESHOLD)
            for pt in zip(*locations[::-1]):
                all_detections_raw.append(
                    {
                        "point": pt,
                        "confidence": result[pt[1], pt[0]],
                        "size": target_size,
                        "angle": angle,
                    }
                )

    print(f"\nFound {len(all_detections_raw)} potential match points before filtering.")

    # --- Process and Save Results ---
    unique_detections_data = group_close_points(
        all_detections_raw, NMS_DISTANCE_THRESHOLD
    )
    print(f"✅ Found {len(unique_detections_data)} unique diamonds after filtering.")

    detected_diamonds_final = []
    overlay_image = source_image.copy()

    for detection in unique_detections_data:
        x, y = detection["point"]
        w, h = detection["size"]

        diamond_info = {
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "confidence": float(detection["confidence"]),
            "matched_angle": int(detection["angle"]),
            "matched_scale": detection["size"][0],
        }
        detected_diamonds_final.append(diamond_info)
        cv2.rectangle(overlay_image, (x, y), (x + w, y + h), (0, 255, 0), 3)

    # --- Save Outputs ---
    print(f"Saving final detection data to: {OUTPUT_JSON_PATH}")
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(detected_diamonds_final, f, indent=4)

    print(f"Saving visual overlay to: {OUTPUT_IMAGE_PATH}")
    cv2.imwrite(OUTPUT_IMAGE_PATH, overlay_image)

    # Create and save the debug heatmap
    print(f"Saving debug confidence heatmap to: {DEBUG_HEATMAP_PATH}")
    heatmap_normalized = cv2.normalize(
        max_confidence_map, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U
    )
    cv2.imwrite(DEBUG_HEATMAP_PATH, heatmap_normalized)

    print("\n--- Process Complete ---")


if __name__ == "__main__":
    main()
