import os
import json
import uuid
from dataclasses import dataclass
from flask import Blueprint, request, jsonify
import fitz  # PyMuPDF
from PIL import Image
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.coordinate_mapping import (
    PDFCoordinates, CanvasCoordinates, ClippingCoordinates, ClippingCoordinateTransformer,
    PageMetadata, HIGH_RES_DPI
)
from utils.symbol_dimensions import SymbolDimensionCalculator

# Create blueprint for symbol annotation API
symbol_annotation_bp = Blueprint('symbol_annotation', __name__)


@dataclass
class SymbolAnnotation:
    """Complete symbol annotation with all coordinate systems"""
    id: str
    name: str
    description: str
    
    # Source legend information
    legend_annotation_id: str
    legend_pdf_coords: PDFCoordinates
    
    # Symbol coordinates in different systems
    pdf_coords: PDFCoordinates  # Final absolute PDF coordinates
    clipping_coords: ClippingCoordinates  # Position within legend clipping
    canvas_coords: CanvasCoordinates  # UI annotation coordinates
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "coordinates": {
                "pdf_absolute": self.pdf_coords.to_dict(),
                "legend_clipping_relative": self.clipping_coords.to_dict(),
                "canvas_annotation": self.canvas_coords.to_dict()
            },
            "source_legend": {
                "annotation_id": self.legend_annotation_id,
                "pdf_coordinates": self.legend_pdf_coords.to_dict()
            },
            "image_info": {
                "width": self.clipping_coords.width_pixels,
                "height": self.clipping_coords.height_pixels,
                "format": "PNG"
            }
        }

