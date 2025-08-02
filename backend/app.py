import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import fitz  # PyMuPDF

# Import new modular components
from api.page_to_html import page_to_html_bp
from api.symbol_annotation import symbol_annotation_bp
from utils.pdf_processor import PDFProcessor

# --- Basic Flask App Setup ---
app = Flask(__name__)

# Register blueprints
app.register_blueprint(page_to_html_bp)
app.register_blueprint(symbol_annotation_bp)

# --- CORS Setup ---
# Configure CORS for development with specific origins
# Also allow credentials for more robust cross-origin requests
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        },
        r"/data/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
            "methods": ["GET"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True,
        },
    },
)

# --- Configuration ---
UPLOAD_FOLDER = "uploads"
# Correctly point to the root /data/processed directory
PROCESSED_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "processed")
)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER

# Ensure the directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


print("✅ Backend server configured successfully.")
print(f" -> Uploads will be stored in: {os.path.abspath(UPLOAD_FOLDER)}")
print(f" -> Processed data will be stored in: {os.path.abspath(PROCESSED_FOLDER)}")


# --- API Endpoints ---


@app.route("/api/upload", methods=["POST", "OPTIONS"])
def upload_and_process_pdf():
    """
    Handles the PDF file upload and processes it using the modular PDF processor.
    This is the legacy endpoint that creates basic page images for the annotation system.
    For the new page-to-HTML pipeline, use /api/process_pdf_to_html
    """
    print("\n--- Received request on /api/upload ---")
    print(f"Request method: {request.method}")
    print(f"Request origin: {request.headers.get('Origin', 'No origin header')}")
    print(f"Request headers: {dict(request.headers)}")

    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request")
        return "", 200

    # 1. Check if a file was sent
    if "file" not in request.files:
        print("❌ ERROR: No file part in the request.")
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    if file.filename == "":
        print("❌ ERROR: No file selected.")
        return jsonify({"error": "No file selected"}), 400

    if file and file.filename.endswith(".pdf"):
        try:
            # 2. Save the uploaded PDF temporarily
            original_filename = file.filename
            print(f"📄 Received file: {original_filename}")

            temp_pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)
            file.save(temp_pdf_path)
            print(f"   -> Temporarily saved PDF to: {temp_pdf_path}")

            # 3. Process the PDF using the new modular processor
            doc_id = str(uuid.uuid4())
            output_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)

            # Create the modular PDF processor
            pdf_processor = PDFProcessor(dpi=200, high_res_dpi=300)

            # Process the PDF
            processing_results = pdf_processor.process_pdf(
                temp_pdf_path, output_dir, doc_id
            )

            # Create legacy page images for backward compatibility
            doc = fitz.open(temp_pdf_path)
            num_pages = len(doc)

            # Create standardized page metadata using new coordinate system
            from utils.coordinate_mapping import PageMetadata, DEFAULT_DPI, HIGH_RES_DPI

            page_metadata = {}
            dpi = DEFAULT_DPI

            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                page_number = page_num + 1

                # Get original PDF page dimensions (in points)
                pdf_rect = page.rect

                # Calculate image dimensions
                image_width_pixels = int(pdf_rect.width * dpi / 72.0)
                image_height_pixels = int(pdf_rect.height * dpi / 72.0)
                high_res_width_pixels = int(pdf_rect.width * HIGH_RES_DPI / 72.0)
                high_res_height_pixels = int(pdf_rect.height * HIGH_RES_DPI / 72.0)

                # Create standardized page metadata
                page_meta = PageMetadata(
                    page_number=page_number,
                    pdf_width_points=pdf_rect.width,
                    pdf_height_points=pdf_rect.height,
                    pdf_rotation_degrees=page.rotation,
                    image_width_pixels=image_width_pixels,
                    image_height_pixels=image_height_pixels,
                    image_dpi=dpi,
                    high_res_image_width_pixels=high_res_width_pixels,
                    high_res_image_height_pixels=high_res_height_pixels,
                    high_res_dpi=HIGH_RES_DPI,
                )

                # Create pixmap for this page at standard DPI
                pix = page.get_pixmap(dpi=dpi)

                # Save the page image
                image_path = os.path.join(output_dir, f"page_{page_number}.png")
                pix.save(image_path)
                print(
                    f"   -> Page {page_number} image saved: {image_path} ({pix.width}x{pix.height})"
                )

                # Store metadata using new format
                page_metadata[page_number] = page_meta.to_dict()

            # Save standardized metadata to JSON file
            metadata_file = os.path.join(output_dir, "page_metadata.json")
            import json

            with open(metadata_file, "w") as f:
                json.dump(
                    {"docId": doc_id, "totalPages": num_pages, "pages": page_metadata},
                    f,
                    indent=2,
                )

            doc.close()

            # 4. Clean up the temporary PDF
            os.remove(temp_pdf_path)
            print(f"   -> Cleaned up temporary file: {temp_pdf_path}")

            # 5. Return a success response
            print(
                "--- ✅ Successfully processed PDF. Sending response to frontend. ---"
            )

            # Debug: Check what's in processing_results to identify serialization issue
            print(f"📊 Processing results keys: {processing_results.keys()}")
            print(f"📊 Processing summary: {processing_results['processing_summary']}")

            # Test JSON serialization of each component
            import json

            try:
                json.dumps(processing_results["processing_summary"])
                print("✅ processing_summary is JSON serializable")
            except Exception as e:
                print(f"❌ processing_summary serialization error: {e}")

            try:
                json.dumps(page_metadata)
                print("✅ page_metadata is JSON serializable")
            except Exception as e:
                print(f"❌ page_metadata serialization error: {e}")

            # Only return the safe parts, not the full processing_results which might contain PageMetadata
            response_data = {
                "message": "File processed successfully",
                "docId": doc_id,
                "totalPages": num_pages,
                "processing_summary": processing_results["processing_summary"],
                "pageMetadata": page_metadata,  # This should be serialized dicts now
            }

            print(f"📤 Response data keys: {response_data.keys()}")

            try:
                json.dumps(response_data)
                print("✅ Full response_data is JSON serializable")
            except Exception as e:
                print(f"❌ response_data serialization error: {e}")
                # Return minimal response if there's still an issue
                return (
                    jsonify(
                        {
                            "message": "File processed successfully",
                            "docId": doc_id,
                            "totalPages": num_pages,
                        }
                    ),
                    200,
                )

            return jsonify(response_data), 200

        except Exception as e:
            print(f"❌ ERROR: An unexpected error occurred: {e}")
            return jsonify({"error": str(e)}), 500

    print("❌ ERROR: Invalid file type. Only PDFs are allowed.")
    return jsonify({"error": "Invalid file type"}), 400


