import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import fitz  # PyMuPDF

# --- Basic Flask App Setup ---
app = Flask(__name__)

# --- CORS Setup ---
# This is the crucial part. We allow requests from our frontend's origin.
# The '*' is a wildcard, but for development, explicitly naming the origin is good practice too.
# For simplicity, we'll allow all origins for now.
CORS(app, resources={r"/api/*": {"origins": "*"}})

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


@app.route("/api/upload", methods=["POST"])
def upload_and_process_pdf():
    """
    Handles the PDF file upload and processes it into page images.
    """
    print("\n--- Received request on /api/upload ---")

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


@app.route("/data/processed/<path:path>")
def serve_processed_file(path):
    """
    Serves files from the processed data directory.
    """
    print(f"---  Serving file request: {path} ---")
    return send_from_directory(app.config["PROCESSED_FOLDER"], path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
