# TODO: Improve this algorithm by utilizing a text recognition andremoval feature so that text-containing symbols are only considered if they have text, and the symbol is matched irrespective of the text content.
import cv2
import numpy as np
import json
import os
import shutil

# --- Configuration ---
SOURCE_IMAGE_PATH = "page_4.png"
TEMPLATE_IMAGE_PATH = "symbol_window.png"
# TEMPLATE_IMAGE_PATH = "symbol_door.png"
# TEMPLATE_IMAGE_PATH = "symbol_assembly.png"

# --- Template Size Configurations ---
# Target sizes for different templates (width, height)
DOOR_TEMPLATE_SIZE = (84, 43)  # symbol_door.png target size
ASSEMBLY_TEMPLATE_SIZE = (94, 94)  # symbol_assembly.png target size (square)
WINDOW_TEMPLATE_SIZE = (66, 77)  # symbol_window.png target size

# Map template files to their target sizes
TEMPLATE_SIZES = {
    "symbol_door.png": DOOR_TEMPLATE_SIZE,
    "symbol_assembly.png": ASSEMBLY_TEMPLATE_SIZE,
    "symbol_window.png": WINDOW_TEMPLATE_SIZE,
}

# Get current template's target size
CURRENT_TEMPLATE_SIZE = TEMPLATE_SIZES.get(
    os.path.basename(TEMPLATE_IMAGE_PATH), DOOR_TEMPLATE_SIZE  # fallback
)

# --- Output Paths ---
CLIPPINGS_DIR = "clippings_final"
CANDIDATES_JSON_PATH = "candidates_log_final.json"
OUTPUT_IMAGE_PATH = "detection_overlay_final.png"

# --- 💡 FINAL Tuning Parameters 💡 ---

# Stage 1: Candidate Generation Threshold.
MATCH_THRESHOLD = 0.28 if TEMPLATE_IMAGE_PATH.endswith("assembly.png") else 0.30

# Stage 2: Intersection over Union (IoU) Verification Threshold.
# A value between 0 and 1. A good outline overlap should be > 0.35.
IOU_THRESHOLD = 0.2 if TEMPLATE_IMAGE_PATH.endswith("assembly.png") else 0.32

# Search variability (±pixels for both width and height)
SCALE_VARIANCE_PX = 2  # ±2 pixels in both dimensions
ROTATION_RANGE = (-1, 1)
ROTATION_STEP = 1

# Other settings
CANNY_THRESHOLD_1 = 50
CANNY_THRESHOLD_2 = 200
NMS_DISTANCE_THRESHOLD = 100


# --- NEW IoU Verification Function ---
def verify_shape_iou(source_edge_clip, template_edges, threshold):
    """
    Verifies a match by calculating the Intersection over Union (IoU)
    of the edge maps. This is a robust shape matching metric.
    """
    if source_edge_clip.shape != template_edges.shape:
        return False, 0.0

    # Convert to boolean arrays for logical operations
    source_bool = source_edge_clip > 0
    template_bool = template_edges > 0

    intersection = np.sum(np.logical_and(source_bool, template_bool))
    union = np.sum(np.logical_or(source_bool, template_bool))

    if union == 0:
        return False, 0.0

    iou_score = intersection / union

    return iou_score >= threshold, iou_score


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


def generate_scale_variations(target_width, target_height, variance_px):
    """
    Generate all scale variations within the variance range.
    Returns list of (width, height) tuples.
    """
    variations = []
    for v in range(-variance_px, variance_px + 1):
        new_width = target_width + v
        new_height = target_height + v
        # Ensure positive dimensions
        if new_width > 0 and new_height > 0:
            variations.append((new_width, new_height))
    return variations


