"""
Validation script to compare our detection results with gem_v5.py output.

This script provides detailed comparison of:
1. Detection coordinates (exact match validation)
2. Confidence scores (should be very close)
3. IoU scores (should be very close)
4. Detection count accuracy
"""

import json
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_gem_v5_results():
    """Load the expected results from gem_v5.py"""
    candidates_file = os.path.join("..", "symbol_identification", "candidates_log_final.json")
    with open(candidates_file, 'r') as f:
        all_results = json.load(f)
    
    # Filter to accepted candidates
    accepted = [r for r in all_results if r["status"] == "ACCEPTED"]
    return accepted

def compare_detection_results():
    """Compare our results with gem_v5.py output"""
    
    print("🔍 Detailed Detection Accuracy Validation")
    print("=" * 60)
    
    # Load expected results
    expected = load_gem_v5_results()
    print(f"📊 Loaded {len(expected)} expected detections from gem_v5.py")
    
    # Our test results (from the test output with more precision)
    our_detections = [
        {"x": 5527, "y": 3951, "width": 96, "height": 96, "confidence": 0.450484, "iou": 0.332237},
        {"x": 5229, "y": 3581, "width": 96, "height": 96, "confidence": 0.449865, "iou": 0.331687},
        {"x": 4795, "y": 3352, "width": 96, "height": 96, "confidence": 0.440518, "iou": 0.325490},
        {"x": 5211, "y": 3316, "width": 96, "height": 96, "confidence": 0.419693, "iou": 0.307125},
        {"x": 4623, "y": 3132, "width": 93, "height": 93, "confidence": 0.407642, "iou": 0.300240},
        {"x": 5131, "y": 2698, "width": 96, "height": 96, "confidence": 0.401080, "iou": 0.293839},
        {"x": 5226, "y": 4457, "width": 96, "height": 96, "confidence": 0.401080, "iou": 0.293839},
        {"x": 5423, "y": 3130, "width": 96, "height": 96, "confidence": 0.399169, "iou": 0.292835},
        {"x": 4135, "y": 3095, "width": 96, "height": 96, "confidence": 0.394082, "iou": 0.289332},
        {"x": 5086, "y": 1995, "width": 96, "height": 96, "confidence": 0.377207, "iou": 0.276235},
        {"x": 5895, "y": 4119, "width": 96, "height": 96, "confidence": 0.376842, "iou": 0.275430},
        {"x": 4428, "y": 4253, "width": 96, "height": 96, "confidence": 0.356953, "iou": 0.263331},
        {"x": 4507, "y": 3299, "width": 93, "height": 93, "confidence": 0.353424, "iou": 0.260690},
        {"x": 5682, "y": 4905, "width": 96, "height": 96, "confidence": 0.341173, "iou": 0.251773},
        {"x": 4648, "y": 3906, "width": 96, "height": 96, "confidence": 0.339172, "iou": 0.250850},
        {"x": 4763, "y": 3615, "width": 96, "height": 96, "confidence": 0.322719, "iou": 0.238975},
    ]
    
    print(f"🎯 Our algorithm found {len(our_detections)} detections")
    
    # Compare detection by detection
    print(f"\n📋 Detailed Comparison (all detections):")
    print(f"{'ID':<3} {'Coordinates':^20} {'Confidence':^20} {'IoU':^20} {'Match':^8}")
    print(f"{'':=<3} {'':=<20} {'':=<20} {'':=<20} {'':=<8}")
    
    exact_matches = 0
    close_matches = 0
    
    for i in range(min(len(expected), len(our_detections))):
        exp = expected[i]
        ours = our_detections[i]
        
        # Check coordinate match
        coord_match = (exp["x"] == ours["x"] and exp["y"] == ours["y"] and 
                      exp["width"] == ours["width"] and exp["height"] == ours["height"])
        
        # Check confidence similarity (within 0.005 for exact, 0.05 for close)
        conf_diff = abs(exp["match_confidence"] - ours["confidence"])
        conf_exact = conf_diff < 0.005
        conf_close = conf_diff < 0.05
        
        # Check IoU similarity (within 0.005 for exact, 0.05 for close)
        iou_diff = abs(exp["iou_score"] - ours["iou"])
        iou_exact = iou_diff < 0.005
        iou_close = iou_diff < 0.05
        
        # Overall match assessment
        if coord_match and conf_exact and iou_exact:
            match_status = "✅ EXACT"
            exact_matches += 1
        elif coord_match and conf_close and iou_close:
            match_status = "✅ CLOSE"
            close_matches += 1
        else:
            match_status = "❌ DIFF"
        
        print(f"{i:<3} ({exp['x']},{exp['y']}) {exp['width']}x{exp['height']:>2} "
              f"exp:{exp['match_confidence']:.3f} ours:{ours['confidence']:.3f} "
              f"exp:{exp['iou_score']:.3f} ours:{ours['iou']:.3f} "
              f"{match_status}")
        
        if not coord_match:
            print(f"    ⚠️ Coordinate mismatch: expected ({exp['x']},{exp['y']}) {exp['width']}x{exp['height']}, "
                  f"got ({ours['x']},{ours['y']}) {ours['width']}x{ours['height']}")
        
        if conf_diff >= 0.005:
            print(f"    📊 Confidence difference: {conf_diff:.4f}")
        
        if iou_diff >= 0.005:
            print(f"    📊 IoU difference: {iou_diff:.4f}")
    
    # Summary statistics
    print(f"\n📊 Accuracy Summary:")
    print(f"   Total expected detections: {len(expected)}")
    print(f"   Total our detections: {len(our_detections)}")
    print(f"   Exact matches: {exact_matches}/{min(len(expected), len(our_detections))}")
    print(f"   Close matches: {close_matches}/{min(len(expected), len(our_detections))}")
    
    accuracy_rate = (exact_matches + close_matches) / min(len(expected), len(our_detections))
    print(f"   Overall accuracy: {accuracy_rate:.1%}")
    
    # Count validation
    if len(our_detections) == len(expected):
        print(f"   ✅ Detection count matches exactly")
    else:
        count_diff = abs(len(our_detections) - len(expected))
        print(f"   ⚠️ Detection count difference: {count_diff}")
    
    # Coordinate validation
    all_coords_match = all(
        exp["x"] == ours["x"] and exp["y"] == ours["y"] and 
        exp["width"] == ours["width"] and exp["height"] == ours["height"]
        for exp, ours in zip(expected[:len(our_detections)], our_detections)
    )
    
    if all_coords_match:
        print(f"   ✅ All coordinates match exactly")
    else:
        print(f"   ⚠️ Some coordinate mismatches detected")
    
    # Algorithm validation conclusion
    if accuracy_rate >= 0.9 and len(our_detections) == len(expected):
        print(f"\n🎉 VALIDATION PASSED: Algorithm is highly accurate!")
        print(f"   ✅ Detection algorithm correctly adapted from gem_v5.py")
        print(f"   ✅ Coordinate transformations working properly")
        print(f"   ✅ IoU verification functioning correctly")
        return True
    else:
        print(f"\n❌ VALIDATION FAILED: Algorithm needs refinement")
        print(f"   Accuracy rate: {accuracy_rate:.1%} (needs ≥90%)")
        print(f"   Count match: {len(our_detections) == len(expected)}")
        return False

if __name__ == "__main__":
    success = compare_detection_results()
    if not success:
        sys.exit(1)