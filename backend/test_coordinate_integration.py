"""
Unit tests for coordinate transformation integration in the detection algorithm.

This test validates that our detection algorithm properly integrates with
the TimberGem coordinate mapping system and produces accurate PDF coordinates.
"""

import sys
import os
import numpy as np
import unittest

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.symbol_detection.detection_algorithm import SymbolDetectionAlgorithm, DetectionCandidate
from utils.coordinate_mapping import PageMetadata, ImageCoordinates, PDFCoordinates, CoordinateTransformer


class TestCoordinateIntegration(unittest.TestCase):
    """Test coordinate transformation integration in detection algorithm"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.algorithm = SymbolDetectionAlgorithm()
        
        # Create realistic page metadata
        self.page_metadata = PageMetadata(
            page_number=1,
            pdf_width_points=1224.0,  # Large page width (17 inches)
            pdf_height_points=1584.0,  # Large page height (22 inches)
            pdf_rotation_degrees=0,
            image_width_pixels=3400,  # 1224 points * 200 DPI / 72 points/inch ≈ 3400
            image_height_pixels=4400,  # 1584 points * 200 DPI / 72 points/inch ≈ 4400
            image_dpi=200,  # Standard DPI
            high_res_image_width_pixels=5100,  # 1224 points * 300 DPI / 72 points/inch ≈ 5100
            high_res_image_height_pixels=6600,  # 1584 points * 300 DPI / 72 points/inch ≈ 6600
            high_res_dpi=300  # High res DPI for detection
        )
        
        self.transformer = CoordinateTransformer(self.page_metadata)
    
    def test_page_metadata_setup(self):
        """Test that page metadata is set up correctly"""
        self.assertEqual(self.page_metadata.page_number, 1)
        self.assertEqual(self.page_metadata.pdf_width_points, 1224.0)
        self.assertEqual(self.page_metadata.high_res_dpi, 300)
        
    def test_coordinate_transformer_creation(self):
        """Test that coordinate transformer is created correctly"""
        self.assertIsNotNone(self.transformer)
        self.assertEqual(self.transformer.page_metadata.page_number, 1)
        
    def test_detection_coordinate_transformation(self):
        """Test that detection coordinates are properly transformed to PDF space"""
        
        # Simulate a detection at image coordinates (1000, 1500) at 300 DPI
        test_detection = {
            "candidate_id": 0,
            "x": 1000,
            "y": 1500,
            "width": 96,
            "height": 96,
            "match_confidence": 0.8,
            "iou_score": 0.4,
            "matched_angle": 0,
            "status": "pending"
        }
        
        # Transform using our algorithm's method
        candidates = self.algorithm._transform_to_pdf_coordinates([test_detection], self.page_metadata)
        
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        
        # Verify the detection candidate structure
        self.assertIsInstance(candidate, DetectionCandidate)
        self.assertEqual(candidate.candidate_id, 0)
        self.assertEqual(candidate.match_confidence, 0.8)
        self.assertEqual(candidate.iou_score, 0.4)
        
        # Verify image coordinates
        self.assertEqual(candidate.image_coords.left, 1000)
        self.assertEqual(candidate.image_coords.top, 1500)
        self.assertEqual(candidate.image_coords.width, 96)
        self.assertEqual(candidate.image_coords.height, 96)
        self.assertEqual(candidate.image_coords.dpi, 300)
        
        # Verify PDF coordinates are reasonable
        self.assertGreater(candidate.pdf_coords.left, 0)
        self.assertGreater(candidate.pdf_coords.top, 0)
        self.assertGreater(candidate.pdf_coords.width, 0)
        self.assertGreater(candidate.pdf_coords.height, 0)
        
        # Test round-trip transformation
        back_transformed = self.transformer.pdf_to_image(candidate.pdf_coords)
        
        # Should be very close (within 1-2 pixels due to rounding)
        self.assertLessEqual(abs(back_transformed.left - candidate.image_coords.left), 2)
        self.assertLessEqual(abs(back_transformed.top - candidate.image_coords.top), 2)
        self.assertLessEqual(abs(back_transformed.width - candidate.image_coords.width), 2)
        self.assertLessEqual(abs(back_transformed.height - candidate.image_coords.height), 2)
        
    def test_multiple_detections_transformation(self):
        """Test transformation of multiple detections"""
        
        test_detections = [
            {"candidate_id": 0, "x": 100, "y": 200, "width": 50, "height": 50, 
             "match_confidence": 0.9, "iou_score": 0.5, "matched_angle": 0, "status": "pending"},
            {"candidate_id": 1, "x": 1000, "y": 1500, "width": 96, "height": 96, 
             "match_confidence": 0.8, "iou_score": 0.4, "matched_angle": 0, "status": "pending"},
            {"candidate_id": 2, "x": 2000, "y": 2500, "width": 80, "height": 80, 
             "match_confidence": 0.7, "iou_score": 0.3, "matched_angle": 0, "status": "pending"},
        ]
        
        candidates = self.algorithm._transform_to_pdf_coordinates(test_detections, self.page_metadata)
        
        self.assertEqual(len(candidates), 3)
        
        # Check that all candidates have proper structure
        for i, candidate in enumerate(candidates):
            self.assertEqual(candidate.candidate_id, i)
            self.assertTrue(hasattr(candidate.pdf_coords, 'left'))
            self.assertTrue(hasattr(candidate.pdf_coords, 'top'))
            self.assertTrue(hasattr(candidate.image_coords, 'left'))
            self.assertTrue(hasattr(candidate.image_coords, 'dpi'))
            
            # Check that PDF coordinates are within reasonable bounds
            self.assertGreaterEqual(candidate.pdf_coords.left, 0)
            self.assertGreaterEqual(candidate.pdf_coords.top, 0)
            self.assertLessEqual(candidate.pdf_coords.left + candidate.pdf_coords.width, 
                               self.page_metadata.pdf_width_points)
            self.assertLessEqual(candidate.pdf_coords.top + candidate.pdf_coords.height, 
                               self.page_metadata.pdf_height_points)
    
    def test_edge_coordinates(self):
        """Test transformation of coordinates at page edges"""
        
        # Test coordinates at corners and edges (within valid bounds)
        edge_cases = [
            {"candidate_id": 0, "x": 0, "y": 0, "width": 50, "height": 50},  # Top-left corner
            {"candidate_id": 1, "x": 2450, "y": 0, "width": 50, "height": 50},  # Top-right corner
            {"candidate_id": 2, "x": 0, "y": 3200, "width": 50, "height": 50},  # Bottom-left corner
            {"candidate_id": 3, "x": 2450, "y": 3200, "width": 50, "height": 50},  # Bottom-right corner
        ]
        
        for edge_case in edge_cases:
            edge_case.update({
                "match_confidence": 0.8, "iou_score": 0.4, 
                "matched_angle": 0, "status": "pending"
            })
        
        candidates = self.algorithm._transform_to_pdf_coordinates(edge_cases, self.page_metadata)
        
        # All edge cases should transform successfully
        self.assertEqual(len(candidates), 4)
        
        for candidate in candidates:
            # PDF coordinates should be within page bounds
            self.assertGreaterEqual(candidate.pdf_coords.left, 0)
            self.assertGreaterEqual(candidate.pdf_coords.top, 0)
            self.assertLessEqual(candidate.pdf_coords.left + candidate.pdf_coords.width, 
                               self.page_metadata.pdf_width_points + 10)  # Small tolerance
            self.assertLessEqual(candidate.pdf_coords.top + candidate.pdf_coords.height, 
                               self.page_metadata.pdf_height_points + 10)  # Small tolerance
    
    def test_detection_params_validation(self):
        """Test validation of detection parameters"""
        
        # Valid parameters
        valid_params = {
            "match_threshold": 0.3,
            "iou_threshold": 0.25,
            "scale_variance_px": 2
        }
        
        processed_params = self.algorithm._prepare_detection_params(valid_params)
        self.assertEqual(processed_params["match_threshold"], 0.3)
        self.assertEqual(processed_params["iou_threshold"], 0.25)
        self.assertEqual(processed_params["scale_variance_px"], 2)
        
        # Test defaults
        default_params = self.algorithm._prepare_detection_params(None)
        self.assertEqual(default_params["match_threshold"], SymbolDetectionAlgorithm.DEFAULT_MATCH_THRESHOLD)
        self.assertEqual(default_params["iou_threshold"], SymbolDetectionAlgorithm.DEFAULT_IOU_THRESHOLD)
        
    def test_input_validation(self):
        """Test input validation for the detection algorithm"""
        
        # Valid inputs
        page_pixmap = np.zeros((1000, 1000), dtype=np.uint8)
        template_image = np.zeros((50, 50), dtype=np.uint8)
        target_dimensions = {"width_pixels_300dpi": 50, "height_pixels_300dpi": 50}
        
        # Should not raise any exceptions
        self.algorithm._validate_inputs(page_pixmap, template_image, target_dimensions)
        
        # Invalid inputs
        with self.assertRaises(ValueError):
            self.algorithm._validate_inputs(None, template_image, target_dimensions)
        
        with self.assertRaises(ValueError):
            self.algorithm._validate_inputs(page_pixmap, None, target_dimensions)
        
        with self.assertRaises(ValueError):
            self.algorithm._validate_inputs(page_pixmap, template_image, {})
        
        with self.assertRaises(ValueError):
            invalid_dimensions = {"width_pixels_300dpi": -10, "height_pixels_300dpi": 50}
            self.algorithm._validate_inputs(page_pixmap, template_image, invalid_dimensions)


class TestDetectionCandidate(unittest.TestCase):
    """Test the DetectionCandidate data structure"""
    
    def test_detection_candidate_creation(self):
        """Test creation of DetectionCandidate objects"""
        
        image_coords = ImageCoordinates(100, 200, 50, 50, 300)
        pdf_coords = PDFCoordinates(72.0, 144.0, 36.0, 36.0)
        
        candidate = DetectionCandidate(
            candidate_id=1,
            image_coords=image_coords,
            pdf_coords=pdf_coords,
            match_confidence=0.85,
            iou_score=0.42,
            matched_angle=0,
            template_size=(50, 50),
            status="pending"
        )
        
        self.assertEqual(candidate.candidate_id, 1)
        self.assertEqual(candidate.match_confidence, 0.85)
        self.assertEqual(candidate.iou_score, 0.42)
        self.assertEqual(candidate.matched_angle, 0)
        self.assertEqual(candidate.template_size, (50, 50))
        self.assertEqual(candidate.status, "pending")
        self.assertIsInstance(candidate.image_coords, ImageCoordinates)
        self.assertIsInstance(candidate.pdf_coords, PDFCoordinates)


if __name__ == "__main__":
    print("🧪 Running Coordinate Integration Tests")
    print("=" * 60)
    
    # Run the tests
    unittest.main(verbosity=2)