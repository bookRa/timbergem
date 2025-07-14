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
                "pages_with_text": 0,
                "pages_with_tables": 0,
                "total_tables": 0
            }
        }
        
        # Process each page
        for page_num in range(num_pages):
            page_results = self._process_page(doc, page_num, output_dir)
            processing_results["pages"][page_num + 1] = page_results
            
            # Update summary statistics
            if page_results["text_extracted"]:
                processing_results["processing_summary"]["pages_with_text"] += 1
            if page_results["tables_found"] > 0:
                processing_results["processing_summary"]["pages_with_tables"] += 1
                processing_results["processing_summary"]["total_tables"] += page_results["tables_found"]
        
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
        print(f"      -> Pages with tables: {processing_results['processing_summary']['pages_with_tables']}")
        print(f"      -> Total tables found: {processing_results['processing_summary']['total_tables']}")
        
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
            "tables_found": 0,
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
        
        # 3. Extract tables
        tables_path = self._extract_tables(page, page_dir, page_number)
        if tables_path:
            page_results["artifacts"]["tables"] = tables_path
            # Count actual tables by checking the CSV content
            page_results["tables_found"] = self._count_tables_in_csv(tables_path)
        
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
    
    def _extract_tables(self, page: fitz.Page, page_dir: str, page_number: int) -> Optional[str]:
        """Extract tables from the page."""
        try:
            tables = page.find_tables()
            
            # Convert tables to list to check length properly
            table_list = list(tables) if tables else []
            
            if table_list:
                tables_path = os.path.join(page_dir, f"page_{page_number}_tables.csv")
                
                # Combine all tables into a single CSV file
                with open(tables_path, 'w', encoding='utf-8') as f:
                    f.write("# Tables extracted from page {}\n".format(page_number))
                    
                    for i, table in enumerate(table_list):
                        f.write(f"\n# Table {i + 1}\n")
                        
                        # Extract table data
                        table_data = table.extract()
                        
                        # Write table as CSV
                        import csv
                        import io
                        
                        # Use StringIO to write CSV data
                        csv_buffer = io.StringIO()
                        csv_writer = csv.writer(csv_buffer)
                        
                        for row in table_data:
                            # Clean up row data
                            clean_row = [str(cell).strip() if cell else "" for cell in row]
                            csv_writer.writerow(clean_row)
                        
                        f.write(csv_buffer.getvalue())
                        f.write("\n")
                
                print(f"       ✅ Tables extracted: {tables_path} ({len(table_list)} tables)")
                return tables_path
            else:
                print(f"       ⚪ No tables found on page {page_number}")
                return None
                
        except Exception as e:
            print(f"       ⚠️  Error extracting tables from page {page_number}: {e}")
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
    
    def _count_tables_in_csv(self, csv_path: str) -> int:
        """Count the number of actual tables in the CSV file."""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Count table headers (lines starting with "# Table")
                return content.count("# Table ")
        except Exception:
            return 0 