def main():
    # Setup
    if os.path.exists(CLIPPINGS_DIR):
        shutil.rmtree(CLIPPINGS_DIR)
    os.makedirs(CLIPPINGS_DIR)
    print(f"Created clean clippings directory: '{CLIPPINGS_DIR}/'")

    target_width, target_height = CURRENT_TEMPLATE_SIZE
    print(f"Using target template size: {target_width}x{target_height} pixels")

    # --- STAGE 1: CANDIDATE GENERATION ---
    print("\n--- Stage 1: Finding All Potential Candidates ---")
    source_image = cv2.imread(SOURCE_IMAGE_PATH)
    source_gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
    source_edges = cv2.Canny(source_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)
    template_image = cv2.imread(TEMPLATE_IMAGE_PATH, cv2.IMREAD_GRAYSCALE)

    all_detections_raw = []
    template_variations = {}

    # Generate scale variations
    scale_variations = generate_scale_variations(
        target_width, target_height, SCALE_VARIANCE_PX
    )

    for scale_width, scale_height in scale_variations:
        for angle in range(ROTATION_RANGE[0], ROTATION_RANGE[1] + 1, ROTATION_STEP):
            target_size = (scale_width, scale_height)
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

            # Store the edge map for Stage 2 using both width and height as key
            template_variations[(scale_width, scale_height, angle)] = template_edges

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

    # --- STAGE 2: IoU VERIFICATION ---
    print(
        f"\n--- Stage 2: Verifying Candidates with IoU Threshold > {IOU_THRESHOLD} ---"
    )

    candidates_log = []
    overlay_image = source_image.copy()

    for i, candidate in enumerate(candidate_points):
        x, y = candidate["point"]
        w, h = candidate["size"]
        angle = candidate["angle"]

        # Get the template edge map that produced this match
        matching_template_edges = template_variations[(w, h, angle)]

        # Clip the corresponding region from the source EDGE map
        source_edge_clip = source_edges[y : y + h, x : x + w]

        # Calculate the Intersection over Union score
        is_verified, iou_score = verify_shape_iou(
            source_edge_clip, matching_template_edges, IOU_THRESHOLD
        )

        status = "ACCEPTED" if is_verified else "REJECTED"

        # Log and create clippings
        clipping_filename = f"candidate_{i:03d}_{status}.png"
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

        # Create composite clipping
        clip_orig_bgr = source_image[y : y + h, x : x + w]
        template_edges_bgr = cv2.cvtColor(matching_template_edges, cv2.COLOR_GRAY2BGR)
        source_edges_bgr = cv2.cvtColor(source_edge_clip, cv2.COLOR_GRAY2BGR)
        cv2.putText(
            source_edges_bgr,
            f"IoU:{iou_score:.2f}",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
        )
        composite_clip = np.hstack(
            [clip_orig_bgr, template_edges_bgr, source_edges_bgr]
        )
        cv2.imwrite(os.path.join(CLIPPINGS_DIR, clipping_filename), composite_clip)

        if is_verified:
            color = (0, 255, 0)
            cv2.rectangle(overlay_image, (x, y), (x + w, y + h), color, 3)
            print(
                f"  ✅ Candidate {i} ACCEPTED. Match Score: {candidate['confidence']:.2f} IoU Score: {iou_score:.2f}"
            )
        else:
            print(
                f"  ❌ Candidate {i} REJECTED. Match Score: {candidate['confidence']:.2f} IoU Score: {iou_score:.2f}"
            )

    # --- FINAL OUTPUT ---
    verified_count = sum(1 for log in candidates_log if log["status"] == "ACCEPTED")
    print(f"\n✅ Found {verified_count} verified symbols.")

    with open(CANDIDATES_JSON_PATH, "w") as f:
        json.dump(candidates_log, f, indent=4)
    print(f"Saved detailed log to: {CANDIDATES_JSON_PATH}")

    cv2.imwrite(OUTPUT_IMAGE_PATH, overlay_image)
    print(f"Saving final visual overlay to: {OUTPUT_IMAGE_PATH}")

    print("\n--- Process Complete ---")


if __name__ == "__main__":
    main()
