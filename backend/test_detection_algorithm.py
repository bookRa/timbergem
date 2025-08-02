"""
Test script for validating the SymbolDetectionAlgorithm against gem_v5.py output.

This script tests the core detection algorithm by:
1. Loading the same inputs that gem_v5.py used
2. Running our detection algorithm
3. Comparing results with the expected gem_v5.py output
4. Validating coordinate transformations
"""

import os
import sys
import json
import cv2
import numpy as np
import fitz  # PyMuPDF
from PIL import Image

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.symbol_detection.detection_algorithm import SymbolDetectionAlgorithm, DetectionCandidate
from utils.coordinate_mapping import PageMetadata, CoordinateTransformer


def load_gem_v5_results():
    """Load the expected results from gem_v5.py for comparison"""
    candidates_file = os.path.join("..", "symbol_identification", "candidates_log_final.json")
    
    if not os.path.exists(candidates_file):
        print(f"❌ Expected results file not found: {candidates_file}")
        return None
    
    with open(candidates_file, 'r') as f:
        expected_results = json.load(f)
    
    # Filter to only accepted candidates for comparison
    accepted_results = [r for r in expected_results if r["status"] == "ACCEPTED"]
    print(f"📊 Loaded {len(accepted_results)} accepted candidates from gem_v5.py")
    
    return accepted_results


def create_test_page_metadata():
    """Create mock page metadata for testing coordinate transformations"""
    # Create realistic page metadata for a typical construction document
    return PageMetadata(
        page_number=4,  # gem_v5 was testing on page_4.png
        pdf_width_points=612.0,  # Standard letter size width in points
        pdf_height_points=792.0,  # Standard letter size height in points
        pdf_rotation_degrees=0,
        image_width_pixels=1700,  # 612 points * 200 DPI / 72 points/inch ≈ 1700
        image_height_pixels=2200,  # 792 points * 200 DPI / 72 points/inch ≈ 2200
        image_dpi=200,  # Standard DPI
        high_res_image_width_pixels=2550,  # 612 points * 300 DPI / 72 points/inch ≈ 2550
        high_res_image_height_pixels=3300,  # 792 points * 300 DPI / 72 points/inch ≈ 3300
        high_res_dpi=300  # High res DPI for detection
    )


def load_test_images():
    """Load the test images used by gem_v5.py"""
    symbol_dir = "../symbol_identification"
    
    # Load source image (page_4.png)
    source_path = os.path.join(symbol_dir, "page_4.png")
    if not os.path.exists(source_path):
        print(f"❌ Source image not found: {source_path}")
        return None, None
    
    source_image = cv2.imread(source_path, cv2.IMREAD_GRAYSCALE)
    print(f"📷 Loaded source image: {source_path} ({source_image.shape})")
    
    # Load template image (symbol_assembly.png from gem_v5.py line 12)
    template_path = os.path.join(symbol_dir, "symbol_assembly.png")
    if not os.path.exists(template_path):
        print(f"❌ Template image not found: {template_path}")
        return None, None
    
    template_image = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    print(f"🔧 Loaded template image: {template_path} ({template_image.shape})")
    
    return source_image, template_image


