"""
Adapted gem_v5 algorithm for integration with TimberGem coordinate system.

This module takes the proven detection algorithm from gem_v5.py and adapts it
for use within the TimberGem system, ensuring proper coordinate transformations
and integration with the existing data structures.
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coordinate_mapping import PDFCoordinates, ImageCoordinates, PageMetadata, CoordinateTransformer


@dataclass
class DetectionCandidate:
    """
    Single detection candidate with all metrics and coordinate information.
    
    This represents a detected symbol instance with both the original detection
    coordinates (in the detection image space) and the transformed PDF coordinates.
    """
    candidate_id: int
    image_coords: ImageCoordinates  # Coordinates in detection image space (300 DPI)
    pdf_coords: PDFCoordinates      # Transformed to PDF coordinate space (points)
    match_confidence: float         # Template matching confidence score
    iou_score: float               # IoU verification score
    matched_angle: int             # Rotation angle that produced the match
    template_size: Tuple[int, int] # Template size variation that matched
    status: str = "pending"        # "pending", "accepted", "rejected"


class SymbolDetectionAlgorithm:
    """
    Core detection algorithm adapted from gem_v5.py for TimberGem integration.
    
    This class implements the proven two-stage detection approach:
    1. Template matching with scale and rotation variations
    2. IoU-based verification for shape matching
    
    Key adaptations for TimberGem:
    - Coordinate transformation to PDF space
    - Integration with PageMetadata system
    - Structured output as DetectionCandidate objects
    """
    
    # Detection constants (adapted from gem_v5.py)
    DEFAULT_MATCH_THRESHOLD = 0.30
    DEFAULT_IOU_THRESHOLD = 0.32
    DEFAULT_SCALE_VARIANCE_PX = 2
    DEFAULT_ROTATION_RANGE = (-1, 1)
    DEFAULT_ROTATION_STEP = 1
    CANNY_THRESHOLD_1 = 50
    CANNY_THRESHOLD_2 = 200
    NMS_DISTANCE_THRESHOLD = 100
    DETECTION_DPI = 300  # Use 300 DPI for detection (matches SymbolDimensionCalculator)
    
    def __init__(self):
        """Initialize the detection algorithm with default parameters."""
        pass
    
    def detect_symbol_on_page(
        self, 
        page_pixmap: np.ndarray,
        template_image: np.ndarray, 
        target_dimensions: Dict[str, int],
        page_metadata: PageMetadata,
        detection_params: Optional[Dict] = None
    ) -> List[DetectionCandidate]:
        """
        Detect a single symbol type on a single page using the gem_v5 algorithm.
        
        Args:
            page_pixmap: Page image as numpy array at DETECTION_DPI (300 DPI)
            template_image: Symbol template as numpy array (grayscale)
            target_dimensions: {"width_pixels_300dpi": X, "height_pixels_300dpi": Y}
            page_metadata: Page metadata for coordinate transformation
            detection_params: Override default detection parameters
            
        Returns:
            List of DetectionCandidate objects with coordinates in PDF space
            
        Raises:
            ValueError: If inputs are invalid or incompatible
        """
        
        print(f"🔍 Starting symbol detection on page {page_metadata.page_number}")
        print(f"   Page pixmap shape: {page_pixmap.shape}")
        print(f"   Template shape: {template_image.shape}")
        print(f"   Target dimensions: {target_dimensions}")
        
        # 1. Validate inputs
        self._validate_inputs(page_pixmap, template_image, target_dimensions)
        
        # 2. Setup detection parameters
        params = self._prepare_detection_params(detection_params)
        target_width = target_dimensions["width_pixels_300dpi"]
        target_height = target_dimensions["height_pixels_300dpi"]
        
        print(f"   Detection parameters: {params}")
        print(f"   Target size: {target_width}x{target_height} pixels")
        
        # 3. Generate template variations (Stage 1 preparation from gem_v5.py)
        print("   🔄 Generating template variations...")
        template_variations = self._generate_template_variations(
            template_image, target_width, target_height, params
        )
        print(f"   Generated {len(template_variations)} template variations")
        
        # 4. Run candidate generation (Stage 1 from gem_v5.py)
        print("   🎯 Running candidate generation...")
        candidates = self._generate_candidates(
            page_pixmap, template_variations, params["match_threshold"]
        )
        print(f"   Found {len(candidates)} initial candidates")
        
        # 5. IoU verification (Stage 2 from gem_v5.py)
        print("   ✅ Running IoU verification...")
        verified_candidates = self._verify_candidates_iou(
            page_pixmap, candidates, template_variations, params["iou_threshold"]
        )
        print(f"   Verified {len(verified_candidates)} candidates")
        
        # 6. Transform coordinates to PDF space
        print("   📐 Transforming coordinates to PDF space...")
        detection_candidates = self._transform_to_pdf_coordinates(
            verified_candidates, page_metadata
        )
        print(f"   ✅ Detection complete: {len(detection_candidates)} final detections")
        
        return detection_candidates
    
    def _validate_inputs(self, page_pixmap: np.ndarray, template_image: np.ndarray, target_dimensions: Dict):
        """Validate input parameters for detection"""
        if page_pixmap is None or page_pixmap.size == 0:
            raise ValueError("Page pixmap is empty or None")
        
        if template_image is None or template_image.size == 0:
            raise ValueError("Template image is empty or None")
        
        if not isinstance(target_dimensions, dict):
            raise ValueError("Target dimensions must be a dictionary")
        
        required_keys = ["width_pixels_300dpi", "height_pixels_300dpi"]
        for key in required_keys:
            if key not in target_dimensions:
                raise ValueError(f"Target dimensions missing required key: {key}")
            if not isinstance(target_dimensions[key], (int, float)) or target_dimensions[key] <= 0:
                raise ValueError(f"Target dimension {key} must be a positive number")
    
    def _prepare_detection_params(self, detection_params: Optional[Dict]) -> Dict:
        """Prepare detection parameters with defaults"""
        params = {
            "match_threshold": self.DEFAULT_MATCH_THRESHOLD,
            "iou_threshold": self.DEFAULT_IOU_THRESHOLD,
            "scale_variance_px": self.DEFAULT_SCALE_VARIANCE_PX,
            "rotation_range": self.DEFAULT_ROTATION_RANGE,
            "rotation_step": self.DEFAULT_ROTATION_STEP
        }
        if detection_params:
            params.update(detection_params)
        return params
    
    def _generate_template_variations(
        self, template_image: np.ndarray, target_width: int, target_height: int, params: Dict
    ) -> Dict[Tuple[int, int, int], np.ndarray]:
        """
        Generate scaled and rotated template variations.
        
        This is adapted from gem_v5.py lines 135-155, generating all combinations
        of scale and rotation variations for robust template matching.
        """
        variations = {}
        
        # Generate scale variations (from gem_v5.py generate_scale_variations)
        variance_px = params["scale_variance_px"]
        scale_variations = []
        for v in range(-variance_px, variance_px + 1):
            new_width = target_width + v
            new_height = target_height + v
            if new_width > 0 and new_height > 0:
                scale_variations.append((new_width, new_height))
        
        print(f"     Scale variations: {scale_variations}")
        
        # Generate rotation and edge map variations for each scale
        for scale_width, scale_height in scale_variations:
            for angle in range(
                params["rotation_range"][0], 
                params["rotation_range"][1] + 1, 
                params["rotation_step"]
            ):
                try:
                    # Scale template (from gem_v5.py line 143)
                    scaled_template = cv2.resize(template_image, (scale_width, scale_height))
                    
                    # Rotate template (from gem_v5.py lines 144-149)
                    h, w = scaled_template.shape[:2]
                    center = (w // 2, h // 2)
                    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated_template = cv2.warpAffine(
                        scaled_template, rot_mat, (w, h), borderValue=255
                    )
                    
                    # Generate edge map for template matching (from gem_v5.py lines 150-152)
                    template_edges = cv2.Canny(
                        rotated_template, self.CANNY_THRESHOLD_1, self.CANNY_THRESHOLD_2
                    )
                    
                    # Store with (width, height, angle) as key
                    variations[(scale_width, scale_height, angle)] = template_edges
                    
                except Exception as e:
                    print(f"     ⚠️ Failed to create variation {scale_width}x{scale_height}@{angle}°: {e}")
                    continue
        
        print(f"     Successfully created {len(variations)} template variations")
        return variations
    
    def _generate_candidates(
        self, source_image: np.ndarray, template_variations: Dict, match_threshold: float
    ) -> List[Dict]:
        """
        Generate detection candidates using template matching.
        
        This implements Stage 1 from gem_v5.py (lines 157-172), running template
        matching for all variations and collecting candidates above the threshold.
        """
        # Generate source edge map (from gem_v5.py line 129)
        source_edges = cv2.Canny(source_image, self.CANNY_THRESHOLD_1, self.CANNY_THRESHOLD_2)
        all_detections_raw = []
        
        # Run template matching for each variation (from gem_v5.py lines 157-169)
        for (width, height, angle), template_edges in template_variations.items():
            try:
                # Template matching (from gem_v5.py lines 157-158)
                result = cv2.matchTemplate(source_edges, template_edges, cv2.TM_CCOEFF_NORMED)
                
                # Find locations above threshold (from gem_v5.py lines 160-169)
                locations = np.where(result >= match_threshold)
                for pt in zip(*locations[::-1]):  # Note: locations are (y,x), we want (x,y)
                    all_detections_raw.append({
                        "point": pt,
                        "confidence": float(result[pt[1], pt[0]]),  # pt is (x,y), result is [y,x]
                        "size": (width, height),
                        "angle": angle,
                    })
                    
            except Exception as e:
                print(f"     ⚠️ Template matching failed for {width}x{height}@{angle}°: {e}")
                continue
        
        print(f"     Raw detections: {len(all_detections_raw)}")
        
        # Group close points (NMS from gem_v5.py lines 171-172)
        unique_candidates = self._group_close_points(all_detections_raw, self.NMS_DISTANCE_THRESHOLD)
        print(f"     After NMS: {len(unique_candidates)} unique candidates")
        
        return unique_candidates
    
    def _verify_candidates_iou(
        self, source_image: np.ndarray, candidates: List[Dict], 
        template_variations: Dict, iou_threshold: float
    ) -> List[Dict]:
        """
        Verify candidates using IoU scoring.
        
        This implements Stage 2 from gem_v5.py (lines 174-243), using Intersection
        over Union to verify that detected regions actually match the template shape.
        """
        source_edges = cv2.Canny(source_image, self.CANNY_THRESHOLD_1, self.CANNY_THRESHOLD_2)
        verified_candidates = []
        
        for i, candidate in enumerate(candidates):
            try:
                x, y = candidate["point"]
                w, h = candidate["size"]
                angle = candidate["angle"]
                
                # Get matching template edges (from gem_v5.py line 188)
                template_edges = template_variations[(w, h, angle)]
                
                # Extract source region (from gem_v5.py line 191)
                source_edge_clip = source_edges[y:y+h, x:x+w]
                
                # Calculate IoU (from gem_v5.py lines 194-196)
                is_verified, iou_score = self._verify_shape_iou(
                    source_edge_clip, template_edges, iou_threshold
                )
                
                if is_verified:
                    verified_candidates.append({
                        "candidate_id": i,
                        "x": x, "y": y, "width": w, "height": h,
                        "match_confidence": candidate["confidence"],
                        "iou_score": iou_score,
                        "matched_angle": angle,
                        "status": "pending"
                    })
                    print(f"     ✅ Candidate {i}: conf={candidate['confidence']:.3f}, IoU={iou_score:.3f}")
                else:
                    print(f"     ❌ Candidate {i}: conf={candidate['confidence']:.3f}, IoU={iou_score:.3f} (rejected)")
                    
            except Exception as e:
                print(f"     ⚠️ IoU verification failed for candidate {i}: {e}")
                continue
        
        return verified_candidates
    
    def _verify_shape_iou(self, source_clip: np.ndarray, template_edges: np.ndarray, threshold: float) -> Tuple[bool, float]:
        """
        Calculate Intersection over Union for shape verification.
        
        This is directly from gem_v5.py lines 58-78, implementing the IoU
        calculation that verifies shape similarity beyond just template matching.
        """
        if source_clip.shape != template_edges.shape:
            return False, 0.0
        
        # Convert to boolean arrays for logical operations
        source_bool = source_clip > 0
        template_bool = template_edges > 0
        
        intersection = np.sum(np.logical_and(source_bool, template_bool))
        union = np.sum(np.logical_or(source_bool, template_bool))
        
        if union == 0:
            return False, 0.0
        
        iou_score = intersection / union
        return iou_score >= threshold, iou_score
    
    def _group_close_points(self, points_data: List[Dict], min_distance: float) -> List[Dict]:
        """
        Group nearby detections using Non-Maximum Suppression.
        
        This is directly from gem_v5.py lines 82-97, removing duplicate detections
        that are too close to each other (keeping the highest confidence one).
        """
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
    
    def _transform_to_pdf_coordinates(
        self, candidates: List[Dict], page_metadata: PageMetadata
    ) -> List[DetectionCandidate]:
        """
        Transform detection coordinates to PDF space using the coordinate mapping system.
        
        This is the key integration point that ensures detected symbols are properly
        positioned in the PDF coordinate space that serves as TimberGem's single
        source of truth.
        """
        transformer = CoordinateTransformer(page_metadata)
        detection_candidates = []
        
        for candidate in candidates:
            try:
                # Create image coordinates for the detection at 300 DPI
                detection_image_coords = ImageCoordinates(
                    left=candidate["x"],
                    top=candidate["y"], 
                    width=candidate["width"],
                    height=candidate["height"],
                    dpi=self.DETECTION_DPI  # 300 DPI
                )
                
                # Transform to PDF coordinates using the coordinate transformer
                # The transformer handles the conversion from 300 DPI detection space
                # to PDF points space automatically
                pdf_coords = transformer.image_to_pdf(detection_image_coords)
                
                # Create detection candidate object
                detection_candidate = DetectionCandidate(
                    candidate_id=candidate["candidate_id"],
                    image_coords=detection_image_coords,
                    pdf_coords=pdf_coords,
                    match_confidence=candidate["match_confidence"],
                    iou_score=candidate["iou_score"],
                    matched_angle=candidate["matched_angle"],
                    template_size=(candidate["width"], candidate["height"]),
                    status=candidate["status"]
                )
                
                detection_candidates.append(detection_candidate)
                
                print(f"     📐 Transformed candidate {candidate['candidate_id']}:")
                print(f"        Detection coords: ({candidate['x']}, {candidate['y']}) {candidate['width']}x{candidate['height']} @ 300 DPI")
                print(f"        PDF coords: ({pdf_coords.left:.2f}, {pdf_coords.top:.2f}) {pdf_coords.width:.2f}x{pdf_coords.height:.2f} points")
                
            except Exception as e:
                print(f"     ❌ Failed to transform candidate {candidate.get('candidate_id', 'unknown')}: {e}")
                continue
        
        return detection_candidates