import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import fitz  # PyMuPDF

# --- Basic Flask App Setup ---
app = Flask(__name__)

# --- CORS Setup ---
# Configure CORS for development with specific origins
# Also allow credentials for more robust cross-origin requests
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    },
    r"/data/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

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
    Handles the PDF file upload and processes it into page images.
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

            # 3. Process the PDF
            doc_id = str(uuid.uuid4())
            output_dir = os.path.join(app.config["PROCESSED_FOLDER"], doc_id)
            os.makedirs(output_dir)
            print(f"   -> Created processing directory: {output_dir}")

            doc = fitz.open(temp_pdf_path)
            num_pages = len(doc)
            print(f"   -> PDF has {num_pages} pages. Starting conversion to PNG...")

            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=200)
                output_image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
                pix.save(output_image_path)
                print(f"     ✅ Saved page {page_num + 1} to {output_image_path}")

            doc.close()

            # 4. Clean up the temporary PDF
            os.remove(temp_pdf_path)
            print(f"   -> Cleaned up temporary file: {temp_pdf_path}")

            # 5. Return a success response
            print(
                "--- ✅ Successfully processed PDF. Sending response to frontend. ---"
            )
            return (
                jsonify(
                    {
                        "message": "File processed successfully",
                        "docId": doc_id,
                        "pageCount": num_pages,
                    }
                ),
                200,
            )

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
            "metadata": {
                "totalAnnotations": len(annotations),
                "annotationsByPage": {}
            }
        }
        
        # Group annotations by page for metadata
        for annotation in annotations:
            page = annotation.get("pageNumber", 1)
            if page not in annotation_data["metadata"]["annotationsByPage"]:
                annotation_data["metadata"]["annotationsByPage"][page] = 0
            annotation_data["metadata"]["annotationsByPage"][page] += 1
        
        # Write to file
        import json
        with open(annotations_file, 'w') as f:
            json.dump(annotation_data, f, indent=2)
        
        print(f"   ✅ Annotations saved to: {annotations_file}")
        
        return jsonify({
            "message": "Annotations saved successfully",
            "docId": doc_id,
            "annotationCount": len(annotations),
            "savedTo": annotations_file
        }), 200
        
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
            return jsonify({
                "docId": doc_id,
                "annotations": [],
                "message": "No annotations found"
            }), 200
        
        import json
        with open(annotations_file, 'r') as f:
            annotation_data = json.load(f)
        
        print(f"   ✅ Loaded {len(annotation_data.get('annotations', []))} annotations")
        
        return jsonify(annotation_data), 200
        
    except Exception as e:
        print(f"❌ ERROR: Failed to load annotations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/data/processed/<path:path>")
def serve_processed_file(path):
    """
    Serves files from the processed data directory.
    """
    print(f"---  Serving file request: {path} ---")
    return send_from_directory(app.config["PROCESSED_FOLDER"], path)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
