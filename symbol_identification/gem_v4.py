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
OUTPUT_IMAGE_PATH = "detection_overlay_debug.png"
DEBUG_HEATMAP_PATH = "debug_confidence_heatmap.png"

# --- Tuning Parameters (from previous run) ---
MATCH_THRESHOLD = 0.28
PATTERN_CONFIDENCE_THRESHOLD = 0.35
VERIFICATION_KERNEL_SIZE = 15

SCALE_RANGE = (88, 102)
SCALE_STEP = 2
ROTATION_RANGE = (-6, 6)
ROTATION_STEP = 2

CANNY_THRESHOLD_1 = 50
CANNY_THRESHOLD_2 = 200
NMS_DISTANCE_THRESHOLD = 50


# --- Helper Functions (unchanged) ---
def verify_match_pattern(confidence_map, point, kernel_size, threshold):
    half = kernel_size // 2
    x, y = point
    kernel = confidence_map[y - half : y + half + 1, x - half : x + half + 1]
    if kernel.size == 0:
        return False, 0.0
    diag1_mask = np.eye(kernel_size, dtype=bool)
    diag2_mask = np.fliplr(diag1_mask)
    diagonal_mask = diag1_mask | diag2_mask
    total_sum = np.sum(kernel)
    diagonal_sum = np.sum(kernel[diagonal_mask])
    if total_sum == 0:
        return False, 0.0
    score = diagonal_sum / total_sum
    return score >= threshold, score


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
    # --- Setup Output Directory ---
    if os.path.exists(CLIPPINGS_DIR):
        shutil.rmtree(CLIPPINGS_DIR)
    os.makedirs(CLIPPINGS_DIR)
    print(f"Created clean clippings directory: '{CLIPPINGS_DIR}/'")

    # --- STAGE 1: CANDIDATE GENERATION (same as before) ---
    print("\n--- Stage 1: Finding All Potential Candidates ---")
    source_image = cv2.imread(SOURCE_IMAGE_PATH)
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    source_edges = cv2.Canny(source_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)
    template_image = cv2.imread(TEMPLATE_IMAGE_PATH, cv2.IMREAD_GRAYSCALE)

    all_detections_raw = []
    max_confidence_map = np.zeros(source_gray.shape, dtype=np.float32)

    for scale_px in range(SCALE_RANGE[0], SCALE_RANGE[1] + 1, SCALE_STEP):
        for angle in range(ROTATION_RANGE[0], ROTATION_RANGE[1] + 1, ROTATION_STEP):
            target_size = (scale_px, scale_px)
            # ... (rest of the matching loop is identical to the previous script)
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

    # --- STAGE 2: VERIFY AND GENERATE DEBUG CLIPPINGS ---
    print("\n--- Stage 2: Verifying Candidates and Generating Debug Clippings ---")

    candidates_log = []
    overlay_image = source_image.copy()

    for i, candidate in enumerate(candidate_points):
        candidate_id = i
        is_verified, pattern_score = verify_match_pattern(
            max_confidence_map,
            candidate["point"],
            VERIFICATION_KERNEL_SIZE,
            PATTERN_CONFIDENCE_THRESHOLD,
        )

        status = "ACCEPTED" if is_verified else "REJECTED"

        # --- Create and save the composite clipping ---
        x, y = candidate["point"]
        w, h = candidate["size"]

        # Clip from original, edges, and heatmap
        clip_orig = source_image[y : y + h, x : x + w]
        clip_edge = cv2.cvtColor(source_edges[y : y + h, x : x + w], cv2.COLOR_GRAY2BGR)
        clip_heat = cv2.normalize(
            max_confidence_map[y : y + h, x : x + w],
            None,
            0,
            255,
            cv2.NORM_MINMAX,
            cv2.CV_8U,
        )
        clip_heat = cv2.cvtColor(clip_heat, cv2.COLOR_GRAY2BGR)

        # Add text labels to each clipping
        cv2.putText(
            clip_orig,
            "Original",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1,
        )
        cv2.putText(
            clip_edge, "Edges", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1
        )
        cv2.putText(
            clip_heat,
            f"Heatmap (Score:{pattern_score:.2f})",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1,
        )

        # Stack the images horizontally
        composite_clip = np.hstack([clip_orig, clip_edge, clip_heat])
        clipping_filename = f"candidate_{candidate_id:03d}.png"
        cv2.imwrite(os.path.join(CLIPPINGS_DIR, clipping_filename), composite_clip)

        # --- Log data for JSON output ---
        log_entry = {
            "candidate_id": candidate_id,
            "clipping_file": clipping_filename,
            "status": status,
            "match_confidence": float(candidate["confidence"]),
            "pattern_score": float(pattern_score),
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "matched_angle": int(candidate["angle"]),
            "matched_scale": candidate["size"][0],
        }
        candidates_log.append(log_entry)

        # Draw on the main overlay image
        color = (
            (0, 255, 0) if is_verified else (0, 0, 255)
        )  # Green for accepted, Red for rejected
        cv2.rectangle(overlay_image, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            overlay_image,
            str(candidate_id),
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2,
        )

    # --- FINAL OUTPUT ---
    print(f"\n✅ Generated {len(candidates_log)} debug clippings.")

    print(f"Saving detailed candidates log to: {CANDIDATES_JSON_PATH}")
    with open(CANDIDATES_JSON_PATH, "w") as f:
        json.dump(candidates_log, f, indent=4)

    print(f"Saving visual overlay to: {OUTPUT_IMAGE_PATH}")
    cv2.imwrite(OUTPUT_IMAGE_PATH, overlay_image)

    # Save the heatmap (still useful)
    heatmap_normalized = cv2.normalize(
        max_confidence_map, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U
    )
    print(f"Saving debug confidence heatmap to: {DEBUG_HEATMAP_PATH}")
    cv2.imwrite(DEBUG_HEATMAP_PATH, heatmap_normalized)

    print("\n--- Process Complete ---")


if __name__ == "__main__":
    main()
