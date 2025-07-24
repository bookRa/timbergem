import cv2
import numpy as np
import json
import os
import shutil

# --- Configuration ---
SOURCE_IMAGE_PATH = "page_3.png"
TEMPLATE_IMAGE_PATH = "assembly.png"

# --- Output Paths ---
CLIPPINGS_DIR = "clippings"
CANDIDATES_JSON_PATH = "candidates_log.json"
OUTPUT_IMAGE_PATH = "detection_overlay_final.png"
DEBUG_HEATMAP_PATH = "debug_confidence_heatmap.png"

# --- Key Tuning Parameters ---

# Stage 1: Lower threshold to ensure we find all potential candidates.
MATCH_THRESHOLD = 0.28

# Stage 2: The new Peak-to-Average Ratio threshold. A good match should have a
# peak value at least 2.75x higher than the average of its match region.
PEAK_QUALITY_THRESHOLD = 2.75

# Multi-scale and rotation settings remain the same.
SCALE_RANGE = (92, 96)
SCALE_STEP = 1
ROTATION_RANGE = (-1, 1)
ROTATION_STEP = 1

# Other settings
CANNY_THRESHOLD_1 = 50
CANNY_THRESHOLD_2 = 200
NMS_DISTANCE_THRESHOLD = 50


# --- NEW Verification Function ---
def verify_peak_quality(match_region, threshold):
    """
    Analyzes a clipped heatmap region. A good match has a sharp peak relative
    to the average energy in the region.
    Returns the verification status and the calculated score.
    """
    if match_region is None or match_region.size == 0:
        return False, 0.0

    peak_value = np.max(match_region)
    mean_value = np.mean(match_region)

    if mean_value < 1e-6:  # Avoid division by zero for black regions
        return False, 0.0

    # Calculate the Peak-to-Average Ratio (PAR)
    score = peak_value / mean_value

    return score >= threshold, score


# --- Helper Function (unchanged) ---
def group_close_points(points_data, min_distance):
    points_data.sort(key=lambda p: p["confidence"], reverse=True)
    unique_detections = []
    for data in points_data:
        is_close = False
        for unique_data in unique_detections:
            dist = np.sqrt(
                (data["point"][0] - unique_data["point"][0]) ** 2
                + (data["point"][1] - unique_data["point"][1]) ** 2
            )
            if dist < min_distance:
                is_close = True
                break
        if not is_close:
            unique_detections.append(data)
    return unique_detections


def main():
    # Setup
    if os.path.exists(CLIPPINGS_DIR):
        shutil.rmtree(CLIPPINGS_DIR)
    os.makedirs(CLIPPINGS_DIR)
    print(f"Created clean clippings directory: '{CLIPPINGS_DIR}/'")

    # --- STAGE 1: CANDIDATE GENERATION ---
    print("\n--- Stage 1: Finding All Potential Candidates ---")
    source_image = cv2.imread(SOURCE_IMAGE_PATH)
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    source_edges = cv2.Canny(source_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)
    template_image = cv2.imread(TEMPLATE_IMAGE_PATH, cv2.IMREAD_GRAYSCALE)

    all_detections_raw = []
    max_confidence_map = np.zeros(source_gray.shape, dtype=np.float32)

    # Multi-scale, multi-rotation matching loop
    for scale_px in range(SCALE_RANGE[0], SCALE_RANGE[1] + 1, SCALE_STEP):
        for angle in range(ROTATION_RANGE[0], ROTATION_RANGE[1] + 1, ROTATION_STEP):
            target_size = (scale_px, scale_px)
            scaled_template = cv2.resize(template_image, target_size)
            h, w = scaled_template.shape
            center = (w // 2, h // 2)
            rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated_template = cv2.warpAffine(
                scaled_template, rot_mat, (w, h), borderValue=255
            )
            template_edges = cv2.Canny(
                rotated_template, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2
            )

            result = cv2.matchTemplate(
                source_edges, template_edges, cv2.TM_CCOEFF_NORMED
            )

            h_res, w_res = result.shape
            max_confidence_map[0:h_res, 0:w_res] = np.maximum(
                max_confidence_map[0:h_res, 0:w_res], result
            )

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

    candidate_points = group_close_points(all_detections_raw, NMS_DISTANCE_THRESHOLD)
    print(f"Found {len(candidate_points)} unique candidates.")

    # --- STAGE 2: PEAK QUALITY VERIFICATION ---
    print("\n--- Stage 2: Verifying Peak Quality for Each Candidate ---")

    candidates_log = []
    overlay_image = source_image.copy()

    for i, candidate in enumerate(candidate_points):
        x, y = candidate["point"]
        w, h = candidate["size"]

        # Correctly clip the full match region from the heatmap
        match_region_heatmap = max_confidence_map[y : y + h, x : x + w]

        is_verified, peak_quality_score = verify_peak_quality(
            match_region_heatmap, PEAK_QUALITY_THRESHOLD
        )

        status = "ACCEPTED" if is_verified else "REJECTED"
        color = (0, 255, 0) if is_verified else (0, 0, 255)

        # --- Create and save the composite clipping ---
        clip_orig = source_image[y : y + h, x : x + w]
        clip_edge = cv2.cvtColor(source_edges[y : y + h, x : x + w], cv2.COLOR_GRAY2BGR)
        clip_heat = cv2.normalize(
            match_region_heatmap, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U
        )
        clip_heat_bgr = cv2.cvtColor(clip_heat, cv2.COLOR_GRAY2BGR)

        # Draw the score on the heatmap clipping
        cv2.putText(
            clip_heat_bgr,
            f"PAR Score:{peak_quality_score:.2f}",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
        )

        composite_clip = np.hstack([clip_orig, clip_edge, clip_heat_bgr])
        clipping_filename = f"candidate_{i:03d}_{status}.png"
        cv2.imwrite(os.path.join(CLIPPINGS_DIR, clipping_filename), composite_clip)

        # Log and draw on overlay
        log_entry = {
            "candidate_id": i,
            "clipping_file": clipping_filename,
            "status": status,
            "match_confidence": float(candidate["confidence"]),
            "peak_quality_score": float(peak_quality_score),
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
        }
        candidates_log.append(log_entry)

        if is_verified:
            cv2.rectangle(overlay_image, (x, y), (x + w, y + h), color, 3)
            print(
                f"  ✅ Candidate {i} ACCEPTED. Peak Quality Score: {peak_quality_score:.2f}"
            )

    # --- FINAL OUTPUT ---
    verified_count = sum(1 for log in candidates_log if log["status"] == "ACCEPTED")
    print(f"\n✅ Found {verified_count} verified diamonds.")

    with open(CANDIDATES_JSON_PATH, "w") as f:
        json.dump(candidates_log, f, indent=4)
    print(f"Saved detailed log to: {CANDIDATES_JSON_PATH}")

    cv2.imwrite(OUTPUT_IMAGE_PATH, overlay_image)
    print(f"Saving final visual overlay to: {OUTPUT_IMAGE_PATH}")

    cv2.imwrite(
        DEBUG_HEATMAP_PATH,
        cv2.normalize(max_confidence_map, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U),
    )
    print(f"Saving debug confidence heatmap to: {DEBUG_HEATMAP_PATH}")

    print("\n--- Process Complete ---")


if __name__ == "__main__":
    main()
