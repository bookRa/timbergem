import cv2
import numpy as np
import json
import os
import shutil

# --- Configuration ---
SOURCE_IMAGE_PATH = "page_3.png"
TEMPLATE_IMAGE_PATH = "assembly.png"
OUTPUT_JSON_PATH = "detected_diamonds_final.json"
OUTPUT_IMAGE_PATH = "detection_overlay_final.png"
CLIPPINGS_DIR = "clippings_final"

# --- 💡 Key Tuning Parameters 💡 ---

# Stage 1: Candidate Generation Threshold.
MATCH_THRESHOLD = 0.28

# Stage 2: IoU Verification Threshold. Start with a moderate value and tune based on clipping scores.
IOU_THRESHOLD = 0.20

# --- New Cleaning Function Parameter ---
# The number of largest contours to keep when cleaning the source edge clipping.
# 4 is a good starting point, representing the four sides of the diamond.
NUM_CONTOURS_TO_KEEP = 20

# Search variability.
SCALE_RANGE = (92, 96)
SCALE_STEP = 1
ROTATION_RANGE = (-1, 1)
ROTATION_STEP = 1

# Other settings
CANNY_THRESHOLD_1 = 50
CANNY_THRESHOLD_2 = 200
NMS_DISTANCE_THRESHOLD = 120


# --- ⭐️ NEW, SIMPLIFIED CLEANING FUNCTION ⭐️ ---
def clean_edges_by_keeping_largest_contours(edge_clip, num_to_keep):
    """
    Cleans an edge map by finding all contours, sorting them by area,
    and keeping only the top N largest ones.
    """
    contours, _ = cv2.findContours(edge_clip, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return np.zeros_like(edge_clip)

    # Sort contours by area in descending order
    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Keep only the top 'num_to_keep' contours
    largest_contours = sorted_contours[:num_to_keep]

    # Create a new black canvas and draw the kept contours
    clean_clip = np.zeros_like(edge_clip)
    cv2.drawContours(clean_clip, largest_contours, -1, 255, 2)

    return clean_clip


# --- IoU and Grouping Functions (Unchanged) ---
def verify_shape_iou(source_edge_clip, template_edges, threshold):
    source_bool = source_edge_clip > 0
    template_bool = template_edges > 0
    intersection = np.sum(np.logical_and(source_bool, template_bool))
    union = np.sum(np.logical_or(source_bool, template_bool))
    if union == 0:
        return False, 0.0
    iou_score = intersection / union
    return iou_score >= threshold, iou_score


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

    # --- STAGE 1 (Unchanged) ---
    print("\n--- Stage 1: Finding All Potential Candidates ---")
    source_image = cv2.imread(SOURCE_IMAGE_PATH)
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    source_edges = cv2.Canny(source_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)
    template_image = cv2.imread(TEMPLATE_IMAGE_PATH, cv2.IMREAD_GRAYSCALE)
    all_detections_raw, template_variations = [], {}

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
            template_variations[(scale_px, angle)] = template_edges
            result = cv2.matchTemplate(
                source_edges, template_edges, cv2.TM_CCOEFF_NORMED
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

    # --- STAGE 2: CLEANING AND IoU VERIFICATION ---
    print(
        f"\n--- Stage 2: Verifying Candidates with IoU Threshold > {IOU_THRESHOLD} ---"
    )

    candidates_log = []
    overlay_image = source_image.copy()

    for i, candidate in enumerate(candidate_points):
        x, y, w, h, angle = (
            *candidate["point"],
            *candidate["size"],
            candidate["angle"],
        )

        source_edge_clip_noisy = source_edges[y : y + h, x : x + w]
        source_edge_clip_clean = clean_edges_by_keeping_largest_contours(
            source_edge_clip_noisy, NUM_CONTOURS_TO_KEEP
        )
        matching_template_edges = template_variations[(w, angle)]

        is_verified, iou_score = verify_shape_iou(
            source_edge_clip_clean, matching_template_edges, IOU_THRESHOLD
        )
        status = "ACCEPTED" if is_verified else "REJECTED"

        # Create and save clippings for EVERY candidate
        clipping_filename = f"candidate_{i:03d}_{status}.png"
        clip_orig_bgr = source_image[y : y + h, x : x + w]
        template_edges_bgr = cv2.cvtColor(matching_template_edges, cv2.COLOR_GRAY2BGR)
        clean_source_edges_bgr = cv2.cvtColor(
            source_edge_clip_clean, cv2.COLOR_GRAY2BGR
        )

        # 🔽🔽🔽 --- MODIFICATION START --- 🔽🔽🔽
        # Get the match confidence score (which is used for NMS)
        match_confidence = candidate["confidence"]

        # Define text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.3
        color = (255, 0, 255)  # Magenta
        thickness = 1

        # Add the scores to the SECOND panel (template_edges_bgr)
        cv2.putText(
            template_edges_bgr,
            f"Match (NMS): {match_confidence:.2f}",
            (5, 15),
            font,
            font_scale,
            color,
            thickness,
        )
        cv2.putText(
            template_edges_bgr,
            f"IoU Score: {iou_score:.2f}",
            (5, 30),
            font,
            font_scale,
            color,
            thickness,
        )
        # 🔼🔼🔼 --- MODIFICATION END --- 🔼🔼🔼

        composite_clip = np.hstack(
            [clip_orig_bgr, template_edges_bgr, clean_source_edges_bgr]
        )
        cv2.imwrite(os.path.join(CLIPPINGS_DIR, clipping_filename), composite_clip)

        log_entry = {
            "candidate_id": i,
            "clipping_file": clipping_filename,
            "status": status,
            "match_confidence": float(candidate["confidence"]),
            "iou_score": float(iou_score),
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "matched_angle": int(angle),
        }
        candidates_log.append(log_entry)

        if is_verified:
            color = (0, 255, 0)
            cv2.rectangle(overlay_image, (x, y), (x + w, y + h), color, 3)
            print(f"  ✅ Candidate {i} ACCEPTED. IoU Score: {iou_score:.2f}")
        else:
            print(f"  ❌ Candidate {i} REJECTED. IoU Score: {iou_score:.2f}")

    # --- FINAL OUTPUT ---
    verified_count = sum(1 for log in candidates_log if log["status"] == "ACCEPTED")
    print(f"\n✅ Found {verified_count} verified diamonds.")

    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump([c for c in candidates_log if c["status"] == "ACCEPTED"], f, indent=4)
    print(f"Saved final accepted detections to: {OUTPUT_JSON_PATH}")

    cv2.imwrite(OUTPUT_IMAGE_PATH, overlay_image)
    print(f"Saving final visual overlay to: {OUTPUT_IMAGE_PATH}")

    print("\n--- Process Complete ---")


if __name__ == "__main__":
    main()
