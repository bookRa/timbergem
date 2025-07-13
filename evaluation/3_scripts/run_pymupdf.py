#!/usr/bin/env python3
"""
Script to process PDF documents in evaluation/1_input_documents/
and extract text using both native and OCR methods with PyMuPDF.
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF

def process_pdf(pdf_path, output_base_dir):
    """
    Process a single PDF file and extract text using both native and OCR methods.
    
    Args:
        pdf_path (Path): Path to the PDF file
        output_base_dir (Path): Base directory for output artifacts
    """
    print(f"Processing: {pdf_path.name}")
    
    # Create output directory for this document
    document_name = pdf_path.stem  # filename without extension
    output_dir = output_base_dir / document_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    doc = None
    try:
        # Open the PDF document
        doc = fitz.open(pdf_path)
        
        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            print(f"  Processing page {page_num + 1}/{len(doc)}")
            
            # Native text extraction
            native_text = page.get_text()
            native_output_path = output_dir / f"page_{page_num + 1}_pymupdf_native.txt"
            with open(native_output_path, 'w', encoding='utf-8') as f:
                f.write(native_text)
            
            # OCR text extraction
            try:
                textpage_ocr = page.get_textpage_ocr()
                ocr_text = page.get_text(textpage=textpage_ocr)
                ocr_output_path = output_dir / f"page_{page_num + 1}_pymupdf_ocr.txt"
                with open(ocr_output_path, 'w', encoding='utf-8') as f:
                    f.write(ocr_text)
            except Exception as e:
                print(f"    Warning: OCR extraction failed for page {page_num + 1}: {e}")
                # Create empty OCR file to indicate the attempt was made
                ocr_output_path = output_dir / f"page_{page_num + 1}_pymupdf_ocr.txt"
                with open(ocr_output_path, 'w', encoding='utf-8') as f:
                    f.write(f"OCR extraction failed: {e}\n")
        
        print(f"  Completed: {len(doc)} pages processed")
        
    except Exception as e:
        print(f"  Error processing {pdf_path.name}: {e}")
    finally:
        # Ensure document is closed properly
        if doc is not None:
            doc.close()

def main():
    """Main function to process all PDF documents."""
    # Define paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    input_dir = project_root / "evaluation" / "1_input_documents"
    output_dir = project_root / "evaluation" / "2_output_artifacts"
    
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files in the input directory
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the input directory")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF files to process")
    print("-" * 50)
    
    # Process each PDF file
    for pdf_file in sorted(pdf_files):
        process_pdf(pdf_file, output_dir)
        print("-" * 50)
    
    print("Processing complete!")

if __name__ == "__main__":
    main()