@app.route("/api/save_annotations", methods=["POST", "OPTIONS"])
def save_annotations():
    """
    Saves annotation data for a document to a JSON file.
    """
    print("\n--- Received request on /api/save_annotations ---")
    print(f"Request method: {request.method}")

    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for annotations")
        return "", 200

    try:
        data = request.get_json()

        if not data:
            print("❌ ERROR: No JSON data received.")
            return jsonify({"error": "No data received"}), 400

        doc_id = data.get("docId")
        annotations = data.get("annotations", [])

        if not doc_id:
            print("❌ ERROR: Document ID is required.")
            return jsonify({"error": "Document ID is required"}), 400

        print(f"📝 Saving annotations for document: {doc_id}")
        print(f"   -> Number of annotations: {len(annotations)}")

        # Ensure the document directory exists
        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        if not os.path.exists(doc_dir):
            print(f"❌ ERROR: Document directory not found: {doc_dir}")
            return jsonify({"error": "Document not found"}), 404

        # Save annotations to JSON file
        annotations_file = os.path.join(doc_dir, "annotations.json")

        # Create the annotation data structure
        annotation_data = {
            "docId": doc_id,
            "timestamp": str(uuid.uuid4()),  # Using uuid as timestamp for now
            "annotations": annotations,
            "metadata": {"totalAnnotations": len(annotations), "annotationsByPage": {}},
        }

        # Group annotations by page for metadata
        for annotation in annotations:
            page = annotation.get("pageNumber", 1)
            if page not in annotation_data["metadata"]["annotationsByPage"]:
                annotation_data["metadata"]["annotationsByPage"][page] = 0
            annotation_data["metadata"]["annotationsByPage"][page] += 1

        # Write to file
        import json

        with open(annotations_file, "w") as f:
            json.dump(annotation_data, f, indent=2)

        print(f"   ✅ Annotations saved to: {annotations_file}")

        return (
            jsonify(
                {
                    "message": "Annotations saved successfully",
                    "docId": doc_id,
                    "annotationCount": len(annotations),
                    "savedTo": annotations_file,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to save annotations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/load_annotations/<doc_id>", methods=["GET"])
def load_annotations(doc_id):
    """
    Loads annotation data for a document from JSON file.
    """
    print(f"\n--- Loading annotations for document: {doc_id} ---")

    try:
        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        annotations_file = os.path.join(doc_dir, "annotations.json")

        if not os.path.exists(annotations_file):
            print(f"   ⚠️  No annotations file found for document {doc_id}")
            return (
                jsonify(
                    {
                        "docId": doc_id,
                        "annotations": [],
                        "message": "No annotations found",
                    }
                ),
                200,
            )

        import json

        with open(annotations_file, "r") as f:
            annotation_data = json.load(f)

        print(f"   ✅ Loaded {len(annotation_data.get('annotations', []))} annotations")

        return jsonify(annotation_data), 200

    except Exception as e:
        print(f"❌ ERROR: Failed to load annotations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/save_summaries", methods=["POST", "OPTIONS"])
def save_summaries():
    """
    Saves page summaries for a document to a JSON file.
    """
    print("\n--- Received request on /api/save_summaries ---")

    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for summaries")
        return "", 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        doc_id = data.get("docId")
        summaries = data.get("summaries", {})

        if not doc_id:
            return jsonify({"error": "Document ID is required"}), 400

        print(f"📝 Saving summaries for document: {doc_id}")

        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        summaries_file = os.path.join(doc_dir, "summaries.json")

        summary_data = {
            "docId": doc_id,
            "timestamp": str(uuid.uuid4()),
            "summaries": summaries,
            "metadata": {
                "totalPages": len(summaries),
                "lastUpdated": str(uuid.uuid4()),  # placeholder for actual timestamp
            },
        }

        import json

        with open(summaries_file, "w") as f:
            json.dump(summary_data, f, indent=2)

        print(f"   ✅ Summaries saved to: {summaries_file}")

        return (
            jsonify(
                {
                    "message": "Summaries saved successfully",
                    "docId": doc_id,
                    "pageCount": len(summaries),
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to save summaries: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/load_summaries/<doc_id>", methods=["GET"])
def load_summaries(doc_id):
    """
    Loads page summaries for a document from JSON file.
    """
    print(f"\n--- Loading summaries for document: {doc_id} ---")

    try:
        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        summaries_file = os.path.join(doc_dir, "summaries.json")

        if not os.path.exists(summaries_file):
            print(f"   ⚠️  No summaries file found for document {doc_id}")
            return (
                jsonify(
                    {"docId": doc_id, "summaries": {}, "message": "No summaries found"}
                ),
                200,
            )

        import json

        with open(summaries_file, "r") as f:
            summary_data = json.load(f)

        print(
            f"   ✅ Loaded summaries for {len(summary_data.get('summaries', {}))} pages"
        )

        return jsonify(summary_data), 200

    except Exception as e:
        print(f"❌ ERROR: Failed to load summaries: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_summary", methods=["POST", "OPTIONS"])
def generate_summary():
    """
    Generates an AI summary for a specific page (placeholder implementation).
    In a real implementation, this would extract text from the PDF page and use an LLM.
    """
    print("\n--- Received request on /api/generate_summary ---")

    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for summary generation")
        return "", 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        doc_id = data.get("docId")
        page_number = data.get("pageNumber")

        if not doc_id or not page_number:
            return jsonify({"error": "Document ID and page number are required"}), 400

        print(f"🤖 Generating AI summary for document: {doc_id}, page: {page_number}")

        # TODO: Implement actual text extraction and LLM summarization
        # For now, return a placeholder summary
        placeholder_summary = f"AI-generated summary for page {page_number}: This page contains construction document information including technical drawings, specifications, and project details. The content includes various building components, measurements, and construction notes that are relevant to the overall project scope."

        print(f"   ✅ Generated summary: {placeholder_summary[:50]}...")

        return (
            jsonify(
                {
                    "docId": doc_id,
                    "pageNumber": page_number,
                    "summary": placeholder_summary,
                    "generated": True,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to generate summary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/save_project_data", methods=["POST", "OPTIONS"])
def save_project_data():
    """
    Saves complete project data including annotations, summaries, and pipeline state.
    """
    print("\n--- Received request on /api/save_project_data ---")

    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for project data")
        return "", 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        doc_id = data.get("docId")
        project_data = data.get("projectData", {})

        if not doc_id:
            return jsonify({"error": "Document ID is required"}), 400

        print(f"💾 Saving project data for document: {doc_id}")

        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        project_file = os.path.join(doc_dir, "project_data.json")

        complete_project_data = {
            "docId": doc_id,
            "timestamp": str(uuid.uuid4()),
            "projectData": project_data,
            "metadata": {
                "version": "1.0",
                "lastUpdated": str(uuid.uuid4()),  # placeholder for actual timestamp
                "pipeline_stage": "define_key_areas",  # this would be dynamic
            },
        }

        import json

        with open(project_file, "w") as f:
            json.dump(complete_project_data, f, indent=2)

        print(f"   ✅ Project data saved to: {project_file}")

        return (
            jsonify(
                {
                    "message": "Project data saved successfully",
                    "docId": doc_id,
                    "savedTo": project_file,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to save project data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/load_project_data/<doc_id>", methods=["GET"])
def load_project_data(doc_id):
    """
    Loads complete project data for a document.
    """
    print(f"\n--- Loading project data for document: {doc_id} ---")

    try:
        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        project_file = os.path.join(doc_dir, "project_data.json")

        if not os.path.exists(project_file):
            print(f"   ⚠️  No project data file found for document {doc_id}")
            return (
                jsonify(
                    {
                        "docId": doc_id,
                        "projectData": {
                            "keyAreas": {},
                            "summaries": {},
                            "knowledgeGraph": None,
                            "scopeGroups": [],
                            "scopeAnnotations": {},
                        },
                        "message": "No project data found",
                    }
                ),
                200,
            )

        import json

        with open(project_file, "r") as f:
            project_data = json.load(f)

        print(f"   ✅ Loaded project data")

        return jsonify(project_data), 200

    except Exception as e:
        print(f"❌ ERROR: Failed to load project data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_clippings", methods=["POST", "OPTIONS"])
def generate_clippings():
    """
    Generates high-resolution clippings from PDF based on canvas annotations.
    """
    print("\n--- Received request on /api/generate_clippings ---")

    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for clippings")
        return "", 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        doc_id = data.get("docId")
        annotations = data.get("annotations", [])
        canvas_dimensions = data.get("canvasDimensions", {})

        if not doc_id:
            return jsonify({"error": "Document ID is required"}), 400

        print(f"🖼️  Generating clippings for document: {doc_id}")
        print(f"   -> Number of annotations: {len(annotations)}")
        print(f"   -> Canvas dimensions received: {canvas_dimensions}")

        # Debug: Print all annotations
        for i, annotation in enumerate(annotations):
            print(
                f"   -> Annotation {i+1}: {annotation['tag']} at ({annotation.get('left', 0):.1f}, {annotation.get('top', 0):.1f}) size {annotation.get('width', 0):.1f}x{annotation.get('height', 0):.1f} on page {annotation.get('pageNumber', 1)}"
            )

        doc_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        # Load page metadata
        metadata_file = os.path.join(doc_dir, "page_metadata.json")
        if not os.path.exists(metadata_file):
            return jsonify({"error": "Page metadata not found"}), 404

        import json

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        # Load original PDF
        original_pdf_path = os.path.join(doc_dir, "original.pdf")
        if not os.path.exists(original_pdf_path):
            return jsonify({"error": "Original PDF not found"}), 404

        doc = fitz.open(original_pdf_path)

        # Create clippings directory structure
        clippings_base_dir = os.path.join(doc_dir, "clippings")
        os.makedirs(clippings_base_dir, exist_ok=True)

        # Group annotations by page and type for sequential naming
        annotations_by_page = {}
        for annotation in annotations:
            page_num = annotation.get("pageNumber", 1)
            if page_num not in annotations_by_page:
                annotations_by_page[page_num] = {}

            tag = annotation["tag"]
            if tag not in annotations_by_page[page_num]:
                annotations_by_page[page_num][tag] = []

            annotations_by_page[page_num][tag].append(annotation)

        clipping_results = []

        for page_num, page_annotations_by_type in annotations_by_page.items():
            # Create page directory
            page_clippings_dir = os.path.join(clippings_base_dir, f"page{page_num}")
            os.makedirs(page_clippings_dir, exist_ok=True)

            for tag, tag_annotations in page_annotations_by_type.items():
                for i, annotation in enumerate(tag_annotations, 1):
                    canvas_coords = {
                        "left": annotation.get("left", 0),
                        "top": annotation.get("top", 0),
                        "width": annotation.get("width", 0),
                        "height": annotation.get("height", 0),
                    }

                    # Get canvas dimensions for this page - use actual canvas dimensions sent from frontend
                    canvas_width = canvas_dimensions.get(str(page_num), {}).get(
                        "width", 600
                    )
                    canvas_height = canvas_dimensions.get(str(page_num), {}).get(
                        "height", 800
                    )

                    print(f"   Processing {tag} {i} on page {page_num}")
                    print(
                        f"     Canvas coords: ({canvas_coords['left']:.1f}, {canvas_coords['top']:.1f}) {canvas_coords['width']:.1f}x{canvas_coords['height']:.1f}"
                    )
                    print(
                        f"     Canvas dimensions: {canvas_width:.1f}x{canvas_height:.1f}"
                    )

                    # Convert canvas coordinates to PDF coordinates using new system
                    from utils.coordinate_mapping import (
                        CanvasCoordinates,
                        CoordinateTransformer,
                        PageMetadata,
                    )

                    # Load page metadata using new format
                    page_metadata_dict = metadata["pages"][str(page_num)]
                    page_metadata = PageMetadata.from_dict(page_metadata_dict)

                    # Create coordinate transformer
                    transformer = CoordinateTransformer(page_metadata)

                    # Create canvas coordinates object
                    canvas_coord_obj = CanvasCoordinates(
                        left=canvas_coords["left"],
                        top=canvas_coords["top"],
                        width=canvas_coords["width"],
                        height=canvas_coords["height"],
                        canvas_width=canvas_width,
                        canvas_height=canvas_height,
                    )

                    # Transform to PDF coordinates
                    pdf_coord_obj = transformer.canvas_to_pdf(canvas_coord_obj)

                    # Convert to old format for generate_pdf_clipping function
                    pdf_coords = {
                        "left": pdf_coord_obj.left,
                        "top": pdf_coord_obj.top,
                        "width": pdf_coord_obj.width,
                        "height": pdf_coord_obj.height,
                    }

                    print(
                        f"     📄 PDF coords (NEW SYSTEM): ({pdf_coords['left']:.2f}, {pdf_coords['top']:.2f}) {pdf_coords['width']:.2f}x{pdf_coords['height']:.2f} points"
                    )
                    print(f"     🎯 Transformation analysis:")
                    print(
                        f"       Canvas → PDF successful: {pdf_coord_obj is not None}"
                    )
                    print(f"       Transformer used: {transformer.__class__.__name__}")
                    print(
                        f"       Page metadata: {page_metadata.pdf_width_points}x{page_metadata.pdf_height_points} @ {page_metadata.image_dpi} DPI"
                    )

                    # Generate high-res clipping with sequential naming
                    clipping_filename = f"{tag}_{i}.png"
                    clipping_path = generate_pdf_clipping(
                        doc,
                        page_num - 1,  # fitz uses 0-based indexing
                        pdf_coords,
                        page_clippings_dir,
                        clipping_filename.replace(".png", ""),
                    )

                    # Only add to results if clipping was successfully generated
                    if clipping_path is not None:
                        clipping_results.append(
                            {
                                "annotationId": annotation["id"],
                                "tag": annotation["tag"],
                                "pageNumber": page_num,
                                "canvasCoords": canvas_coords,
                                "pdfCoords": pdf_coords,
                                "clippingPath": clipping_path,
                                "relativeUrl": f"/data/processed/{doc_id}/clippings/page{page_num}/{clipping_filename}",
                            }
                        )
                    else:
                        print(
                            f"     ⚠️  Skipped clipping for {tag} {i} on page {page_num} (invalid coordinates)"
                        )
                        # Still add to results but mark as failed
                        clipping_results.append(
                            {
                                "annotationId": annotation["id"],
                                "tag": annotation["tag"],
                                "pageNumber": page_num,
                                "canvasCoords": canvas_coords,
                                "pdfCoords": pdf_coords,
                                "clippingPath": None,
                                "relativeUrl": None,
                                "error": "Invalid coordinates - annotation outside page bounds or too small",
                            }
                        )

        successful_count = len(
            [r for r in clipping_results if r.get("clippingPath") is not None]
        )
        failed_count = len(clipping_results) - successful_count

        print(
            f"   ✅ Processed {len(clipping_results)} annotations: {successful_count} successful, {failed_count} failed"
        )

        # Generate a debug overlay image showing where we think the annotations are
        try:
            # Filter out failed clippings for debug overlay
            successful_clippings = [
                r for r in clipping_results if r.get("clippingPath") is not None
            ]

            if successful_clippings:
                debug_overlay_path = generate_debug_overlay(
                    doc, successful_clippings, doc_dir
                )
                print(f"   🔍 Debug overlay generated: {debug_overlay_path}")

                # Generate a test clipping using the exact same coordinates as the debug overlay
                test_clipping_path = generate_test_clipping(
                    doc, successful_clippings, doc_dir
                )
                print(f"   🧪 Test clipping generated: {test_clipping_path}")
            else:
                print(f"   ⚠️  No successful clippings to generate debug overlay")
        except Exception as e:
            print(f"   ⚠️  Failed to generate debug overlay: {e}")

        doc.close()

        return (
            jsonify(
                {
                    "message": "Clippings generated successfully",
                    "docId": doc_id,
                    "clippings": clipping_results,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to generate clippings: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Old coordinate transformation function removed - replaced by new coordinate mapping system


def generate_pdf_clipping(doc, page_index, pdf_coords, output_dir, filename_prefix):
    """
    Generate a high-resolution clipping from the PDF.

    Both PyMuPDF and our coordinate system use top-left origin - no conversion needed!
    """
    page = doc.load_page(page_index)

    print(f"       🔍 CLIPPING DEBUG:")
    print(f"         Page rect: {page.rect}")
    print(
        f"         PDF coords (top-left): ({pdf_coords['left']:.1f}, {pdf_coords['top']:.1f}) {pdf_coords['width']:.1f}x{pdf_coords['height']:.1f}"
    )

    # Validate minimum dimensions before proceeding
    min_dimension = 1.0  # Minimum 1 point in each dimension
    if pdf_coords["width"] < min_dimension or pdf_coords["height"] < min_dimension:
        print(
            f"         ❌ INVALID: Annotation too small (width: {pdf_coords['width']:.1f}, height: {pdf_coords['height']:.1f})"
        )
        print(f"         Skipping clipping generation for invalid annotation")
        return None

    # No coordinate conversion needed - both systems use top-left origin
    mupdf_left = pdf_coords["left"]
    mupdf_top = pdf_coords["top"]
    mupdf_width = pdf_coords["width"]
    mupdf_height = pdf_coords["height"]

    print(
        f"         Direct coords (top-left): ({mupdf_left:.1f}, {mupdf_top:.1f}) {mupdf_width:.1f}x{mupdf_height:.1f}"
    )

    # Create clipping rectangle using MuPDF coordinates
    clip_rect = fitz.Rect(
        mupdf_left, mupdf_top, mupdf_left + mupdf_width, mupdf_top + mupdf_height
    )

    print(f"         Clip rect: {clip_rect}")

    # Validate the clipping rectangle is within page bounds and has valid dimensions
    page_rect = page.rect

    # First intersect with page bounds
    clipped_rect = clip_rect & page_rect
    print(f"         Intersected with page bounds: {clipped_rect}")

    # Check if the intersection resulted in a valid rectangle
    if (
        clipped_rect.is_empty
        or clipped_rect.width < min_dimension
        or clipped_rect.height < min_dimension
    ):
        print(
            f"         ❌ INVALID: Clipping rectangle is empty or too small after intersection"
        )
        print(f"         Final rect: {clipped_rect}")
        print(
            f"         Dimensions: {clipped_rect.width:.1f}x{clipped_rect.height:.1f}"
        )
        print(f"         Skipping clipping generation for out-of-bounds annotation")
        return None

    # Use the intersected rectangle for clipping
    clip_rect = clipped_rect

    try:
        # Generate high-resolution pixmap (300 DPI for high quality)
        matrix = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI scaling
        pix = page.get_pixmap(matrix=matrix, clip=clip_rect)

        # Validate pixmap dimensions before saving
        if pix.width <= 0 or pix.height <= 0:
            print(
                f"         ❌ INVALID: Generated pixmap has invalid dimensions: {pix.width}x{pix.height}"
            )
            return None

        # Save clipping
        output_path = os.path.join(output_dir, f"{filename_prefix}_clipping.png")
        pix.save(output_path)

        print(f"     ✅ Generated clipping: {output_path}")
        print(f"       Size: {pix.width}x{pix.height} px")
        print(
            f"       Actual clipped area: {clip_rect.width:.1f}x{clip_rect.height:.1f} pts"
        )

        return output_path

    except Exception as e:
        print(f"         ❌ FAILED to generate clipping: {e}")
        print(f"         Clip rect: {clip_rect}")
        print(f"         Dimensions: {clip_rect.width:.1f}x{clip_rect.height:.1f}")
        return None


def generate_debug_overlay(doc, clipping_results, doc_dir):
    """
    Generate a debug overlay showing where annotations were detected on the PDF.
    """
    if not clipping_results:
        return None

    # Group by page
    pages_with_annotations = {}
    for result in clipping_results:
        page_num = result["pageNumber"]
        if page_num not in pages_with_annotations:
            pages_with_annotations[page_num] = []
        pages_with_annotations[page_num].append(result)

    debug_dir = os.path.join(doc_dir, "debug")
    os.makedirs(debug_dir, exist_ok=True)

    for page_num, page_results in pages_with_annotations.items():
        page = doc.load_page(page_num - 1)  # fitz uses 0-based indexing

        # Create a high-res image of the full page
        matrix = fitz.Matrix(200 / 72, 200 / 72)  # 200 DPI
        pix = page.get_pixmap(matrix=matrix)

        # Convert to PIL Image for drawing
        from PIL import Image, ImageDraw, ImageFont
        import io

        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        draw = ImageDraw.Draw(img)

        # Draw rectangles for each annotation
        colors = ["red", "blue", "green", "orange", "purple", "yellow"]
        for i, result in enumerate(page_results):
            color = colors[i % len(colors)]
            pdf_coords = result["pdfCoords"]

            # Convert PDF coordinates to image coordinates
            left = pdf_coords["left"] * (200 / 72)  # Scale to 200 DPI
            top = (page.rect.height - pdf_coords["top"] - pdf_coords["height"]) * (
                200 / 72
            )  # Flip Y and scale
            right = left + (pdf_coords["width"] * (200 / 72))
            bottom = top + (pdf_coords["height"] * (200 / 72))

            # Draw rectangle
            draw.rectangle([left, top, right, bottom], outline=color, width=3)

            # Draw label
            label = (
                f"{result['tag']} ({pdf_coords['left']:.1f},{pdf_coords['top']:.1f})"
            )
            draw.text((left + 5, top + 5), label, fill=color)

        # Save debug image
        debug_path = os.path.join(debug_dir, f"page_{page_num}_debug.png")
        img.save(debug_path)
        print(f"     🔍 Debug overlay for page {page_num}: {debug_path}")

    return debug_dir


def generate_test_clipping(doc, clipping_results, doc_dir):
    """
    Generate a test clipping using the exact same coordinate logic as the debug overlay.
    This helps verify if the coordinate transformation is working correctly.
    """
    if not clipping_results:
        return None

    # Take the first clipping result for testing
    test_result = clipping_results[0]
    page_num = test_result["pageNumber"]
    pdf_coords = test_result["pdfCoords"]

    page = doc.load_page(page_num - 1)  # fitz uses 0-based indexing

    print(f"   🧪 TEST CLIPPING DEBUG:")
    print(f"     Page {page_num} rect: {page.rect}")
    print(
        f"     PDF coords from transform: ({pdf_coords['left']:.1f}, {pdf_coords['top']:.1f}) {pdf_coords['width']:.1f}x{pdf_coords['height']:.1f}"
    )

    # Use the EXACT same coordinate conversion as the debug overlay
    # Convert PDF coordinates to image coordinates for a 200 DPI test image
    left = pdf_coords["left"] * (200 / 72)  # Scale to 200 DPI
    top = (pdf_coords["top"] - pdf_coords["height"]) * (200 / 72)
    right = left + (pdf_coords["width"] * (200 / 72))
    bottom = top + (pdf_coords["height"] * (200 / 72))

    print(
        f"     Image coords for 200 DPI: ({left:.1f}, {top:.1f}) to ({right:.1f}, {bottom:.1f})"
    )

    # Create a full page image at 200 DPI
    matrix = fitz.Matrix(200 / 72, 200 / 72)  # 200 DPI
    pix = page.get_pixmap(matrix=matrix)

    # Convert to PIL Image
    from PIL import Image
    import io

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Crop the image using the calculated coordinates
    crop_box = (int(left), int(top), int(right), int(bottom))
    print(f"     Crop box: {crop_box}")

    try:
        cropped_img = img.crop(crop_box)

        # Save the test clipping
        test_dir = os.path.join(doc_dir, "test_clippings")
        os.makedirs(test_dir, exist_ok=True)

        test_path = os.path.join(test_dir, f"test_{test_result['tag']}_crop.png")
        cropped_img.save(test_path)

        print(f"     ✅ Test clipping saved: {test_path}")
        print(f"     Size: {cropped_img.size}")

        return test_path
    except Exception as e:
        print(f"     ❌ Failed to create test clipping: {e}")
        return None


@app.route("/data/processed/<path:path>")
def serve_processed_file(path):
    """
    Serves files from the processed data directory.
    """
    print(f"---  Serving file request: {path} ---")
    return send_from_directory(app.config["PROCESSED_FOLDER"], path)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
