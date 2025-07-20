import os
import json
import uuid
from flask import Blueprint, request, jsonify
import fitz  # PyMuPDF
from PIL import Image
import io

# Create blueprint for symbol annotation API
symbol_annotation_bp = Blueprint('symbol_annotation', __name__)

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
        
        # Load page metadata for coordinate transformation
        metadata_file = os.path.join(doc_dir, "page_metadata.json")
        if not os.path.exists(metadata_file):
            return jsonify({"error": "Page metadata not found"}), 404
        
        with open(metadata_file, 'r') as f:
            page_metadata = json.load(f)
        
        saved_symbols = []
        symbol_metadata = []
        
        # Group symbols by legend for processing
        symbols_by_legend = {}
        for symbol in symbols:
            legend_id = symbol["legendId"]
            if legend_id not in symbols_by_legend:
                symbols_by_legend[legend_id] = []
            symbols_by_legend[legend_id].append(symbol)
        
        # Process each legend and its symbols
        for legend_id, legend_symbols in symbols_by_legend.items():
            if legend_id not in clipping_images:
                print(f"   ⚠️  Skipping legend {legend_id} - no clipping image found")
                continue
            
            clipping_data = clipping_images[legend_id]
            legend_annotation = clipping_data["annotation"]
            clipping_url = clipping_data["url"]
            
            print(f"   📐 Processing legend {legend_id} on page {legend_annotation['pageNumber']}")
            print(f"     -> Legend clipping: {clipping_url}")
            print(f"     -> Symbols in this legend: {len(legend_symbols)}")
            
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
                
                # Process each symbol in this legend
                for i, symbol in enumerate(legend_symbols, 1):
                    symbol_name = symbol["name"].strip()
                    if not symbol_name:
                        continue
                    
                    # Create safe filename from symbol name
                    safe_name = "".join(c for c in symbol_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    safe_name = safe_name.replace(' ', '_')
                    
                    # Extract symbol coordinates (relative to the legend clipping)
                    symbol_left = int(symbol["left"])
                    symbol_top = int(symbol["top"])
                    symbol_width = int(symbol["width"])
                    symbol_height = int(symbol["height"])
                    
                    # Validate coordinates are within legend image bounds
                    if (symbol_left < 0 or symbol_top < 0 or 
                        symbol_left + symbol_width > legend_image.width or 
                        symbol_top + symbol_height > legend_image.height):
                        print(f"     ⚠️  Symbol '{symbol_name}' coordinates out of bounds, adjusting...")
                        
                        # Clamp to image bounds
                        symbol_left = max(0, min(symbol_left, legend_image.width - 1))
                        symbol_top = max(0, min(symbol_top, legend_image.height - 1))
                        symbol_width = max(1, min(symbol_width, legend_image.width - symbol_left))
                        symbol_height = max(1, min(symbol_height, legend_image.height - symbol_top))
                    
                    # Extract symbol from legend image
                    symbol_box = (symbol_left, symbol_top, symbol_left + symbol_width, symbol_top + symbol_height)
                    symbol_image = legend_image.crop(symbol_box)
                    
                    # Save symbol image
                    symbol_filename = f"{safe_name}_{i}.png"
                    symbol_path = os.path.join(legend_dir, symbol_filename)
                    symbol_image.save(symbol_path)
                    
                    print(f"     ✅ Saved symbol '{symbol_name}': {symbol_path}")
                    print(f"       Size: {symbol_image.size}")
                    
                    # Calculate coordinates relative to original PDF
                    # This requires transforming through multiple coordinate systems:
                    # 1. Symbol coords relative to legend clipping
                    # 2. Legend clipping coords relative to page canvas
                    # 3. Page canvas coords relative to original PDF
                    
                    page_num = legend_annotation["pageNumber"]
                    page_meta = page_metadata["pages"][str(page_num)]
                    
                    # Get legend annotation coordinates (in canvas space)
                    legend_canvas_left = legend_annotation["left"]
                    legend_canvas_top = legend_annotation["top"]
                    
                    # Transform symbol coordinates to canvas space
                    # Note: This assumes the legend clipping maintains the same scale as the canvas
                    symbol_canvas_left = legend_canvas_left + symbol_left
                    symbol_canvas_top = legend_canvas_top + symbol_top
                    
                    # Transform from canvas coordinates to PDF coordinates
                    canvas_width = page_meta.get("image_width", 800)  # Fallback values
                    canvas_height = page_meta.get("image_height", 600)
                    pdf_width = page_meta["pdf_width"]
                    pdf_height = page_meta["pdf_height"]
                    
                    # Calculate PDF coordinates
                    pdf_left = (symbol_canvas_left / canvas_width) * pdf_width
                    pdf_top = (symbol_canvas_top / canvas_height) * pdf_height
                    pdf_width_symbol = (symbol_width / canvas_width) * pdf_width
                    pdf_height_symbol = (symbol_height / canvas_height) * pdf_height
                    
                    # Store symbol metadata
                    symbol_meta = {
                        "id": symbol["id"],
                        "name": symbol_name,
                        "description": symbol.get("description", ""),
                        "filename": symbol_filename,
                        "relative_path": f"symbols/legend_{legend_id}/{symbol_filename}",
                        "coordinates": {
                            # Coordinates within the legend clipping
                            "legend_relative": {
                                "left": symbol_left,
                                "top": symbol_top,
                                "width": symbol_width,
                                "height": symbol_height
                            },
                            # Coordinates in the original page canvas
                            "canvas_absolute": {
                                "left": symbol_canvas_left,
                                "top": symbol_canvas_top,
                                "width": symbol_width,
                                "height": symbol_height
                            },
                            # Coordinates in the original PDF (in points)
                            "pdf_absolute": {
                                "left": pdf_left,
                                "top": pdf_top,
                                "width": pdf_width_symbol,
                                "height": pdf_height_symbol
                            }
                        },
                        "source_legend": {
                            "legend_id": legend_id,
                            "page_number": page_num,
                            "annotation_id": legend_annotation["id"]
                        },
                        "image_info": {
                            "width": symbol_image.width,
                            "height": symbol_image.height,
                            "format": "PNG"
                        }
                    }
                    
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
        
        return jsonify({
            "message": "Symbol clippings saved successfully",
            "docId": doc_id,
            "savedSymbols": len(saved_symbols),
            "symbolsMetadata": metadata_file,
            "symbolsList": saved_symbols
        }), 200
        
    except Exception as e:
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