#!/usr/bin/env python3
"""
Test script to generate tight templates for existing symbols.
This will test the tight template generation functionality.
"""

import os
import sys
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from utils.symbol_dimensions import SymbolDimensionCalculator

def test_tight_template_generation():
    """Test tight template generation on existing symbols"""
    
    # Find the most recent document with symbols
    data_dir = "data/processed"
    if not os.path.exists(data_dir):
        print("❌ No processed data directory found")
        return
    
    # Look for documents with symbols
    doc_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    for doc_dir in doc_dirs:
        symbols_metadata_path = os.path.join(data_dir, doc_dir, "symbols", "symbols_metadata.json")
        if os.path.exists(symbols_metadata_path):
            print(f"\n🔍 Testing tight template generation for document: {doc_dir}")
            
            # Load symbols metadata
            with open(symbols_metadata_path, 'r') as f:
                metadata = json.load(f)
            
            calculator = SymbolDimensionCalculator()
            
            # Test template generation for each symbol
            for symbol in metadata.get("symbols", []):
                symbol_name = symbol.get("name", "Unknown")
                relative_path = symbol.get("relative_path", "")
                
                if not relative_path:
                    continue
                
                original_path = os.path.join(data_dir, doc_dir, relative_path)
                if not os.path.exists(original_path):
                    print(f"   ⚠️ Original image not found: {original_path}")
                    continue
                
                # Generate tight template path
                base_name = os.path.splitext(os.path.basename(original_path))[0]
                template_name = f"{base_name}_template.png"
                template_path = os.path.join(os.path.dirname(original_path), template_name)
                
                print(f"\n📋 Processing symbol: {symbol_name}")
                print(f"   Original: {original_path}")
                print(f"   Template: {template_path}")
                
                # Generate tight template
                result = calculator.generate_tight_template(original_path, template_path)
                
                if result["success"]:
                    print(f"   ✅ Success!")
                    print(f"   📐 Template dimensions: {result['template_dimensions']}")
                    print(f"   📍 Crop offset: {result['crop_offset']}")
                    
                    # Compare with original symbol dimensions
                    original_dims = symbol.get("symbol_template_dimensions", {})
                    print(f"   🔄 Original dimensions: {original_dims}")
                    
                    template_dims = result["template_dimensions"]
                    if (template_dims["width_pixels_300dpi"] != original_dims.get("width_pixels_300dpi", 0) or
                        template_dims["height_pixels_300dpi"] != original_dims.get("height_pixels_300dpi", 0)):
                        print(f"   🎯 TIGHT TEMPLATE IS DIFFERENT FROM ORIGINAL!")
                    else:
                        print(f"   ➡️ Template matches original dimensions")
                else:
                    print(f"   ❌ Failed to generate tight template")
            
            # Test only the first document with symbols
            break
    else:
        print("❌ No documents with symbols found")

if __name__ == "__main__":
    test_tight_template_generation()