"""
Detection update API endpoints for interactive canvas operations.

This module handles real-time updates to detection coordinates, status changes,
and adding/deleting detections from the interactive canvas.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
import sys

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.coordinate_mapping import (
    PDFCoordinates,
    ImageCoordinates,
    PageMetadata,
    CoordinateTransformer,
)
from utils.symbol_detection.detection_storage import DetectionStorage
from utils.symbol_detection.detection_coordinator import DetectionCoordinator

# Create blueprint for detection update API
detection_updates_bp = Blueprint("detection_updates", __name__)


@detection_updates_bp.route(
    "/api/update_detection_coordinates", methods=["POST", "OPTIONS"]
)
def update_detection_coordinates():
    """
    Update detection coordinates from canvas interactions.
    Handles coordinate transformation from canvas to PDF space.
    """
    print("\n--- Received request on /api/update_detection_coordinates ---")

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        # Extract parameters
        doc_id = data.get("docId")
        run_id = data.get("runId")
        detection_id = data.get("detectionId")
        pdf_coords = data.get("pdfCoords")  # Already in PDF coordinate space

        print(f"🔄 Updating detection coordinates:")
        print(f"   Document: {doc_id}")
        print(f"   Run: {run_id}")
        print(f"   Detection: {detection_id}")
        print(f"   New PDF coords: {pdf_coords}")

        if not all([doc_id, run_id, detection_id, pdf_coords]):
            return jsonify({"error": "Missing required parameters"}), 400

        # Get processed folder
        from flask import current_app

        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )

        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        # Create PDF coordinates object
        pdf_coords_obj = PDFCoordinates(
            left=pdf_coords["left_points"],
            top=pdf_coords["top_points"],
            width=pdf_coords["width_points"],
            height=pdf_coords["height_points"],
        )

        # Load page metadata for coordinate transformation
        page_metadata_file = os.path.join(doc_dir, "page_metadata.json")
        if not os.path.exists(page_metadata_file):
            return jsonify({"error": "Page metadata not found"}), 404

        with open(page_metadata_file, "r") as f:
            page_metadata_dict = json.load(f)

        # Update detection in storage
        detection_storage = DetectionStorage(doc_dir)

        # Load current detection to get page info
        detection_data = detection_storage.load_detection_by_id(run_id, detection_id)
        if not detection_data:
            return jsonify({"error": "Detection not found"}), 404

        # Calculate image coordinates from PDF coordinates
        page_num = detection_data.get("pageNumber", 1)
        page_metadata = PageMetadata.from_dict(
            page_metadata_dict["pages"][str(page_num)]
        )

        transformer = CoordinateTransformer(page_metadata)
        image_coords = transformer.pdf_to_image(pdf_coords_obj)

        # Update detection coordinates
        detection_storage.update_detection_coordinates(
            run_id, detection_id, pdf_coords_obj, image_coords
        )

        print(f"✅ Detection coordinates updated successfully")

        return jsonify(
            {
                "success": True,
                "detectionId": detection_id,
                "pdfCoords": pdf_coords_obj.to_dict(),
                "imageCoords": image_coords.to_dict(),
            }
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to update detection coordinates: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@detection_updates_bp.route("/api/update_detection_status", methods=["POST", "OPTIONS"])
@detection_updates_bp.route(
    "/api/update_detection_status_simple", methods=["POST", "OPTIONS"]
)
def update_detection_status():
    """
    Update the status of a detection (accept/reject/pending).
    """
    print("\n--- Received request on /api/update_detection_status ---")

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        # Extract parameters
        doc_id = data.get("docId")
        run_id = data.get("runId")
        detection_id = data.get("detectionId")
        new_status = data.get("status")  # "accepted", "rejected", "pending"

        print(f"🔄 Updating detection status:")
        print(f"   Document: {doc_id}")
        print(f"   Run: {run_id}")
        print(f"   Detection: {detection_id}")
        print(f"   New status: {new_status}")

        if not all([doc_id, run_id, detection_id, new_status]):
            return jsonify({"error": "Missing required parameters"}), 400

        if new_status not in ["accepted", "rejected", "pending"]:
            return jsonify({"error": "Invalid status"}), 400

        # Get processed folder
        from flask import current_app

        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )

        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        # Update detection status
        detection_storage = DetectionStorage(doc_dir)

        updates = [
            {
                "detectionId": detection_id,
                "action": (
                    "accept"
                    if new_status == "accepted"
                    else "reject" if new_status == "rejected" else "pending"
                ),
                "reviewedBy": "user",  # Could be enhanced with user auth
            }
        ]

        detection_storage.update_detection_status(run_id, updates)

        print(f"✅ Detection status updated successfully")

        return jsonify(
            {"success": True, "detectionId": detection_id, "status": new_status}
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to update detection status: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@detection_updates_bp.route("/api/add_user_detection", methods=["POST", "OPTIONS"])
def add_user_detection():
    """
    Add a new user-created detection to the canvas.
    """
    print("\n--- Received request on /api/add_user_detection ---")

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        # Extract parameters
        doc_id = data.get("docId")
        run_id = data.get("runId")
        symbol_id = data.get("symbolId")
        pdf_coords = data.get("pdfCoords")
        page_number = data.get("pageNumber", 1)

        print(f"➕ Adding user detection:")
        print(f"   Document: {doc_id}")
        print(f"   Run: {run_id}")
        print(f"   Symbol: {symbol_id}")
        print(f"   PDF coords: {pdf_coords}")
        print(f"   Page: {page_number}")

        if not all([doc_id, run_id, symbol_id, pdf_coords]):
            return jsonify({"error": "Missing required parameters"}), 400

        # Get processed folder
        from flask import current_app

        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )

        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        # Create PDF coordinates object
        pdf_coords_obj = PDFCoordinates(
            left=pdf_coords["left_points"],
            top=pdf_coords["top_points"],
            width=pdf_coords["width_points"],
            height=pdf_coords["height_points"],
        )

        # Load page metadata for coordinate transformation
        page_metadata_file = os.path.join(doc_dir, "page_metadata.json")
        if not os.path.exists(page_metadata_file):
            return jsonify({"error": "Page metadata not found"}), 404

        with open(page_metadata_file, "r") as f:
            page_metadata_dict = json.load(f)

        page_metadata = PageMetadata.from_dict(
            page_metadata_dict["pages"][str(page_number)]
        )
        transformer = CoordinateTransformer(page_metadata)
        image_coords = transformer.pdf_to_image(pdf_coords_obj)

        # Add user detection
        detection_storage = DetectionStorage(doc_dir)
        detection_id = detection_storage.add_user_detection(
            run_id, symbol_id, pdf_coords_obj, image_coords, page_number
        )

        print(f"✅ User detection added successfully: {detection_id}")

        return jsonify(
            {
                "success": True,
                "detectionId": detection_id,
                "pdfCoords": pdf_coords_obj.to_dict(),
                "imageCoords": image_coords.to_dict(),
            }
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to add user detection: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@detection_updates_bp.route("/api/delete_detection", methods=["POST", "OPTIONS"])
def delete_detection():
    """
    Delete a detection from the canvas.
    """
    print("\n--- Received request on /api/delete_detection ---")

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        # Extract parameters
        doc_id = data.get("docId")
        run_id = data.get("runId")
        detection_id = data.get("detectionId")

        print(f"🗑️ Deleting detection:")
        print(f"   Document: {doc_id}")
        print(f"   Run: {run_id}")
        print(f"   Detection: {detection_id}")

        if not all([doc_id, run_id, detection_id]):
            return jsonify({"error": "Missing required parameters"}), 400

        # Get processed folder
        from flask import current_app

        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )

        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        # Delete detection
        detection_storage = DetectionStorage(doc_dir)
        success = detection_storage.delete_detection(run_id, detection_id)

        if success:
            print(f"✅ Detection deleted successfully")
            return jsonify({"success": True, "detectionId": detection_id})
        else:
            return jsonify({"error": "Detection not found"}), 404

    except Exception as e:
        print(f"❌ ERROR: Failed to delete detection: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@detection_updates_bp.route(
    "/api/get_page_image/<doc_id>/<int:page_number>", methods=["GET"]
)
def get_page_image(doc_id, page_number):
    """
    Get page image for canvas display.
    """
    try:
        # Get processed folder
        from flask import current_app

        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )

        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404

        # Look for page image
        page_image_path = os.path.join(
            doc_dir, f"page_{page_number}", f"page_{page_number}_pixmap.png"
        )

        if not os.path.exists(page_image_path):
            return jsonify({"error": "Page image not found"}), 404

        # Return image path (relative to processed folder for frontend)
        relative_path = os.path.relpath(page_image_path, processed_folder)

        return jsonify(
            {"imagePath": f"/data/processed/{relative_path.replace(os.sep, '/')}"}
        )

    except Exception as e:
        print(f"❌ ERROR: Failed to get page image: {e}")
        return jsonify({"error": str(e)}), 500
