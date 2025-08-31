#!/usr/bin/env python3
"""
Test script for the symbol dimensions integration
"""

import sys
import os

sys.path.append("/Users/bigo/Projects/timbergem/backend")

from utils.symbol_dimensions import SymbolDimensionCalculator
from utils.coordinate_mapping import PDFCoordinates
import fitz
import json


def test_symbol_dimensions():
    """Test the symbol dimension calculator with existing metadata"""

    doc_id = "fbccf66c-16f4-4e6d-a56d-1688ce3e0941"

    # Paths
    metadata_path = f"/Users/bigo/Projects/timbergem/data/processed/{doc_id}/symbols/symbols_metadata.json"
    pdf_path = f"/Users/bigo/Projects/timbergem/data/processed/{doc_id}/original.pdf"

    if not os.path.exists(metadata_path):
        print(f"❌ Metadata file not found: {metadata_path}")
        return

    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return

    # Load existing metadata
    with open(metadata_path, "r") as f:
        metadata_json = json.load(f)

    print(f"🔍 Testing symbol dimensions calculation...")
    print(f"   Found {len(metadata_json['symbols'])} symbols to test")

    # Initialize calculator and PDF
    calculator = SymbolDimensionCalculator()
    pdf_document = fitz.open(pdf_path)

    try:
        for i, symbol in enumerate(metadata_json["symbols"]):
            print(f"\n📏 Testing symbol {i+1}: '{symbol['name']}'")

            # Create PDF coordinates
            pdf_coords = PDFCoordinates(
                left=symbol["coordinates"]["pdf_absolute"]["left_points"],
                top=symbol["coordinates"]["pdf_absolute"]["top_points"],
                width=symbol["coordinates"]["pdf_absolute"]["width_points"],
                height=symbol["coordinates"]["pdf_absolute"]["height_points"],
            )

            # Calculate dimensions
            dimensions = calculator.calculate_dimensions_from_pdf(
                pdf_document, symbol["page_number"], pdf_coords
            )

            print(
                f"   PDF coords: ({pdf_coords.left:.2f}, {pdf_coords.top:.2f}) {pdf_coords.width:.2f}x{pdf_coords.height:.2f}"
            )
            print(f"   Calculated dimensions: {dimensions}")

            # Check if dimensions already exist in metadata
            if "symbol_template_dimensions" in symbol:
                existing = symbol["symbol_template_dimensions"]
                print(f"   Existing dimensions: {existing}")
            else:
                print(f"   ✨ No existing dimensions found - this would be new data!")

    finally:
        pdf_document.close()

    print(f"\n✅ Symbol dimensions test completed!")


if __name__ == "__main__":
    test_symbol_dimensions()
