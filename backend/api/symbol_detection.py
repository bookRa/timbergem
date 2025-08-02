"""
API endpoints for symbol detection operations.

This module provides REST API endpoints for the symbol detection system,
including detection execution, progress monitoring, and result management.
"""

import os
import json
from flask import Blueprint, request, jsonify, current_app
from utils.symbol_detection import SymbolDetectionEngine, ProgressMonitor
import threading
import time

# Create blueprint for symbol detection API
symbol_detection_bp = Blueprint("symbol_detection", __name__)


@symbol_detection_bp.route("/api/run_symbol_detection", methods=["POST", "OPTIONS"])
def run_symbol_detection():
    """
    Execute symbol detection across pages for specified symbols.
    
    Request Body:
    {
        "docId": "uuid",
        "symbolIds": ["symbol_uuid_1", "symbol_uuid_2"],  // Optional: specific symbols
        "detectionParams": {
            "matchThreshold": 0.30,
            "iouThreshold": 0.32,
            "scaleVariancePx": 2,
            "rotationRange": [-1, 1],
            "rotationStep": 1
        }
    }
    
    Response:
    {
        "message": "Symbol detection started successfully",
        "runId": "detection_run_uuid",
        "docId": "uuid",
        "estimatedDuration": "2-5 minutes"
    }
    """
    
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        doc_id = data.get("docId")
        symbol_ids = data.get("symbolIds")  # Optional: specific symbols
        detection_params = data.get("detectionParams", {})
        
        if not doc_id:
            return jsonify({"error": "Document ID is required"}), 400
        
        print(f"🔍 Starting symbol detection for document: {doc_id}")
        if symbol_ids:
            print(f"   -> Detecting specific symbols: {symbol_ids}")
        else:
            print(f"   -> Detecting all symbols")
        
        print(f"   -> Detection parameters: {detection_params}")
        
        # Get processed folder path
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        # Validate document exists
        doc_dir = os.path.join(processed_folder, doc_id)
        if not os.path.exists(doc_dir):
            return jsonify({"error": "Document not found"}), 404
        
        # Create detection engine
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        
        # Start detection in background thread
        detection_thread = threading.Thread(
            target=_run_detection_background,
            args=(engine, symbol_ids, detection_params),
            daemon=True
        )
        detection_thread.start()
        
        # Get initial run ID (engine creates it synchronously)
        # We need to wait a moment for the thread to start and create the run
        time.sleep(0.1)
        
        # For now, we'll create a placeholder response
        # In a real implementation, we'd need to modify the engine to return the run ID immediately
        
        print(f"   ✅ Detection started in background thread")
        
        return jsonify({
            "message": "Symbol detection started successfully",
            "docId": doc_id,
            "status": "running",
            "estimatedDuration": "2-5 minutes depending on document size and number of symbols"
        }), 200
        
    except FileNotFoundError as e:
        print(f"❌ ERROR: File not found: {e}")
        return jsonify({"error": f"Required files not found: {str(e)}"}), 404
        
    except ValueError as e:
        print(f"❌ ERROR: Invalid parameters: {e}")
        return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        print(f"❌ ERROR: Failed to start symbol detection: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


def _run_detection_background(engine, symbol_ids, detection_params):
    """Run detection in background thread"""
    try:
        print(f"🔄 Background detection thread started")
        
        # Define progress callback
        def progress_callback(progress_summary):
            print(f"📊 Progress: {progress_summary.get('progressPercent', 0):.1f}% - {progress_summary.get('currentStep', 'Processing...')}")
        
        # Run detection
        run_id = engine.run_detection(symbol_ids, detection_params, progress_callback)
        print(f"✅ Background detection completed: {run_id}")
        
    except Exception as e:
        print(f"💥 Background detection failed: {e}")
        import traceback
        traceback.print_exc()


@symbol_detection_bp.route("/api/detection_progress/<doc_id>", methods=["GET"])
def get_detection_progress(doc_id):
    """
    Get real-time progress for the latest detection run of a document.
    
    Response:
    {
        "runId": "detection_run_uuid",
        "status": "running" | "completed" | "failed",
        "progressPercent": 75.5,
        "currentStep": "Processing symbol Valve on page 3/5",
        "estimatedTimeRemaining": "2m 30s",
        "processingRate": 0.25,
        "errorCount": 0,
        "warningCount": 1,
        "lastUpdated": "2024-01-01T12:30:45Z"
    }
    """
    
    try:
        print(f"📊 Getting detection progress for document: {doc_id}")
        
        # Get processed folder path
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        # Create detection engine to access storage
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        
        # Get list of detection runs (most recent first)
        runs_list = engine.list_detection_runs()
        
        if not runs_list:
            return jsonify({
                "message": "No detection runs found for this document",
                "docId": doc_id,
                "hasRuns": False
            }), 200
        
        # Get the most recent run
        latest_run = runs_list[0]
        run_id = latest_run["runId"]
        
        # Get detailed progress
        progress_data = engine.get_detection_progress(run_id)
        
        if not progress_data:
            return jsonify({
                "message": "Progress data not available",
                "docId": doc_id,
                "runId": run_id,
                "hasProgress": False
            }), 200
        
        # Return progress summary
        progress_summary = {
            "docId": doc_id,
            "runId": progress_data.get("runId"),
            "status": progress_data.get("status"),
            "progressPercent": progress_data.get("progressPercent", 0),
            "currentStep": progress_data.get("currentStep"),
            "estimatedTimeRemaining": progress_data.get("estimatedTimeRemaining"),
            "processingRate": progress_data.get("processingRate", 0),
            "completedSteps": progress_data.get("completedSteps", 0),
            "totalSteps": progress_data.get("totalSteps", 0),
            "errorCount": len(progress_data.get("errors", [])),
            "warningCount": len(progress_data.get("warnings", [])),
            "lastUpdated": progress_data.get("lastUpdated"),
            "hasProgress": True
        }
        
        return jsonify(progress_summary), 200
        
    except FileNotFoundError:
        return jsonify({"error": "Document not found"}), 404
        
    except Exception as e:
        print(f"❌ ERROR: Failed to get detection progress: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_detection_bp.route("/api/detection_results/<doc_id>", methods=["GET"])
def get_detection_results(doc_id):
    """
    Get detection results for the latest completed run of a document.
    
    Query Parameters:
    - runId: Specific run ID (optional, defaults to latest)
    - includeRejected: Include rejected detections (default: false)
    
    Response:
    {
        "docId": "uuid",
        "runId": "detection_run_uuid", 
        "status": "completed",
        "summary": {
            "totalDetections": 156,
            "acceptedCount": 120,
            "rejectedCount": 25,
            "pendingCount": 11,
            "symbolsProcessed": 5,
            "pagesProcessed": 12
        },
        "symbolResults": {
            "symbol_uuid_1": {
                "symbolInfo": {...},
                "detectionsByPage": {...},
                "summary": {...}
            }
        }
    }
    """
    
    try:
        run_id = request.args.get("runId")
        include_rejected = request.args.get("includeRejected", "false").lower() == "true"
        
        print(f"📋 Getting detection results for document: {doc_id}")
        if run_id:
            print(f"   -> Specific run: {run_id}")
        else:
            print(f"   -> Latest run")
        
        # Get processed folder path
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        # Create detection engine
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        
        # Get run ID if not specified
        if not run_id:
            runs_list = engine.list_detection_runs()
            if not runs_list:
                return jsonify({
                    "message": "No detection runs found",
                    "docId": doc_id,
                    "hasResults": False
                }), 200
            
            # Find the latest completed run
            completed_runs = [r for r in runs_list if r.get("status") == "completed"]
            if not completed_runs:
                return jsonify({
                    "message": "No completed detection runs found",
                    "docId": doc_id,
                    "hasResults": False,
                    "availableRuns": len(runs_list)
                }), 200
            
            run_id = completed_runs[0]["runId"]
        
        # Load detection results
        results = engine.load_detection_results(run_id)
        
        if not results:
            return jsonify({
                "error": "Detection results not found",
                "docId": doc_id,
                "runId": run_id
            }), 404
        
        # Filter results if requested
        if not include_rejected and "symbolDetections" in results:
            for symbol_id, symbol_data in results["symbolDetections"].items():
                if "detectionsByPage" in symbol_data:
                    for page_num, detections in symbol_data["detectionsByPage"].items():
                        # Filter out rejected detections
                        filtered_detections = [
                            d for d in detections 
                            if d.get("status") != "rejected"
                        ]
                        symbol_data["detectionsByPage"][page_num] = filtered_detections
        
        # Create response
        response = {
            "docId": doc_id,
            "runId": run_id,
            "status": results.get("status"),
            "summary": results.get("summary", {}),
            "symbolResults": results.get("symbolDetections", {}),
            "hasResults": True,
            "createdAt": results.get("createdAt"),
            "params": results.get("params", {})
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"❌ ERROR: Failed to get detection results: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_detection_bp.route("/api/update_detection_status", methods=["POST", "OPTIONS"])
def update_detection_status():
    """
    Update status of individual detections (accept/reject/modify).
    
    Request Body:
    {
        "docId": "uuid",
        "runId": "detection_run_uuid",
        "updates": [
            {
                "detectionId": "det_uuid",
                "action": "accept" | "reject" | "modify",
                "newCoords": {...},  // Required if action is "modify"
                "reviewedBy": "user_id"
            }
        ]
    }
    
    Response:
    {
        "message": "Detection status updated successfully",
        "updatedCount": 5,
        "docId": "uuid",
        "runId": "detection_run_uuid"
    }
    """
    
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        doc_id = data.get("docId")
        run_id = data.get("runId")
        updates = data.get("updates", [])
        
        if not all([doc_id, run_id, updates]):
            return jsonify({"error": "Missing required parameters: docId, runId, updates"}), 400
        
        print(f"🔄 Updating detection statuses for document: {doc_id}, run: {run_id}")
        print(f"   -> {len(updates)} updates to process")
        
        # Validate updates
        for i, update in enumerate(updates):
            required_fields = ["detectionId", "action"]
            for field in required_fields:
                if field not in update:
                    return jsonify({"error": f"Update {i}: Missing required field '{field}'"}), 400
            
            if update["action"] not in ["accept", "reject", "modify"]:
                return jsonify({"error": f"Update {i}: Invalid action '{update['action']}'"}), 400
            
            if update["action"] == "modify" and "newCoords" not in update:
                return jsonify({"error": f"Update {i}: 'newCoords' required for modify action"}), 400
        
        # Get processed folder path
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        # Create detection engine and apply updates
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        engine.update_detection_status(run_id, updates)
        
        print(f"   ✅ Successfully updated {len(updates)} detection statuses")
        
        return jsonify({
            "message": "Detection status updated successfully",
            "updatedCount": len(updates),
            "docId": doc_id,
            "runId": run_id
        }), 200
        
    except FileNotFoundError:
        return jsonify({"error": "Document or detection run not found"}), 404
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        print(f"❌ ERROR: Failed to update detection status: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_detection_bp.route("/api/detection_runs/<doc_id>", methods=["GET"])
def list_detection_runs(doc_id):
    """
    List all detection runs for a document.
    
    Response:
    {
        "docId": "uuid",
        "runs": [
            {
                "runId": "uuid",
                "createdAt": "2024-01-01T12:00:00Z",
                "status": "completed",
                "summary": {...},
                "symbolCount": 5
            }
        ]
    }
    """
    
    try:
        print(f"📋 Listing detection runs for document: {doc_id}")
        
        # Get processed folder path
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        # Create detection engine
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        
        # Get runs list
        runs = engine.list_detection_runs()
        
        return jsonify({
            "docId": doc_id,
            "runs": runs,
            "totalRuns": len(runs)
        }), 200
        
    except FileNotFoundError:
        return jsonify({"error": "Document not found"}), 404
        
    except Exception as e:
        print(f"❌ ERROR: Failed to list detection runs: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_detection_bp.route("/api/detection_runs/<doc_id>/<run_id>", methods=["DELETE"])
def delete_detection_run(doc_id, run_id):
    """
    Delete a specific detection run.
    
    Response:
    {
        "message": "Detection run deleted successfully",
        "docId": "uuid",
        "runId": "uuid"
    }
    """
    
    try:
        print(f"🗑️ Deleting detection run: {run_id} for document: {doc_id}")
        
        # Get processed folder path
        processed_folder = current_app.config.get("PROCESSED_FOLDER")
        if not processed_folder:
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
        
        # Create detection engine
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        
        # Delete the run
        success = engine.delete_detection_run(run_id)
        
        if success:
            return jsonify({
                "message": "Detection run deleted successfully",
                "docId": doc_id,
                "runId": run_id
            }), 200
        else:
            return jsonify({
                "error": "Detection run not found",
                "docId": doc_id,
                "runId": run_id
            }), 404
        
    except Exception as e:
        print(f"❌ ERROR: Failed to delete detection run: {e}")
        return jsonify({"error": str(e)}), 500


# Health check endpoint
@symbol_detection_bp.route("/api/detection_health", methods=["GET"])
def detection_health():
    """
    Health check endpoint for the detection system.
    
    Response:
    {
        "status": "healthy",
        "version": "1.0.0",
        "capabilities": [...],
        "systemInfo": {...}
    }
    """
    
    try:
        from utils.symbol_detection import __version__, __description__
        
        return jsonify({
            "status": "healthy",
            "service": "Symbol Detection API",
            "version": __version__,
            "description": __description__,
            "capabilities": [
                "Multi-symbol detection",
                "Real-time progress tracking", 
                "Result storage and retrieval",
                "Detection status management",
                "Coordinate transformation"
            ],
            "systemInfo": {
                "algorithmBase": "gem_v5 with IoU verification",
                "detectionDPI": 300,
                "coordinateSystem": "PDF points (single source of truth)",
                "supportedFormats": ["PDF"],
                "maxConcurrentRuns": 1  # Current limitation
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500