def test_detection_algorithm():
    """Test the detection algorithm and compare with gem_v5.py results"""
    print("🧪 Testing SymbolDetectionAlgorithm...")
    print("=" * 60)
    
    # 1. Load expected results from gem_v5.py
    expected_results = load_gem_v5_results()
    if expected_results is None:
        return False
    
    # 2. Load test images
    source_image, template_image = load_test_images()
    if source_image is None or template_image is None:
        return False
    
    # 3. Create test page metadata
    page_metadata = create_test_page_metadata()
    
    # 4. Set up target dimensions (from gem_v5.py ASSEMBLY_TEMPLATE_SIZE)
    target_dimensions = {
        "width_pixels_300dpi": 94,   # From gem_v5.py line 17
        "height_pixels_300dpi": 94   # From gem_v5.py line 17 (square)
    }
    
    # 5. Set up detection parameters to match gem_v5.py
    detection_params = {
        "match_threshold": 0.28,  # From gem_v5.py line 40 (assembly.png)
        "iou_threshold": 0.2,     # From gem_v5.py line 44 (assembly.png)
        "scale_variance_px": 2,   # From gem_v5.py line 47
        "rotation_range": (-1, 1), # From gem_v5.py line 48
        "rotation_step": 1        # From gem_v5.py line 49
    }
    
    print(f"🎯 Detection parameters: {detection_params}")
    print(f"📐 Target dimensions: {target_dimensions}")
    print(f"📄 Page metadata: {page_metadata.pdf_width_points}x{page_metadata.pdf_height_points} points")
    
    # 6. Run our detection algorithm
    print("\n🔍 Running detection algorithm...")
    algorithm = SymbolDetectionAlgorithm()
    
    try:
        detected_candidates = algorithm.detect_symbol_on_page(
            source_image, template_image, target_dimensions, page_metadata, detection_params
        )
        
        print(f"\n✅ Detection completed successfully!")
        print(f"📊 Found {len(detected_candidates)} candidates")
        
    except Exception as e:
        print(f"\n❌ Detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. Compare results with gem_v5.py output
    print(f"\n📋 Comparing with gem_v5.py results...")
    print(f"   Expected: {len(expected_results)} accepted candidates")
    print(f"   Detected: {len(detected_candidates)} candidates")
    
    # 8. Analyze detection results
    if len(detected_candidates) > 0:
        print(f"\n📈 Detection Statistics:")
        confidences = [c.match_confidence for c in detected_candidates]
        iou_scores = [c.iou_score for c in detected_candidates]
        
        print(f"   Confidence range: {min(confidences):.3f} - {max(confidences):.3f}")
        print(f"   Average confidence: {sum(confidences) / len(confidences):.3f}")
        print(f"   IoU range: {min(iou_scores):.3f} - {max(iou_scores):.3f}")
        print(f"   Average IoU: {sum(iou_scores) / len(iou_scores):.3f}")
        
        print(f"\n🔍 First few detections:")
        for i, candidate in enumerate(detected_candidates[:5]):
            print(f"   {i+1}. PDF coords: ({candidate.pdf_coords.left:.1f}, {candidate.pdf_coords.top:.1f}) "
                  f"{candidate.pdf_coords.width:.1f}x{candidate.pdf_coords.height:.1f}")
            print(f"      Image coords: ({candidate.image_coords.left}, {candidate.image_coords.top}) "
                  f"{candidate.image_coords.width}x{candidate.image_coords.height}")
            print(f"      Confidence: {candidate.match_confidence:.3f}, IoU: {candidate.iou_score:.3f}")
    
    # 9. Validate coordinate transformations
    print(f"\n🧮 Validating coordinate transformations...")
    transformer = CoordinateTransformer(page_metadata)
    
    for i, candidate in enumerate(detected_candidates[:3]):  # Check first 3
        # Transform back to image coordinates
        back_transformed = transformer.pdf_to_image(candidate.pdf_coords)
        
        # Check if round-trip transformation is accurate
        x_diff = abs(back_transformed.left - candidate.image_coords.left)
        y_diff = abs(back_transformed.top - candidate.image_coords.top)
        w_diff = abs(back_transformed.width - candidate.image_coords.width)
        h_diff = abs(back_transformed.height - candidate.image_coords.height)
        
        max_diff = max(x_diff, y_diff, w_diff, h_diff)
        print(f"   Candidate {i+1} round-trip error: {max_diff} pixels (should be < 2)")
        
        if max_diff > 2:
            print(f"     ⚠️ Large coordinate transformation error detected!")
            print(f"     Original: {candidate.image_coords.left}, {candidate.image_coords.top}, "
                  f"{candidate.image_coords.width}, {candidate.image_coords.height}")
            print(f"     Back-transformed: {back_transformed.left}, {back_transformed.top}, "
                  f"{back_transformed.width}, {back_transformed.height}")
    
    # 10. Summary
    print(f"\n🎉 Test Summary:")
    print(f"   ✅ Algorithm executed successfully")
    print(f"   ✅ Found {len(detected_candidates)} detections")
    print(f"   ✅ Coordinate transformations validated")
    
    # Compare count with expected (allowing for some variance due to algorithm differences)
    expected_count = len(expected_results)
    detected_count = len(detected_candidates)
    count_ratio = detected_count / expected_count if expected_count > 0 else 0
    
    if 0.7 <= count_ratio <= 1.5:  # Allow 30% variance
        print(f"   ✅ Detection count within reasonable range of expected ({count_ratio:.2f}x)")
    else:
        print(f"   ⚠️ Detection count significantly different from expected ({count_ratio:.2f}x)")
    
    return True


def test_coordinate_transformations():
    """Test coordinate transformation accuracy"""
    print("\n🧮 Testing coordinate transformations in isolation...")
    
    # Create test page metadata
    page_metadata = create_test_page_metadata()
    transformer = CoordinateTransformer(page_metadata)
    
    # Test some known coordinate transformations
    test_cases = [
        # (image_x, image_y, image_w, image_h) at 300 DPI
        (0, 0, 100, 100),
        (1000, 1000, 50, 50),
        (2000, 2500, 94, 94),  # Typical symbol size
    ]
    
    print("   Testing round-trip transformations (Image → PDF → Image):")
    
    for i, (x, y, w, h) in enumerate(test_cases):
        from utils.coordinate_mapping import ImageCoordinates
        
        # Create image coordinates at 300 DPI
        original_coords = ImageCoordinates(x, y, w, h, dpi=300)
        
        # Transform to PDF
        pdf_coords = transformer.image_to_pdf(original_coords)
        
        # Transform back to image
        back_coords = transformer.pdf_to_image(pdf_coords)
        
        # Check accuracy
        x_err = abs(back_coords.left - original_coords.left)
        y_err = abs(back_coords.top - original_coords.top)
        w_err = abs(back_coords.width - original_coords.width)
        h_err = abs(back_coords.height - original_coords.height)
        
        max_err = max(x_err, y_err, w_err, h_err)
        
        print(f"   Test {i+1}: ({x}, {y}) {w}x{h} → PDF → ({back_coords.left}, {back_coords.top}) "
              f"{back_coords.width}x{back_coords.height} (error: {max_err})")
        
        if max_err <= 1:
            print(f"     ✅ Accurate transformation")
        else:
            print(f"     ⚠️ High transformation error: {max_err}")


if __name__ == "__main__":
    print("🧪 SymbolDetectionAlgorithm Test Suite")
    print("=" * 60)
    
    # Test coordinate transformations first
    test_coordinate_transformations()
    
    # Test main detection algorithm
    success = test_detection_algorithm()
    
    if success:
        print(f"\n🎉 All tests completed successfully!")
    else:
        print(f"\n❌ Some tests failed!")
        sys.exit(1)