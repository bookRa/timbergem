import cv2
import numpy as np
import pytesseract


# --- Helper function for Non-Maximum Suppression ---
def non_max_suppression(boxes, overlapThresh):
    """
    A simple implementation of Non-Maximum Suppression to merge
    overlapping bounding boxes.
    """
    if len(boxes) == 0:
        return []

    # If the bounding boxes are integers, convert them to floats -- this
    # is important since we'll be doing a bunch of divisions
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")

    # Initialize the list of picked indexes
    pick = []

    # Grab the coordinates of the bounding boxes
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]

    # Compute the area of the bounding boxes and sort the bounding
    # boxes by the bottom-right y-coordinate of the bounding box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)

    # Keep looping while some indexes still remain in the indexes
    # list
    while len(idxs) > 0:
        # Grab the last index in the indexes list and add the
        # index value to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        # Find the largest (x, y) coordinates for the start of
        # the bounding box and the smallest (x, y) coordinates
        # for the end of the bounding box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        # Compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        # Compute the ratio of overlap
        overlap = (w * h) / area[idxs[:last]]

        # Delete all indexes from the index list that have
        idxs = np.delete(
            idxs, np.concatenate(([last], np.where(overlap > overlapThresh)[0]))
        )

    # Return only the bounding boxes that were picked as integers
    return boxes[pick].astype("int")


def detect_diamond_symbols_hybrid(
    source_image_path, template_image_path, output_image_path
):
    """
    Detects diamond symbols using a multi-stage hybrid pipeline:
    1. Candidate generation via edge-based template matching.
    2. Filtering via size, shape, and OCR validation.
    """
    # --- Load Source and Template Images ---
    source_img = cv2.imread(source_image_path)
    template_img = cv2.imread(template_image_path)
    if source_img is None or template_img is None:
        print(
            f"Error loading images. Check paths: {source_image_path}, {template_image_path}"
        )
        return

    # Convert images to grayscale for processing
    source_gray = cv2.cvtColor(source_img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

    # --- STAGE 1: CANDIDATE GENERATION (Edge-Based Template Matching) ---
    print("Stage 1: Finding candidate regions using template matching...")

    # Get template dimensions
    tH, tW = template_gray.shape[:2]

    # **REFINEMENT**: Apply Gaussian Blur to smooth images before edge detection.
    # This makes the matching more robust to noise and slight variations.
    source_blurred = cv2.GaussianBlur(source_gray, (5, 5), 0)
    template_blurred = cv2.GaussianBlur(template_gray, (5, 5), 0)

    # Create edge maps from the blurred images
    template_edges = cv2.Canny(template_blurred, 50, 200)
    source_edges = cv2.Canny(source_blurred, 50, 200)

    # Use a multi-scale approach to find templates of slightly different sizes
    candidate_boxes = []
    for scale in np.linspace(0.8, 1.2, 20)[::-1]:
        # Resize the source image for the multi-scale search
        resized_w = int(source_edges.shape[1] * scale)
        resized_h = int(source_edges.shape[0] * scale)
        resized_source = cv2.resize(source_edges, (resized_w, resized_h))

        r = source_edges.shape[1] / float(resized_source.shape[1])

        if resized_source.shape[0] < tH or resized_source.shape[1] < tW:
            break

        result = cv2.matchTemplate(resized_source, template_edges, cv2.TM_CCOEFF_NORMED)

        # **REFINEMENT**: Lowered threshold to increase recall.
        # This will find more potential candidates, which will be filtered later.
        threshold = 0.3
        loc = np.where(result >= threshold)

        for pt in zip(*loc[::-1]):
            startX = int(pt[0] * r)
            startY = int(pt[1] * r)
            endX = int((pt[0] + tW) * r)
            endY = int((pt[1] + tH) * r)
            candidate_boxes.append((startX, startY, endX - startX, endY - startY))

    # Merge overlapping candidate boxes
    if not candidate_boxes:
        print(
            "No initial candidates found. Try lowering the template matching threshold further."
        )
    candidate_boxes = np.array(candidate_boxes)
    candidate_boxes = non_max_suppression(candidate_boxes, 0.3)
    print(f"Found {len(candidate_boxes)} unique candidate regions.")

    # --- STAGE 2: MULTI-FACTOR FILTERING ---
    print("Stage 2: Filtering candidates with size, shape, and OCR...")
    validated_symbols = []
    for x, y, w, h in candidate_boxes:
        # **Filter 1: Size Constraint**
        # Use the provided 94x94 knowledge with some tolerance
        if not (70 < w < 120 and 70 < h < 120):
            continue

        # **Filter 2: Shape Re-Validation (on the ROI)**
        roi_gray = source_gray[y : y + h, x : x + w]
        _, roi_thresh = cv2.threshold(
            roi_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        contours, _ = cv2.findContours(
            roi_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            continue

        # Find the largest contour in the ROI
        contour = max(contours, key=cv2.contourArea)

        # Check if it's a 4-sided, convex polygon
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue

        # **Filter 3: OCR Validation**
        # Crop from the original grayscale image for best OCR results
        ocr_roi = source_gray[y : y + h, x : x + w]

        # Pad the ROI slightly to improve OCR accuracy
        padded_roi = cv2.copyMakeBorder(
            ocr_roi, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
        )

        # Use Tesseract to extract text
        # --psm 7: Treat the image as a single text line.
        custom_config = r"--oem 3 --psm 7 -c tessedit_char_whitelist=Ww0123456789ab"
        text = pytesseract.image_to_string(padded_roi, config=custom_config)

        # Check if the extracted text matches a plausible symbol format (e.g., starts with 'W', has a digit)
        text = text.strip()
        if (
            len(text) > 1
            and text.upper().startswith("W")
            and any(char.isdigit() for char in text)
        ):
            validated_symbols.append((x, y, w, h))

    print(f"Found {len(validated_symbols)} symbols after all validation steps.")

    # --- Draw Final Results ---
    output_image = source_img.copy()
    for x, y, w, h in validated_symbols:
        cv2.rectangle(output_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imwrite(output_image_path, output_image)
    print(f"Output image saved to: {output_image_path}")


# --- Main Execution ---
if __name__ == "__main__":
    # IMPORTANT: You must have Tesseract installed on your system for this to work.
    # For Windows, download from: https://github.com/UB-Mannheim/tesseract/wiki
    # For macOS (using Homebrew): brew install tesseract
    # For Linux (Debian/Ubuntu): sudo apt-get install tesseract-ocr

    # **REFINEMENT**: Changed to .jpg to match the uploaded file.
    input_file = "page_3.png"
    template_file = "assembly.png"  # Your diamond template image
    output_file = "page_3_detected_diamonds_v6_hybrid.png"

    detect_diamond_symbols_hybrid(input_file, template_file, output_file)
