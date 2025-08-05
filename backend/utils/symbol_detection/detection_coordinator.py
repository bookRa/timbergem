"""
Detection coordinator for orchestrating multi-symbol, multi-page detection operations.

This module manages the complex orchestration of running symbol detection across
multiple symbols and pages, integrating with storage and progress tracking systems.
"""

import os
import cv2
import json
import fitz
import numpy as np
from typing import Dict, List, Optional, Callable, Any
from PIL import Image

from .detection_algorithm import SymbolDetectionAlgorithm
from .detection_storage import DetectionStorage
from .detection_progress import DetectionProgress
from ..coordinate_mapping import PageMetadata


class DetectionCoordinator:
    """
    Orchestrates symbol detection across multiple symbols and pages.
    
    This class manages the complex workflow of:
    1. Loading symbol templates and metadata
    2. Processing each symbol across all pages
    3. Coordinating with storage and progress systems
    4. Handling errors and recovery
    """
    
    def __init__(self, doc_id: str, processed_folder: str):
        """
        Initialize the detection coordinator.
        
        Args:
            doc_id: Document identifier
            processed_folder: Path to processed documents folder
        """
        self.doc_id = doc_id
        self.doc_dir = os.path.join(processed_folder, doc_id)
        self.algorithm = SymbolDetectionAlgorithm()
        self.storage = DetectionStorage(self.doc_dir)
        
        # Validate document directory
        if not os.path.exists(self.doc_dir):
            raise FileNotFoundError(f"Document directory not found: {self.doc_dir}")
        
        print(f"🎭 Detection coordinator initialized for document {doc_id}")
    
    def run_detection(
        self, 
        symbol_ids: Optional[List[str]] = None,
        detection_params: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """
        Run detection for specified symbols across all pages.
        
        Args:
            symbol_ids: List of symbol IDs to detect (None = all symbols)
            detection_params: Override default detection parameters
            progress_callback: Optional callback for progress updates
            
        Returns:
            Detection run ID for tracking results
            
        Raises:
            ValueError: If no symbol templates found or invalid parameters
            FileNotFoundError: If required document files missing
        """
        
        print(f"🚀 Starting detection run for document {self.doc_id}")
        
        # 1. Load and validate symbol metadata
        symbols_metadata = self._load_symbols_metadata()
        if not symbols_metadata:
            raise ValueError("No symbol templates found - run Symbol Annotation first")
        
        # Filter symbols if specific IDs requested
        if symbol_ids:
            symbols_to_process = {
                sid: self._find_symbol_by_id(symbols_metadata["symbols"], sid)
                for sid in symbol_ids
            }
            # Remove None values (invalid symbol IDs)
            symbols_to_process = {k: v for k, v in symbols_to_process.items() if v is not None}
            
            if not symbols_to_process:
                raise ValueError(f"No valid symbols found for IDs: {symbol_ids}")
        else:
            symbols_to_process = {s["id"]: s for s in symbols_metadata["symbols"]}
        
        print(f"📊 Processing {len(symbols_to_process)} symbols:")
        for symbol_id, symbol in symbols_to_process.items():
            print(f"   - {symbol['name']} ({symbol_id})")
        
        # 2. Load page metadata and validate
        page_metadata = self._load_page_metadata()
        total_pages = len(page_metadata)
        
        if total_pages == 0:
            raise ValueError("No page metadata found")
        
        print(f"📄 Processing across {total_pages} pages")
        
        # 3. Create detection run
        run_params = {
            "detection_params": detection_params or {},
            "symbol_ids": list(symbols_to_process.keys()),
            "total_symbols": len(symbols_to_process),
            "total_pages": total_pages,
            "doc_id": self.doc_id
        }
        
        run_id = self.storage.create_detection_run(run_params)
        run_dir = os.path.join(self.storage.detections_dir, f"run_{run_id}")
        
        # 4. Initialize progress tracking
        symbol_names = [s["name"] for s in symbols_to_process.values()]
        progress = DetectionProgress(run_id, run_dir)
        progress.start_detection(len(symbols_to_process), total_pages, symbol_names)
        
        try:
            # 5. Load PDF document once for efficiency
            pdf_document = self._load_pdf_document()
            
            # 6. Process each symbol across all pages
            for symbol_index, (symbol_id, symbol_metadata) in enumerate(symbols_to_process.items()):
                try:
                    symbol_name = symbol_metadata["name"]
                    progress.start_symbol_processing(symbol_name, symbol_index, len(symbols_to_process))
                    
                    # Load symbol template
                    template_image = self._load_symbol_template(symbol_metadata)
                    
                    # Use actual template image dimensions as target (like gem_v5.py)
                    # This preserves template detail and matches gem_v5.py's approach
                    template_height, template_width = template_image.shape[:2]
                    actual_template_dimensions = {
                        "width_pixels_300dpi": template_width,
                        "height_pixels_300dpi": template_height
                    }
                    print(f"   📏 Using actual template dimensions: {template_width}x{template_height} pixels (gem_v5.py approach)")
                    print(f"   📊 Contour-detected dimensions were: {symbol_metadata['symbol_template_dimensions']['width_pixels_300dpi']}x{symbol_metadata['symbol_template_dimensions']['height_pixels_300dpi']} pixels")
                    
                    # Detect symbol across all pages using actual template dimensions
                    symbol_detections = self._detect_symbol_across_pages(
                        pdf_document, template_image, symbol_metadata, page_metadata, 
                        detection_params, progress, actual_template_dimensions
                    )
                    
                    # Save symbol detection results
                    total_detections = sum(len(detections) for detections in symbol_detections.values())
                    self.storage.save_symbol_detections(
                        run_id, symbol_id, symbol_metadata, symbol_detections
                    )
                    
                    # Create debug overlay image (like gem_v5.py)
                    if total_detections > 0:
                        self._create_debug_overlay(
                            pdf_document, symbol_detections, symbol_metadata, run_id, symbol_id
                        )
                    
                    progress.complete_symbol_processing(symbol_name, total_detections)
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(progress.get_progress_summary())
                        
                except Exception as e:
                    error_msg = f"Failed to process symbol {symbol_metadata.get('name', symbol_id)}: {str(e)}"
                    progress.add_error(error_msg, {"symbolId": symbol_id, "symbolName": symbol_metadata.get('name')})
                    print(f"❌ {error_msg}")
                    
                    # Continue with other symbols instead of failing entire run
                    continue
            
            # 7. Complete detection successfully
            progress.complete_detection(success=True)
            self.storage.complete_detection_run(run_id, success=True)
            pdf_document.close()
            
            print(f"🎉 Detection run {run_id} completed successfully")
            return run_id
            
        except Exception as e:
            # Handle critical errors that stop the entire run
            error_msg = f"Detection run failed: {str(e)}"
            progress.add_error(error_msg)
            progress.complete_detection(success=False, final_message=error_msg)
            self.storage.complete_detection_run(run_id, success=False, final_message=error_msg)
            print(f"💥 Critical error: {error_msg}")
            raise
    
    def _detect_symbol_across_pages(
        self, 
        pdf_document: fitz.Document, 
        template_image: np.ndarray, 
        symbol_metadata: Dict[str, Any], 
        page_metadata: Dict[int, PageMetadata], 
        detection_params: Optional[Dict[str, Any]],
        progress: DetectionProgress,
        template_dimensions: Optional[Dict[str, int]] = None
    ) -> Dict[int, List]:
        """
        Detect a single symbol across all pages.
        
        Args:
            pdf_document: PyMuPDF document object
            template_image: Symbol template as numpy array
            symbol_metadata: Symbol metadata including dimensions
            page_metadata: Page metadata for coordinate transformations
            detection_params: Detection algorithm parameters
            progress: Progress tracker
            template_dimensions: Optional override for template dimensions (uses actual template size)
        Returns:
            Dict mapping page numbers to lists of DetectionCandidate objects
        """
        
        detections_by_page = {}
        symbol_name = symbol_metadata["name"]
        
        print(f"🔍 Detecting '{symbol_name}' across {len(page_metadata)} pages")
        
        for page_num, page_meta in page_metadata.items():
            try:
                # Load page pixmap at detection DPI (300 DPI)
                page_pixmap = self._load_page_pixmap(pdf_document, page_num - 1)  # Convert to 0-based
                
                # Use actual template dimensions if provided, otherwise fall back to contour-detected dimensions
                dimensions_to_use = template_dimensions or symbol_metadata["symbol_template_dimensions"]
                
                # Run detection on this page
                page_detections = self.algorithm.detect_symbol_on_page(
                    page_pixmap, 
                    template_image, 
                    dimensions_to_use,
                    page_meta, 
                    detection_params
                )
                
                # Store detections if any found
                if page_detections:
                    detections_by_page[page_num] = page_detections
                    print(f"   📍 Page {page_num}: {len(page_detections)} detections")
                else:
                    print(f"   📍 Page {page_num}: No detections")
                
                # Update progress
                progress.update_page_progress(page_num, len(page_detections), len(page_metadata))
                progress.complete_step()
                
            except Exception as e:
                error_msg = f"Failed to process page {page_num} for symbol '{symbol_name}': {str(e)}"
                progress.add_error(error_msg, {
                    "pageNum": page_num, 
                    "symbolId": symbol_metadata["id"],
                    "symbolName": symbol_name
                })
                print(f"❌ {error_msg}")
                
                # Continue with other pages
                continue
        
        total_detections = sum(len(detections) for detections in detections_by_page.values())
        pages_with_detections = len(detections_by_page)
        
        print(f"✅ Symbol '{symbol_name}' complete: {total_detections} detections across {pages_with_detections} pages")
        
        return detections_by_page
    
    def _load_symbols_metadata(self) -> Optional[Dict[str, Any]]:
        """Load symbols metadata from file"""
        metadata_file = os.path.join(self.doc_dir, "symbols", "symbols_metadata.json")
        if not os.path.exists(metadata_file):
            print(f"⚠️ Symbols metadata not found: {metadata_file}")
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            print(f"📋 Loaded metadata for {len(metadata.get('symbols', []))} symbols")
            return metadata
            
        except Exception as e:
            print(f"❌ Failed to load symbols metadata: {e}")
            return None
    
    def _find_symbol_by_id(self, symbols_list: List[Dict[str, Any]], symbol_id: str) -> Optional[Dict[str, Any]]:
        """Find symbol metadata by ID"""
        for symbol in symbols_list:
            if symbol.get("id") == symbol_id:
                return symbol
        return None
    
    def _load_page_metadata(self) -> Dict[int, PageMetadata]:
        """Load page metadata for coordinate transformations"""
        metadata_file = os.path.join(self.doc_dir, "page_metadata.json")
        
        if not os.path.exists(metadata_file):
            raise FileNotFoundError(f"Page metadata not found: {metadata_file}")
        
        try:
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
            
            page_metadata = {}
            for page_num, page_data in metadata_dict["pages"].items():
                page_metadata[int(page_num)] = PageMetadata.from_dict(page_data)
            
            print(f"📐 Loaded page metadata for {len(page_metadata)} pages")
            return page_metadata
            
        except Exception as e:
            print(f"❌ Failed to load page metadata: {e}")
            raise
    
    def _load_pdf_document(self) -> fitz.Document:
        """Load the original PDF document"""
        pdf_path = os.path.join(self.doc_dir, "original.pdf")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Original PDF not found: {pdf_path}")
        
        try:
            pdf_document = fitz.open(pdf_path)
            print(f"📄 Loaded PDF document: {len(pdf_document)} pages")
            return pdf_document
            
        except Exception as e:
            print(f"❌ Failed to load PDF document: {e}")
            raise
    
    def _load_symbol_template(self, symbol_metadata: Dict[str, Any]) -> np.ndarray:
        """
        Load symbol template image as numpy array.
        
        Args:
            symbol_metadata: Symbol metadata containing relative path
            
        Returns:
            Template image as grayscale numpy array
        """
        template_path = os.path.join(self.doc_dir, symbol_metadata["relative_path"])
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Symbol template not found: {template_path}")
        
        try:
            # Load using PIL then convert to numpy
            template_pil = Image.open(template_path)
            template_array = np.array(template_pil)
            
            # Convert to grayscale if needed
            if len(template_array.shape) == 3:
                template_gray = cv2.cvtColor(template_array, cv2.COLOR_RGB2GRAY)
            else:
                template_gray = template_array
            
            print(f"🖼️ Loaded template: {template_path} ({template_gray.shape})")
            return template_gray
            
        except Exception as e:
            print(f"❌ Failed to load symbol template: {e}")
            raise
    
    def _load_page_pixmap(self, pdf_document: fitz.Document, page_index: int) -> np.ndarray:
        """
        Load page pixmap at detection DPI (300 DPI) as numpy array.
        
        Args:
            pdf_document: PyMuPDF document object
            page_index: 0-based page index
            
        Returns:
            Page image as grayscale numpy array
        """
        try:
            page = pdf_document.load_page(page_index)
            
            # Generate pixmap at 300 DPI for detection
            pix = page.get_pixmap(dpi=self.algorithm.DETECTION_DPI)
            
            # Convert to numpy array
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h, pix.w, pix.n
            )
            
            # Convert to grayscale if needed (detection algorithm expects grayscale)
            if img_data.shape[2] > 1:
                img_gray = cv2.cvtColor(img_data, cv2.COLOR_RGB2GRAY)
            else:
                img_gray = img_data.reshape(img_data.shape[0], img_data.shape[1])
            
            return img_gray
            
        except Exception as e:
            print(f"❌ Failed to load page pixmap for page {page_index + 1}: {e}")
            raise
    
    def get_detection_progress(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time progress for a detection run.
        
        Args:
            run_id: Detection run ID
            
        Returns:
            Progress data or None if run not found
        """
        run_dir = os.path.join(self.storage.detections_dir, f"run_{run_id}")
        progress_file = os.path.join(run_dir, "progress.json")
        
        if not os.path.exists(progress_file):
            return None
        
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load progress: {e}")
            return None
    
    def load_detection_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load complete detection results for a run.
        
        Args:
            run_id: Detection run ID
            
        Returns:
            Complete detection results or None if not found
        """
        return self.storage.load_detection_run(run_id)
    
    def update_detection_status(self, run_id: str, updates: List[Dict[str, Any]]):
        """
        Update status of individual detections.
        
        Args:
            run_id: Detection run ID
            updates: List of detection status updates
        """
        return self.storage.update_detection_status(run_id, updates)
    
    def list_detection_runs(self) -> List[Dict[str, Any]]:
        """
        List all detection runs for this document.
        
        Returns:
            List of detection run summaries
        """
        return self.storage.list_detection_runs()
    
    def delete_detection_run(self, run_id: str) -> bool:
        """
        Delete a detection run and all its data.
        
        Args:
            run_id: Detection run ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return self.storage.delete_detection_run(run_id)
    
    def _create_debug_overlay(
        self, 
        pdf_document: fitz.Document, 
        symbol_detections: Dict[int, List], 
        symbol_metadata: Dict[str, Any], 
        run_id: str, 
        symbol_id: str
    ):
        """
        Create debug overlay image showing detected symbols (like gem_v5.py).
        
        Args:
            pdf_document: PyMuPDF document object
            symbol_detections: Detection results by page
            symbol_metadata: Symbol metadata
            run_id: Detection run ID
            symbol_id: Symbol ID
        """
        try:
            import cv2
            import numpy as np
            
            symbol_name = symbol_metadata["name"]
            print(f"🎨 Creating debug overlay for {symbol_name}")
            
            # Create overlay for each page that has detections
            for page_num, detections in symbol_detections.items():
                if not detections:
                    continue
                    
                # Load page pixmap
                page_pixmap = self._load_page_pixmap(pdf_document, page_num - 1)
                
                # Convert to BGR for OpenCV
                overlay_image = cv2.cvtColor(page_pixmap, cv2.COLOR_GRAY2BGR)
                
                # Draw detection rectangles
                for detection in detections:
                    x = detection.image_coords.left
                    y = detection.image_coords.top  
                    w = detection.image_coords.width
                    h = detection.image_coords.height
                    
                    # Color based on confidence (like gem_v5.py)
                    if detection.iou_score >= 0.5:
                        color = (0, 255, 0)  # Green for high confidence
                    elif detection.iou_score >= 0.2:
                        color = (0, 165, 255)  # Orange for medium confidence  
                    else:
                        color = (0, 0, 255)  # Red for low confidence
                    
                    # Draw rectangle
                    cv2.rectangle(overlay_image, (int(x), int(y)), (int(x + w), int(y + h)), color, 3)
                    
                    # Add confidence text
                    text = f"IoU:{detection.iou_score:.2f}"
                    cv2.putText(
                        overlay_image, text, (int(x), int(y - 5)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
                    )
                
                # Save overlay image
                overlay_dir = os.path.join(self.doc_dir, "symbols", "detections", f"run_{run_id}", f"symbol_{symbol_id}")
                overlay_path = os.path.join(overlay_dir, f"debug_overlay_page_{page_num}.png")
                
                cv2.imwrite(overlay_path, overlay_image)
                print(f"🖼️ Saved debug overlay: {overlay_path}")
                
        except Exception as e:
            print(f"❌ Failed to create debug overlay: {e}")
            # Don't raise - this is optional debug feature