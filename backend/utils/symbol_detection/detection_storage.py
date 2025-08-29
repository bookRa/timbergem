"""
Detection result storage and persistence for TimberGem symbol detection.

This module handles the storage, retrieval, and management of detection results,
providing a clean interface for persisting detection runs and their outcomes.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import asdict
import shutil
import threading

from .detection_algorithm import DetectionCandidate

if TYPE_CHECKING:
    from ..coordinate_mapping import PDFCoordinates, ImageCoordinates


class DetectionStorage:
    """
    Manages storage and retrieval of symbol detection results.

    This class provides a file-based storage system for detection runs,
    organizing results by document and detection run for easy retrieval
    and management.
    """

    # Process-local lock registry to protect JSON files from concurrent writes
    _lock_registry: Dict[str, threading.Lock] = {}
    _registry_guard = threading.Lock()

    def __init__(self, doc_dir: str):
        """
        Initialize detection storage for a specific document.

        Args:
            doc_dir: Path to the document's processed directory
        """
        self.doc_dir = doc_dir
        self.detections_dir = os.path.join(doc_dir, "symbols", "detections")
        self.runs_index_file = os.path.join(self.detections_dir, "detection_runs.json")

        # Ensure directories exist
        os.makedirs(self.detections_dir, exist_ok=True)

        # Initialize runs index if it doesn't exist
        if not os.path.exists(self.runs_index_file):
            self._initialize_runs_index()

    @classmethod
    def _get_path_lock(cls, path: str) -> threading.Lock:
        with cls._registry_guard:
            lock = cls._lock_registry.get(path)
            if lock is None:
                lock = threading.Lock()
                cls._lock_registry[path] = lock
            return lock

    @staticmethod
    def _atomic_write_json(file_path: str, data: Dict[str, Any]):
        tmp_path = file_path + ".tmp"
        backup_path = file_path + ".bak"
        try:
            if os.path.exists(file_path):
                try:
                    shutil.copyfile(file_path, backup_path)
                except Exception:
                    pass
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, file_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @staticmethod
    def _safe_load_json(file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception:
            backup_path = file_path + ".bak"
            if os.path.exists(backup_path):
                with open(backup_path, "r") as f:
                    return json.load(f)
            raise

    def _initialize_runs_index(self):
        """Initialize the detection runs index file"""
        initial_index = {
            "version": "1.0",
            "created": datetime.now(timezone.utc).isoformat(),
            "runs": [],
        }

        lock = self._get_path_lock(self.runs_index_file)
        with lock:
            self._atomic_write_json(self.runs_index_file, initial_index)

    def create_detection_run(self, run_params: Dict[str, Any]) -> str:
        """
        Create a new detection run and return run ID.

        Args:
            run_params: Detection run parameters including:
                - symbol_ids: List of symbol IDs to detect
                - detection_params: Algorithm parameters
                - total_symbols: Number of symbols to process
                - total_pages: Number of pages to process

        Returns:
            str: Unique run ID for this detection run
        """
        run_id = str(uuid.uuid4())
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        os.makedirs(run_dir, exist_ok=True)

        print(f"📁 Created detection run directory: {run_dir}")

        # Create run metadata
        run_metadata = {
            "runId": run_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "status": "initializing",
            "params": run_params,
            "summary": {
                "totalSymbols": run_params.get("total_symbols", 0),
                "totalPages": run_params.get("total_pages", 0),
                "totalDetections": 0,
                "completedSymbols": 0,
                "completedPages": 0,
                "symbolsWithDetections": 0,
                "avgConfidence": 0.0,
                "avgIou": 0.0,
            },
            "symbolResults": {},
        }

        # Save run metadata
        self._save_run_metadata(run_id, run_metadata)

        # Update runs index
        self._update_runs_index(run_id, run_metadata)

        print(f"✅ Detection run {run_id} created successfully")
        return run_id

    def save_symbol_detections(
        self,
        run_id: str,
        symbol_id: str,
        symbol_info: Dict[str, Any],
        detections_by_page: Dict[int, List[DetectionCandidate]],
    ):
        """
        Save detection results for a specific symbol.

        Args:
            run_id: Detection run ID
            symbol_id: Symbol identifier
            symbol_info: Symbol metadata
            detections_by_page: Detection results grouped by page number
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        symbol_dir = os.path.join(run_dir, f"symbol_{symbol_id}")
        os.makedirs(symbol_dir, exist_ok=True)

        print(f"💾 Saving detections for symbol {symbol_info.get('name', symbol_id)}")

        # Convert DetectionCandidate objects to serializable format
        serializable_detections = {}
        total_detections = 0
        confidence_scores = []
        iou_scores = []

        for page_num, detections in detections_by_page.items():
            page_detections = []
            for detection in detections:
                # Generate unique detection ID
                detection_dict = {
                    "detectionId": f"det_{uuid.uuid4()}",
                    "candidateId": detection.candidate_id,
                    "imageCoords": detection.image_coords.to_dict(),
                    "pdfCoords": detection.pdf_coords.to_dict(),
                    "matchConfidence": detection.match_confidence,
                    "iouScore": detection.iou_score,
                    "matchedAngle": detection.matched_angle,
                    "templateSize": detection.template_size,
                    "status": detection.status,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "reviewedAt": None,
                    "reviewedBy": None,
                }
                page_detections.append(detection_dict)
                total_detections += 1
                confidence_scores.append(detection.match_confidence)
                iou_scores.append(detection.iou_score)

            serializable_detections[str(page_num)] = page_detections

        # Calculate summary statistics
        symbol_summary = self._calculate_symbol_summary(
            serializable_detections, confidence_scores, iou_scores
        )

        symbol_data = {
            "symbolId": symbol_id,
            "symbolInfo": symbol_info,
            "detectionsByPage": serializable_detections,
            "summary": symbol_summary,
            "savedAt": datetime.now(timezone.utc).isoformat(),
        }

        # Save symbol detection data
        symbol_file = os.path.join(symbol_dir, "detections.json")
        lock = self._get_path_lock(symbol_file)
        with lock:
            self._atomic_write_json(symbol_file, symbol_data)

        print(
            f"   📊 Saved {total_detections} detections across {len(detections_by_page)} pages"
        )

        # Update run metadata with this symbol's results
        self._update_run_symbol_results(run_id, symbol_id, symbol_summary)

    def update_detection_status(
        self, run_id: str, detection_updates: List[Dict[str, Any]]
    ):
        """
        Update status of individual detections.

        Args:
            run_id: Detection run ID
            detection_updates: List of updates, each containing:
                - detectionId: ID of detection to update
                - action: "accept", "reject", or "modify"
                - newCoords: New coordinates if action is "modify"
                - reviewedBy: User who made the review
        """
        print(
            f"🔄 Updating {len(detection_updates)} detection statuses for run {run_id}"
        )

        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        if not os.path.exists(run_dir):
            raise ValueError(f"Detection run {run_id} not found")

        # Group updates by symbol
        updates_by_symbol = {}
        for update in detection_updates:
            detection_id = update["detectionId"]
            # Find which symbol this detection belongs to
            symbol_id = self._find_symbol_for_detection(run_id, detection_id)
            if symbol_id:
                if symbol_id not in updates_by_symbol:
                    updates_by_symbol[symbol_id] = []
                updates_by_symbol[symbol_id].append(update)

        # Apply updates to each symbol's detection file
        for symbol_id, symbol_updates in updates_by_symbol.items():
            self._apply_symbol_detection_updates(run_id, symbol_id, symbol_updates)

        # Update run summary statistics
        self._recalculate_run_summary(run_id)

        print(f"✅ Updated statuses for {len(detection_updates)} detections")

    def load_detection_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load complete detection run data.

        Args:
            run_id: Detection run ID

        Returns:
            Dict containing complete run data or None if not found
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        if not os.path.exists(run_dir):
            return None

        # Load run metadata
        metadata_file = os.path.join(run_dir, "run_metadata.json")
        if not os.path.exists(metadata_file):
            return None

        lock = self._get_path_lock(metadata_file)
        with lock:
            run_data = self._safe_load_json(metadata_file)

        # Load all symbol detections
        symbol_detections = {}
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_id = item.replace("symbol_", "")
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    s_lock = self._get_path_lock(symbol_file)
                    with s_lock:
                        symbol_detections[symbol_id] = self._safe_load_json(symbol_file)

        run_data["symbolDetections"] = symbol_detections
        return run_data

    def list_detection_runs(self) -> List[Dict[str, Any]]:
        """
        List all detection runs for this document.

        Returns:
            List of run summaries
        """
        if not os.path.exists(self.runs_index_file):
            return []

        lock = self._get_path_lock(self.runs_index_file)
        with lock:
            index_data = self._safe_load_json(self.runs_index_file)

        return index_data.get("runs", [])

    def delete_detection_run(self, run_id: str) -> bool:
        """
        Delete a detection run and all its data.

        Args:
            run_id: Detection run ID

        Returns:
            bool: True if deleted successfully, False if not found
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        if not os.path.exists(run_dir):
            return False

        # Remove run directory
        shutil.rmtree(run_dir)

        # Remove from runs index
        if os.path.exists(self.runs_index_file):
            lock = self._get_path_lock(self.runs_index_file)
            with lock:
                index_data = self._safe_load_json(self.runs_index_file)

            index_data["runs"] = [r for r in index_data["runs"] if r["runId"] != run_id]

            with lock:
                self._atomic_write_json(self.runs_index_file, index_data)

        print(f"🗑️ Deleted detection run {run_id}")
        return True

    def _save_run_metadata(self, run_id: str, metadata: Dict[str, Any]):
        """Save run metadata to file"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def _update_runs_index(self, run_id: str, run_metadata: Dict[str, Any]):
        """Update the runs index file"""
        if os.path.exists(self.runs_index_file):
            lock = self._get_path_lock(self.runs_index_file)
            with lock:
                runs_index = self._safe_load_json(self.runs_index_file)
        else:
            runs_index = {"version": "1.0", "runs": []}

        # Create run entry for index
        run_entry = {
            "runId": run_id,
            "createdAt": run_metadata["createdAt"],
            "status": run_metadata["status"],
            "summary": run_metadata["summary"].copy(),
            "symbolCount": len(run_metadata.get("params", {}).get("symbol_ids", [])),
        }

        # Remove existing entry if it exists
        runs_index["runs"] = [r for r in runs_index["runs"] if r["runId"] != run_id]
        runs_index["runs"].append(run_entry)

        # Sort by creation date (newest first)
        runs_index["runs"].sort(key=lambda x: x["createdAt"], reverse=True)

        lock = self._get_path_lock(self.runs_index_file)
        with lock:
            self._atomic_write_json(self.runs_index_file, runs_index)

    def _calculate_symbol_summary(
        self,
        detections_by_page: Dict[str, List[Dict]],
        confidence_scores: List[float],
        iou_scores: List[float],
    ) -> Dict[str, Any]:
        """Calculate summary statistics for symbol detections"""
        total = sum(len(detections) for detections in detections_by_page.values())

        summary = {
            "totalDetections": total,
            "pagesWithDetections": len(
                [p for p in detections_by_page.values() if len(p) > 0]
            ),
            "acceptedCount": 0,
            "rejectedCount": 0,
            "pendingCount": total,
            "modifiedCount": 0,
        }

        if confidence_scores:
            summary.update(
                {
                    "avgConfidence": sum(confidence_scores) / len(confidence_scores),
                    "minConfidence": min(confidence_scores),
                    "maxConfidence": max(confidence_scores),
                }
            )
        else:
            summary.update({"avgConfidence": 0, "minConfidence": 0, "maxConfidence": 0})

        if iou_scores:
            summary.update(
                {
                    "avgIou": sum(iou_scores) / len(iou_scores),
                    "minIou": min(iou_scores),
                    "maxIou": max(iou_scores),
                }
            )
        else:
            summary.update({"avgIou": 0, "minIou": 0, "maxIou": 0})

        return summary

    def _update_run_symbol_results(
        self, run_id: str, symbol_id: str, symbol_summary: Dict[str, Any]
    ):
        """Update run metadata with symbol results"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")

        lock = self._get_path_lock(metadata_file)
        with lock:
            run_metadata = self._safe_load_json(metadata_file)

        # Update symbol results
        run_metadata["symbolResults"][symbol_id] = symbol_summary
        run_metadata["summary"]["completedSymbols"] += 1

        # Recalculate overall statistics
        total_detections = sum(
            s["totalDetections"] for s in run_metadata["symbolResults"].values()
        )

        confidence_scores = []
        iou_scores = []
        symbols_with_detections = 0

        for symbol_result in run_metadata["symbolResults"].values():
            if symbol_result["totalDetections"] > 0:
                symbols_with_detections += 1
                # Weight by number of detections
                weight = symbol_result["totalDetections"]
                confidence_scores.extend([symbol_result["avgConfidence"]] * weight)
                iou_scores.extend([symbol_result["avgIou"]] * weight)

        run_metadata["summary"].update(
            {
                "totalDetections": total_detections,
                "symbolsWithDetections": symbols_with_detections,
                "avgConfidence": (
                    sum(confidence_scores) / len(confidence_scores)
                    if confidence_scores
                    else 0
                ),
                "avgIou": sum(iou_scores) / len(iou_scores) if iou_scores else 0,
            }
        )

        # Save updated metadata
        with lock:
            self._atomic_write_json(metadata_file, run_metadata)

    def _find_symbol_for_detection(
        self, run_id: str, detection_id: str
    ) -> Optional[str]:
        """Find which symbol a detection belongs to"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")

        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_id = item.replace("symbol_", "")
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    lock = self._get_path_lock(symbol_file)
                    with lock:
                        symbol_data = self._safe_load_json(symbol_file)

                    # Search through all pages for this detection ID
                    for page_detections in symbol_data["detectionsByPage"].values():
                        for detection in page_detections:
                            if detection["detectionId"] == detection_id:
                                return symbol_id

        return None

    def _apply_symbol_detection_updates(
        self, run_id: str, symbol_id: str, updates: List[Dict[str, Any]]
    ):
        """Apply updates to a symbol's detection file"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        symbol_file = os.path.join(run_dir, f"symbol_{symbol_id}", "detections.json")

        lock = self._get_path_lock(symbol_file)
        with lock:
            symbol_data = self._safe_load_json(symbol_file)

        # Apply each update
        for update in updates:
            detection_id = update["detectionId"]
            action = update["action"]

            # Find and update the detection
            for page_detections in symbol_data["detectionsByPage"].values():
                for detection in page_detections:
                    if detection["detectionId"] == detection_id:
                        if action == "accept":
                            detection["status"] = "accepted"
                        elif action == "reject":
                            detection["status"] = "rejected"
                        elif action == "pending":
                            detection["status"] = "pending"
                        elif action == "modify":
                            detection["status"] = "modified"
                            if "newCoords" in update:
                                detection["pdfCoords"] = update["newCoords"]

                        detection["reviewedAt"] = datetime.now(timezone.utc).isoformat()
                        detection["reviewedBy"] = update.get("reviewedBy", "unknown")
                        break

        # Recalculate symbol summary
        symbol_data["summary"] = self._recalculate_symbol_summary(
            symbol_data["detectionsByPage"]
        )

        # Save updated symbol data
        with lock:
            self._atomic_write_json(symbol_file, symbol_data)

    def _recalculate_symbol_summary(
        self, detections_by_page: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """Recalculate symbol summary after status updates"""
        total = 0
        accepted = 0
        rejected = 0
        pending = 0
        modified = 0

        for page_detections in detections_by_page.values():
            for detection in page_detections:
                total += 1
                status = detection["status"]
                if status == "accepted":
                    accepted += 1
                elif status == "rejected":
                    rejected += 1
                elif status == "modified":
                    modified += 1
                else:
                    pending += 1

        return {
            "totalDetections": total,
            "acceptedCount": accepted,
            "rejectedCount": rejected,
            "pendingCount": pending,
            "modifiedCount": modified,
            "pagesWithDetections": len(
                [p for p in detections_by_page.values() if len(p) > 0]
            ),
        }

    def _recalculate_run_summary(self, run_id: str):
        """Recalculate run summary statistics after status updates"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")

        lock = self._get_path_lock(metadata_file)
        with lock:
            run_metadata = self._safe_load_json(metadata_file)

        # Reload all symbol data and recalculate
        total_accepted = 0
        total_rejected = 0
        total_pending = 0
        total_modified = 0

        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    lock = self._get_path_lock(symbol_file)
                    with lock:
                        symbol_data = self._safe_load_json(symbol_file)

                    summary = symbol_data["summary"]
                    total_accepted += summary.get("acceptedCount", 0)
                    total_rejected += summary.get("rejectedCount", 0)
                    total_pending += summary.get("pendingCount", 0)
                    total_modified += summary.get("modifiedCount", 0)

        # Update run summary
        run_metadata["summary"].update(
            {
                "acceptedDetections": total_accepted,
                "rejectedDetections": total_rejected,
                "pendingDetections": total_pending,
                "modifiedDetections": total_modified,
            }
        )

        # Save updated run metadata
        with lock:
            self._atomic_write_json(metadata_file, run_metadata)

        # Update runs index
        self._update_runs_index(run_id, run_metadata)

    def complete_detection_run(
        self, run_id: str, success: bool = True, final_message: str = None
    ):
        """
        Mark a detection run as completed or failed.

        Args:
            run_id: Detection run ID
            success: Whether the detection completed successfully
            final_message: Optional final status message
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")

        if not os.path.exists(metadata_file):
            print(f"❌ Run metadata not found for run {run_id}")
            return

        lock = self._get_path_lock(metadata_file)
        with lock:
            run_metadata = self._safe_load_json(metadata_file)

        # Update status and completion info
        end_time = datetime.now(timezone.utc).isoformat()
        status = "completed" if success else "failed"

        run_metadata.update(
            {
                "status": status,
                "endTime": end_time,
                "finalMessage": final_message
                or (
                    "Detection completed successfully"
                    if success
                    else "Detection failed"
                ),
            }
        )

        # Save updated metadata
        with lock:
            self._atomic_write_json(metadata_file, run_metadata)

        # Update runs index
        self._update_runs_index(run_id, run_metadata)

        print(f"✅ Detection run {run_id} marked as {status}")

    def load_detection_by_id(
        self, run_id: str, detection_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load a specific detection by ID.

        Args:
            run_id: Detection run ID
            detection_id: Specific detection ID

        Returns:
            Detection data or None if not found
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        if not os.path.exists(run_dir):
            return None

        # Search through all symbol files for the detection
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    lock = self._get_path_lock(symbol_file)
                    with lock:
                        symbol_data = self._safe_load_json(symbol_file)

                    # Search through all pages for the detection
                    for page_detections in symbol_data["detectionsByPage"].values():
                        for detection in page_detections:
                            if detection["detectionId"] == detection_id:
                                return detection

        return None

    def update_detection_coordinates(
        self,
        run_id: str,
        detection_id: str,
        pdf_coords: "PDFCoordinates",
        image_coords: "ImageCoordinates",
    ):
        """
        Update detection coordinates from canvas interactions.

        Args:
            run_id: Detection run ID
            detection_id: Detection ID to update
            pdf_coords: New PDF coordinates
            image_coords: New image coordinates
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        if not os.path.exists(run_dir):
            raise ValueError(f"Detection run {run_id} not found")

        # Find and update the detection
        updated = False
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    lock = self._get_path_lock(symbol_file)
                    with lock:
                        symbol_data = self._safe_load_json(symbol_file)

                    # Search and update detection
                    for page_detections in symbol_data["detectionsByPage"].values():
                        for detection in page_detections:
                            if detection["detectionId"] == detection_id:
                                # Update coordinates
                                detection["pdfCoords"] = pdf_coords.to_dict()
                                detection["imageCoords"] = image_coords.to_dict()
                                detection["isUserModified"] = True
                                detection["modifiedAt"] = datetime.now(
                                    timezone.utc
                                ).isoformat()

                                # Save updated data atomically with lock
                                with lock:
                                    self._atomic_write_json(symbol_file, symbol_data)

                                updated = True
                                break

                    if updated:
                        break

        if not updated:
            raise ValueError(f"Detection {detection_id} not found in run {run_id}")

        # Recalculate run summary
        self._recalculate_run_summary(run_id)

    def add_user_detection(
        self,
        run_id: str,
        symbol_id: str,
        pdf_coords: "PDFCoordinates",
        image_coords: "ImageCoordinates",
        page_number: int,
    ) -> str:
        """
        Add a new user-created detection.

        Args:
            run_id: Detection run ID
            symbol_id: Symbol ID this detection belongs to
            pdf_coords: PDF coordinates of the detection
            image_coords: Image coordinates of the detection
            page_number: Page number where detection was added

        Returns:
            New detection ID
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        symbol_dir = os.path.join(run_dir, f"symbol_{symbol_id}")
        symbol_file = os.path.join(symbol_dir, "detections.json")

        if not os.path.exists(symbol_file):
            raise ValueError(f"Symbol {symbol_id} not found in run {run_id}")

        # Load current symbol data
        lock = self._get_path_lock(symbol_file)
        with lock:
            symbol_data = self._safe_load_json(symbol_file)

        # Generate new detection ID
        detection_id = f"user_{uuid.uuid4()}"

        # Create new detection object
        new_detection = {
            "detectionId": detection_id,
            "candidateId": -1,  # User-added marker
            "imageCoords": image_coords.to_dict(),
            "pdfCoords": pdf_coords.to_dict(),
            "matchConfidence": 1.0,  # User confidence
            "iouScore": 1.0,
            "matchedAngle": 0,
            "templateSize": [image_coords.width, image_coords.height],
            "status": "pending",
            "isUserAdded": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "reviewedAt": None,
            "reviewedBy": None,
        }

        # Add to appropriate page
        page_key = str(page_number)
        if page_key not in symbol_data["detectionsByPage"]:
            symbol_data["detectionsByPage"][page_key] = []

        symbol_data["detectionsByPage"][page_key].append(new_detection)

        # Update summary
        symbol_data["summary"]["totalDetections"] += 1
        symbol_data["summary"]["pendingCount"] += 1

        # Save updated data
        with lock:
            self._atomic_write_json(symbol_file, symbol_data)

        # Recalculate run summary
        self._recalculate_run_summary(run_id)

        return detection_id

    def delete_detection(self, run_id: str, detection_id: str) -> bool:
        """
        Delete a detection.

        Args:
            run_id: Detection run ID
            detection_id: Detection ID to delete

        Returns:
            True if deleted, False if not found
        """
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        if not os.path.exists(run_dir):
            return False

        # Find and delete the detection
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    with open(symbol_file, "r") as f:
                        symbol_data = json.load(f)

                    # Search and remove detection
                    for page_key, page_detections in symbol_data[
                        "detectionsByPage"
                    ].items():
                        for i, detection in enumerate(page_detections):
                            if detection["detectionId"] == detection_id:
                                # Remove detection
                                removed_detection = page_detections.pop(i)

                                # Update summary
                                symbol_data["summary"]["totalDetections"] -= 1

                                # Update status counts
                                status = removed_detection.get("status", "pending")
                                if status == "pending":
                                    symbol_data["summary"]["pendingCount"] -= 1
                                elif status == "accepted":
                                    symbol_data["summary"]["acceptedCount"] -= 1
                                elif status == "rejected":
                                    symbol_data["summary"]["rejectedCount"] -= 1

                                # Save updated data
                                with open(symbol_file, "w") as f:
                                    json.dump(symbol_data, f, indent=2)

                                # Recalculate run summary
                                self._recalculate_run_summary(run_id)

                                return True

        return False
