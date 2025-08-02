"""
Main SymbolDetectionEngine class - public interface for detection operations.

This provides the complete detection system including multi-symbol, multi-page
orchestration, storage, and progress tracking capabilities.
"""

from typing import Dict, List, Optional, Callable, Any
from .detection_coordinator import DetectionCoordinator
from .detection_algorithm import SymbolDetectionAlgorithm, DetectionCandidate


class SymbolDetectionEngine:
    """
    Main interface for symbol detection operations.
    
    This class provides the complete detection system including:
    - Multi-symbol, multi-page detection orchestration
    - Real-time progress tracking
    - Result storage and retrieval
    - Detection status management
    """
    
    def __init__(self, doc_id: str, processed_folder: str):
        """
        Initialize the detection engine for a specific document.
        
        Args:
            doc_id: Document identifier
            processed_folder: Path to processed documents folder
        """
        self.doc_id = doc_id
        self.coordinator = DetectionCoordinator(doc_id, processed_folder)
        
        # Keep algorithm accessible for testing/debugging
        self.algorithm = SymbolDetectionAlgorithm()
    
    def run_detection(
        self,
        symbol_ids: Optional[List[str]] = None,
        detection_params: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """
        Execute symbol detection across specified symbols and all pages.
        
        Args:
            symbol_ids: List of symbol IDs to detect (None = all symbols)
            detection_params: Detection algorithm parameters:
                - match_threshold: Template matching threshold (default: 0.30)
                - iou_threshold: IoU verification threshold (default: 0.32) 
                - scale_variance_px: Scale variation in pixels (default: 2)
                - rotation_range: Rotation range in degrees (default: (-1, 1))
                - rotation_step: Rotation step in degrees (default: 1)
            progress_callback: Optional callback function for progress updates
                
        Returns:
            Detection run ID for tracking and loading results
            
        Raises:
            ValueError: If no symbol templates found or invalid parameters
            FileNotFoundError: If required document files missing
        """
        return self.coordinator.run_detection(symbol_ids, detection_params, progress_callback)
    
    def get_detection_progress(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time progress for a detection run.
        
        Args:
            run_id: Detection run ID
            
        Returns:
            Progress data dict or None if run not found
        """
        return self.coordinator.get_detection_progress(run_id)
    
    def load_detection_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load complete detection results for a run.
        
        Args:
            run_id: Detection run ID
            
        Returns:
            Complete detection results dict or None if not found
        """
        return self.coordinator.load_detection_results(run_id)
    
    def update_detection_status(self, run_id: str, updates: List[Dict[str, Any]]):
        """
        Update status of individual detections (accept/reject/modify).
        
        Args:
            run_id: Detection run ID
            updates: List of detection updates, each containing:
                - detectionId: ID of detection to update
                - action: "accept", "reject", or "modify"
                - newCoords: New coordinates if action is "modify"
                - reviewedBy: User who made the review
        """
        return self.coordinator.update_detection_status(run_id, updates)
    
    def list_detection_runs(self) -> List[Dict[str, Any]]:
        """
        List all detection runs for this document.
        
        Returns:
            List of detection run summaries
        """
        return self.coordinator.list_detection_runs()
    
    def delete_detection_run(self, run_id: str) -> bool:
        """
        Delete a detection run and all its data.
        
        Args:
            run_id: Detection run ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return self.coordinator.delete_detection_run(run_id)
    
    # Legacy method for testing/debugging - detect single symbol on single page
    def detect_symbol_on_page(
        self,
        page_pixmap,
        template_image, 
        target_dimensions: Dict[str, int],
        page_metadata,
        detection_params: Optional[Dict] = None
    ) -> List[DetectionCandidate]:
        """
        Detect a single symbol type on a single page (legacy method for testing).
        
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