@symbol_annotation_bp.route("/api/save_symbol_clippings", methods=["POST", "OPTIONS"])
def save_symbol_clippings():
    """
    Save individual symbol clippings from Symbol Legend annotations.
    Each symbol becomes its own image file with metadata linking back to the original PDF coordinates.
    """
    print("\n--- Received request on /api/save_symbol_clippings ---")
    
    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for symbol clippings")
        return "", 200
    
    try:
        data = request.get_json()
        pdf_document = None  # Initialize to handle cleanup on errors
        
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        doc_id = data.get("docId")
        symbols = data.get("symbols", [])
        clipping_images = data.get("clippingImages", {})
        
        if not doc_id:
            return jsonify({"error": "Document ID is required"}), 400
        
        if not symbols:
            return jsonify({"error": "No symbols to save"}), 400
        
        print(f"🔣 Saving symbol clippings for document: {doc_id}")
        print(f"   -> Number of symbols: {len(symbols)}")
        
        # Get the processed folder path from app config
        from flask import current_app
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404
        
        # Create symbols directory
        symbols_dir = os.path.join(doc_dir, "symbols")
        os.makedirs(symbols_dir, exist_ok=True)
        
        # Load page metadata for coordinate transformation using new system
        metadata_file = os.path.join(doc_dir, "page_metadata.json")
        if not os.path.exists(metadata_file):
            return jsonify({"error": "Page metadata not found"}), 404
        
        # Load the original PDF document for symbol dimension calculations
        pdf_file = os.path.join(doc_dir, "original.pdf")
        if not os.path.exists(pdf_file):
            return jsonify({"error": "Original PDF not found"}), 404
        
        pdf_document = fitz.open(pdf_file)
        dimension_calculator = SymbolDimensionCalculator()
        
        with open(metadata_file, 'r') as f:
            metadata_dict = json.load(f)
        
        # Convert to new PageMetadata objects
        page_metadata = {}
        for page_num, page_data in metadata_dict["pages"].items():
            page_metadata[int(page_num)] = PageMetadata.from_dict(page_data)
        
        saved_symbols = []
        symbol_metadata = []
        
        # Group symbols by legend for processing
        symbols_by_legend = {}
        for symbol in symbols:
            legend_id = symbol["legendId"]
            if legend_id not in symbols_by_legend:
                symbols_by_legend[legend_id] = []
            symbols_by_legend[legend_id].append(symbol)
        
        # Process each legend and its symbols using new coordinate system
        for legend_id, legend_symbols in symbols_by_legend.items():
            if legend_id not in clipping_images:
                print(f"   ⚠️  Skipping legend {legend_id} - no clipping image found")
                continue
            
            clipping_data = clipping_images[legend_id]
            legend_annotation = clipping_data["annotation"]
            clipping_url = clipping_data["url"]
            page_number = legend_annotation['pageNumber']
            
            print(f"   📐 Processing legend {legend_id} on page {page_number}")
            print(f"     -> Legend clipping: {clipping_url}")
            print(f"     -> Symbols in this legend: {len(legend_symbols)}")
            
            # Get legend PDF coordinates from the annotation (should be stored from DefineKeyAreasTab)
            if "pdfCoordinates" not in legend_annotation:
                print(f"     ❌ Legend annotation missing PDF coordinates")
                continue
                
            legend_pdf_coords = PDFCoordinates(
                left=legend_annotation["pdfCoordinates"]["left_points"],
                top=legend_annotation["pdfCoordinates"]["top_points"],
                width=legend_annotation["pdfCoordinates"]["width_points"],
                height=legend_annotation["pdfCoordinates"]["height_points"]
            )
            
            # Create clipping coordinate transformer
            clipping_transformer = ClippingCoordinateTransformer(
                legend_pdf_coords=legend_pdf_coords,
                clipping_dpi=HIGH_RES_DPI,  # Clippings are generated at high-res DPI
                page_metadata=page_metadata[page_number]
            )
            
            # Load the legend clipping image
            clipping_path = clipping_url.replace(f"/data/processed/{doc_id}/", "")
            full_clipping_path = os.path.join(doc_dir, clipping_path)
            
            if not os.path.exists(full_clipping_path):
                print(f"     ❌ Legend clipping not found: {full_clipping_path}")
                continue
            
            try:
                legend_image = Image.open(full_clipping_path)
                print(f"     ✅ Loaded legend image: {legend_image.size}")
                
                # Create legend-specific directory
                legend_dir = os.path.join(symbols_dir, f"legend_{legend_id}")
                os.makedirs(legend_dir, exist_ok=True)
                
                # Process each symbol in this legend using new coordinate system
                for i, symbol in enumerate(legend_symbols, 1):
                    symbol_name = symbol["name"].strip()
                    if not symbol_name:
                        continue
                    
                    # Create safe filename from symbol name
                    safe_name = "".join(c for c in symbol_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    safe_name = safe_name.replace(' ', '_')
                    
                    # Create symbol canvas coordinates (from UI annotation)
                    symbol_canvas_coords = CanvasCoordinates(
                        left=float(symbol["left"]),
                        top=float(symbol["top"]),
                        width=float(symbol["width"]),
                        height=float(symbol["height"]),
                        canvas_width=float(symbol.get("canvasWidth", legend_image.width)),
                        canvas_height=float(symbol.get("canvasHeight", legend_image.height))
                    )
                    
                    # Transform to absolute PDF coordinates
                    symbol_pdf_coords = clipping_transformer.symbol_canvas_to_pdf(symbol_canvas_coords)
                    
                    # Also get clipping coordinates for image extraction
                    symbol_clipping_coords = clipping_transformer.canvas_to_clipping(symbol_canvas_coords)
                    
                    print(f"     🔣 Processing symbol '{symbol_name}':")
                    print(f"       Canvas: ({symbol_canvas_coords.left:.1f}, {symbol_canvas_coords.top:.1f}) {symbol_canvas_coords.width:.1f}x{symbol_canvas_coords.height:.1f}")
                    print(f"       PDF: ({symbol_pdf_coords.left:.2f}, {symbol_pdf_coords.top:.2f}) {symbol_pdf_coords.width:.2f}x{symbol_pdf_coords.height:.2f}")
                    
                    # Validate clipping coordinates are within legend image bounds
                    if (symbol_clipping_coords.left_pixels < 0 or symbol_clipping_coords.top_pixels < 0 or 
                        symbol_clipping_coords.left_pixels + symbol_clipping_coords.width_pixels > legend_image.width or 
                        symbol_clipping_coords.top_pixels + symbol_clipping_coords.height_pixels > legend_image.height):
                        print(f"       ⚠️  Symbol coordinates out of bounds, adjusting...")
                        
                        # Clamp to image bounds
                        left = max(0, min(symbol_clipping_coords.left_pixels, legend_image.width - 1))
                        top = max(0, min(symbol_clipping_coords.top_pixels, legend_image.height - 1))
                        width = max(1, min(symbol_clipping_coords.width_pixels, legend_image.width - left))
                        height = max(1, min(symbol_clipping_coords.height_pixels, legend_image.height - top))
                        
                        # Update clipping coordinates
                        symbol_clipping_coords = ClippingCoordinates(
                            left_pixels=left, top_pixels=top, width_pixels=width, height_pixels=height,
                            clipping_dpi=symbol_clipping_coords.clipping_dpi
                        )
                    
                    # Extract symbol from legend image
                    symbol_box = (
                        symbol_clipping_coords.left_pixels, 
                        symbol_clipping_coords.top_pixels,
                        symbol_clipping_coords.left_pixels + symbol_clipping_coords.width_pixels,
                        symbol_clipping_coords.top_pixels + symbol_clipping_coords.height_pixels
                    )
                    symbol_image = legend_image.crop(symbol_box)
                    
                    # Save symbol image
                    symbol_filename = f"{safe_name}_{i}.png"
                    symbol_path = os.path.join(legend_dir, symbol_filename)
                    symbol_image.save(symbol_path)
                    
                    print(f"       ✅ Saved symbol image: {symbol_path}")
                    print(f"       Image size: {symbol_image.size}")
                    
                    # Calculate symbol dimensions using contour analysis
                    try:
                        symbol_dimensions = dimension_calculator.calculate_dimensions_from_pdf(
                            pdf_document, 
                            page_number, 
                            symbol_pdf_coords
                        )
                        print(f"       📏 Symbol dimensions: {symbol_dimensions}")
                    except Exception as e:
                        print(f"       ⚠️  Failed to calculate symbol dimensions: {e}")
                        symbol_dimensions = {"height_pixels_300dpi": 0, "width_pixels_300dpi": 0}
                    
                    # Create complete symbol annotation object
                    symbol_annotation = SymbolAnnotation(
                        id=str(uuid.uuid4()),
                        name=symbol_name,
                        description=symbol.get("description", ""),
                        legend_annotation_id=legend_id,
                        legend_pdf_coords=legend_pdf_coords,
                        pdf_coords=symbol_pdf_coords,
                        clipping_coords=symbol_clipping_coords,
                        canvas_coords=symbol_canvas_coords
                    )
                    
                    # Store comprehensive symbol metadata using new coordinate system
                    symbol_meta = {
                        "id": symbol_annotation.id,
                        "name": symbol_name,
                        "description": symbol.get("description", ""),
                        "filename": symbol_filename,
                        "relative_path": f"symbols/legend_{legend_id}/{symbol_filename}",
                        "coordinates": symbol_annotation.to_dict()["coordinates"],
                        "source_legend": symbol_annotation.to_dict()["source_legend"],
                        "image_info": symbol_annotation.to_dict()["image_info"],
                        "page_number": page_number,
                        "coordinate_system": symbol.get("coordinateSystem", "UNKNOWN"),
                        "symbol_template_dimensions": symbol_dimensions,
                        "frontend_data": {
                            "canvas_coords": {
                                "left": symbol.get("left"),
                                "top": symbol.get("top"),
                                "width": symbol.get("width"),
                                "height": symbol.get("height")
                            },
                            "canvas_dimensions": {
                                "width": symbol.get("canvasWidth"),
                                "height": symbol.get("canvasHeight")
                            }
                        }
                    }
                    
                    print(f"       📄 Symbol metadata created:")
                    print(f"         Coordinate System: {symbol_meta['coordinate_system']}")
                    print(f"         PDF Coordinates: ({symbol_pdf_coords.left:.2f}, {symbol_pdf_coords.top:.2f}) {symbol_pdf_coords.width:.2f}x{symbol_pdf_coords.height:.2f}")
                    print(f"         Canvas Coordinates: ({symbol.get('left')}, {symbol.get('top')}) {symbol.get('width')}x{symbol.get('height')}")
                    print(f"         Symbol Dimensions: {symbol_dimensions}")
                    print(f"         Image saved: {symbol_path}")
                    
                    symbol_metadata.append(symbol_meta)
                    saved_symbols.append(symbol_name)
                
                legend_image.close()
                
            except Exception as e:
                print(f"     ❌ Error processing legend {legend_id}: {e}")
                continue
        
        # Save symbol metadata
        metadata_file = os.path.join(symbols_dir, "symbols_metadata.json")
        complete_metadata = {
            "docId": doc_id,
            "timestamp": str(uuid.uuid4()),
            "total_symbols": len(symbol_metadata),
            "symbols_by_legend": len(symbols_by_legend),
            "symbols": symbol_metadata,
            "processing_info": {
                "version": "1.0",
                "coordinate_systems": [
                    "legend_relative: coordinates within the legend clipping image",
                    "canvas_absolute: coordinates in the original page canvas",
                    "pdf_absolute: coordinates in the original PDF (points)"
                ]
            }
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(complete_metadata, f, indent=2)
        
        print(f"   ✅ Symbol processing complete:")
        print(f"     -> Saved {len(saved_symbols)} symbols")
        print(f"     -> Metadata saved: {metadata_file}")
        
        # Close the PDF document
        pdf_document.close()
        
        return jsonify({
            "message": "Symbol clippings saved successfully",
            "docId": doc_id,
            "savedSymbols": len(saved_symbols),
            "symbolsMetadata": metadata_file,
            "symbolsList": saved_symbols
        }), 200
        
    except Exception as e:
        # Ensure PDF document is closed even on error
        try:
            if pdf_document is not None:
                pdf_document.close()
        except:
            pass
        print(f"❌ ERROR: Failed to save symbol clippings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@symbol_annotation_bp.route("/api/load_symbols/<doc_id>", methods=["GET"])
def load_symbols(doc_id):
    """
    Load symbol metadata for a document.
    """
    print(f"\n--- Loading symbols for document: {doc_id} ---")
    
    try:
        from flask import current_app
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        doc_dir = os.path.join(processed_folder, doc_id)
        symbols_dir = os.path.join(doc_dir, "symbols")
        metadata_file = os.path.join(symbols_dir, "symbols_metadata.json")
        
        if not os.path.exists(metadata_file):
            print(f"   ⚠️  No symbols metadata found for document {doc_id}")
            return jsonify({
                "docId": doc_id,
                "symbols": [],
                "message": "No symbols found"
            }), 200
        
        with open(metadata_file, 'r') as f:
            symbol_data = json.load(f)
        
        print(f"   ✅ Loaded {len(symbol_data.get('symbols', []))} symbols")
        
        return jsonify(symbol_data), 200
        
    except Exception as e:
        print(f"❌ ERROR: Failed to load symbols: {e}")
        return jsonify({"error": str(e)}), 500 