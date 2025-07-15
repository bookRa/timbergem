import os
import json
import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Optional
import uuid


class PDFProcessor:
    """
    Handles PDF processing operations including:
    - Text extraction
    - Table extraction 
    - High-resolution pixmap generation
    - Metadata collection
    """
    
    def __init__(self, dpi: int = 200, high_res_dpi: int = 300):
        self.dpi = dpi
        self.high_res_dpi = high_res_dpi
    
    def process_pdf(self, pdf_path: str, output_dir: str, doc_id: str) -> Dict:
        """
        Complete PDF processing pipeline that extracts all artifacts for each page.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save processed artifacts
            doc_id: Unique document identifier
            
        Returns:
            Dictionary containing processing results and metadata
        """
        print(f"🔄 Starting PDF processing for {pdf_path}")
        
        # Create output directory structure
        os.makedirs(output_dir, exist_ok=True)
        
        # Open PDF document
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        
        print(f"   -> PDF has {num_pages} pages")
        
        # Store processing results
        processing_results = {
            "docId": doc_id,
            "totalPages": num_pages,
            "dpi": self.dpi,
            "high_res_dpi": self.high_res_dpi,
            "pages": {},
            "processing_summary": {
                "pages_with_text": 0
            }
        }
        
        # Process each page
        for page_num in range(num_pages):
            page_results = self._process_page(doc, page_num, output_dir)
            processing_results["pages"][page_num + 1] = page_results
            
            # Update summary statistics
            if page_results["text_extracted"]:
                processing_results["processing_summary"]["pages_with_text"] += 1
        
        # Save processing metadata
        metadata_file = os.path.join(output_dir, "processing_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(processing_results, f, indent=2)
        
        # Copy original PDF for reference (only if it doesn't already exist)
        import shutil
        original_pdf_path = os.path.join(output_dir, "original.pdf")
        if not os.path.exists(original_pdf_path):
            shutil.copy2(pdf_path, original_pdf_path)
            print(f"   ✅ Saved original PDF to: {original_pdf_path}")
        else:
            print(f"   ✅ Original PDF already exists: {original_pdf_path}")
        
        doc.close()
        
        print(f"   ✅ PDF processing complete")
        print(f"      -> Pages with text: {processing_results['processing_summary']['pages_with_text']}")
        
        return processing_results
    
    def _process_page(self, doc: fitz.Document, page_num: int, output_dir: str) -> Dict:
        """
        Process a single page to extract all artifacts.
        
        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based)
            output_dir: Output directory for artifacts
            
        Returns:
            Dictionary containing page processing results
        """
        page = doc.load_page(page_num)
        page_number = page_num + 1  # 1-based for user display
        
        print(f"     Processing page {page_number}...")
        
        # Create page-specific directory
        page_dir = os.path.join(output_dir, f"page_{page_number}")
        os.makedirs(page_dir, exist_ok=True)
        
        page_results = {
            "page_number": page_number,
            "page_dir": page_dir,
            "artifacts": {},
            "text_extracted": False,
            "pdf_metadata": self._get_page_metadata(page)
        }
        
        # 1. Generate high-resolution pixmap
        pixmap_path = self._generate_pixmap(page, page_dir, page_number)
        page_results["artifacts"]["pixmap"] = pixmap_path
        
        # 2. Extract text
        text_path = self._extract_text(page, page_dir, page_number)
        if text_path:
            page_results["artifacts"]["text"] = text_path
            page_results["text_extracted"] = True
        
        return page_results
    
    def _generate_pixmap(self, page: fitz.Page, page_dir: str, page_number: int) -> str:
        """Generate high-resolution pixmap for the page."""
        pix = page.get_pixmap(dpi=self.high_res_dpi)
        pixmap_path = os.path.join(page_dir, f"page_{page_number}_pixmap.png")
        pix.save(pixmap_path)
        
        print(f"       ✅ Pixmap saved: {pixmap_path} ({pix.width}x{pix.height})")
        return pixmap_path
    
    def _extract_text(self, page: fitz.Page, page_dir: str, page_number: int) -> Optional[str]:
        """Extract text from the page."""
        text = page.get_text()
        
        # Only save if meaningful text was found
        if text.strip():
            text_path = os.path.join(page_dir, f"page_{page_number}_text.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            word_count = len(text.split())
            print(f"       ✅ Text extracted: {text_path} ({word_count} words)")
            return text_path
        else:
            print(f"       ⚪ No meaningful text found on page {page_number}")
            return None
    

    
    def _get_page_metadata(self, page: fitz.Page) -> Dict:
        """Get page metadata for coordinate transformation."""
        pdf_rect = page.rect
        
        return {
            "pdf_width": pdf_rect.width,
            "pdf_height": pdf_rect.height,
            "rotation": page.rotation,
            "dpi": self.dpi,
            "high_res_dpi": self.high_res_dpi
        }
    
 