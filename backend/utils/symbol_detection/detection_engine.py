"""
Simple SymbolDetectionEngine wrapper for milestone 1 testing.

This provides a minimal interface for testing the core detection algorithm
without the full orchestration system (which will be implemented in later milestones).
"""

from typing import Dict, List, Optional
from .detection_algorithm import SymbolDetectionAlgorithm, DetectionCandidate


class SymbolDetectionEngine:
    """
    Minimal detection engine for milestone 1 testing.
    
    This class provides a simple interface to test the core detection algorithm
    without requiring the full multi-symbol, multi-page orchestration system.
    """
    
    def __init__(self):
        self.algorithm = SymbolDetectionAlgorithm()
    
    def detect_symbol_on_page(
        self,
        page_pixmap,
        template_image, 
        target_dimensions: Dict[str, int],
        page_metadata,
        detection_params: Optional[Dict] = None
    ) -> List[DetectionCandidate]:
        """
        Detect a single symbol type on a single page.
        
        This is a direct wrapper around the detection algorithm for testing purposes.
        
        Args:
            page_pixmap: Page image as numpy array at 300 DPI
            template_image: Symbol template as numpy array (grayscale)
            target_dimensions: {"width_pixels_300dpi": X, "height_pixels_300dpi": Y}
            page_metadata: PageMetadata object for coordinate transformation
            detection_params: Optional detection parameters override
            
        Returns:
            List of DetectionCandidate objects with coordinates in PDF space
        """
        return self.algorithm.detect_symbol_on_page(
            page_pixmap, template_image, target_dimensions, page_metadata, detection_params
        )