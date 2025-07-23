import cv2
import numpy as np


def detect_diamond_symbols(source_image_path, output_image_path):
    """
    Detects diamond-shaped symbols using a more robust contour analysis
    method that handles touching lines and filters more strictly.

    Args:
        source_image_path (str): The file path for the source architectural drawing.
        output_image_path (str): The file path to save the output image.
    """
    # --- 1. Load and Preprocess the Image ---
    image = cv2.imread(source_image_path)
    if image is None:
        print(f"Error: Could not load image from {source_image_path}")
        return

    output_image = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Use a high-contrast binary threshold.
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # --- 2. Find All Contours ---
    # RETR_TREE is still the best mode for finding all potential shapes.
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    print(f"Found {len(contours)} total contours. Applying robust analysis...")
    detected_count = 0

    for contour in contours:
        # --- 3. Filter Contours by Area ---
        # A preliminary filter to remove anything obviously too small or too large.
        area = cv2.contourArea(contour)
        if area < 100 or area > 5000:
            continue

        # --- 4. NEW: Analyze the Convex Hull ---
        # This is the key to ignoring attached lines. We analyze the hull of the
        # shape, not the raw contour itself.
        hull = cv2.convexHull(contour)

        # Approximate the hull to a polygon.
        perimeter = cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, 0.03 * perimeter, True)

        # --- 5. Apply Stricter Geometric Filters ---
        # We only proceed if the approximated hull is a quadrilateral.
        if len(approx) == 4:

            # Filter 1: Solidity Check
            # Solidity is the ratio of the contour area to its convex hull area.
            # A solid diamond shape will have a solidity close to 1.
            hull_area = cv2.contourArea(hull)
            if hull_area == 0:
                continue
            solidity = float(area) / hull_area
            if solidity < 0.9:
                continue

            # Filter 2: Aspect Ratio Check
            # The bounding box of the shape should be squarish.
            (x, y, w, h) = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            if aspect_ratio < 0.8 or aspect_ratio > 1.2:
                continue

            # If all checks pass, we've likely found a diamond.
            cv2.drawContours(output_image, [approx], -1, (0, 255, 0), 2)
            detected_count += 1

    print(f"Successfully detected and highlighted {detected_count} diamond symbols.")

    # --- 6. Save the Final Image ---
    cv2.imwrite(output_image_path, output_image)
    print(f"Output image saved to: {output_image_path}")


# --- Main Execution ---
if __name__ == "__main__":
    input_file = "page_3.png"
    output_file = "page_3_detected_diamonds_v4.png"

    detect_diamond_symbols(input_file, output_file)
