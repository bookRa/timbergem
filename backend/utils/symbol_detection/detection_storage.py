"""
Detection result storage and persistence for TimberGem symbol detection.

This module handles the storage, retrieval, and management of detection results,
providing a clean interface for persisting detection runs and their outcomes.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import shutil

from .detection_algorithm import DetectionCandidate


class DetectionStorage:
    """
    Manages storage and retrieval of symbol detection results.
    
    This class provides a file-based storage system for detection runs,
    organizing results by document and detection run for easy retrieval
    and management.
    """
    
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
    
    def _initialize_runs_index(self):
        """Initialize the detection runs index file"""
        initial_index = {
            "version": "1.0",
            "created": datetime.now(timezone.utc).isoformat(),
            "runs": []
        }
        
        with open(self.runs_index_file, 'w') as f:
            json.dump(initial_index, f, indent=2)
    
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
                "avgIou": 0.0
            },
            "symbolResults": {}
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
        detections_by_page: Dict[int, List[DetectionCandidate]]
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
                    "reviewedBy": None
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
            "savedAt": datetime.now(timezone.utc).isoformat()
        }
        
        # Save symbol detection data
        symbol_file = os.path.join(symbol_dir, "detections.json")
        with open(symbol_file, 'w') as f:
            json.dump(symbol_data, f, indent=2)
        
        print(f"   📊 Saved {total_detections} detections across {len(detections_by_page)} pages")
        
        # Update run metadata with this symbol's results
        self._update_run_symbol_results(run_id, symbol_id, symbol_summary)
    
    def update_detection_status(self, run_id: str, detection_updates: List[Dict[str, Any]]):
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
        print(f"🔄 Updating {len(detection_updates)} detection statuses for run {run_id}")
        
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
        
        with open(metadata_file, 'r') as f:
            run_data = json.load(f)
        
        # Load all symbol detections
        symbol_detections = {}
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_id = item.replace("symbol_", "")
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    with open(symbol_file, 'r') as f:
                        symbol_detections[symbol_id] = json.load(f)
        
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
        
        with open(self.runs_index_file, 'r') as f:
            index_data = json.load(f)
        
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
            with open(self.runs_index_file, 'r') as f:
                index_data = json.load(f)
            
            index_data["runs"] = [r for r in index_data["runs"] if r["runId"] != run_id]
            
            with open(self.runs_index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        
        print(f"🗑️ Deleted detection run {run_id}")
        return True
    
    def _save_run_metadata(self, run_id: str, metadata: Dict[str, Any]):
        """Save run metadata to file"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _update_runs_index(self, run_id: str, run_metadata: Dict[str, Any]):
        """Update the runs index file"""
        if os.path.exists(self.runs_index_file):
            with open(self.runs_index_file, 'r') as f:
                runs_index = json.load(f)
        else:
            runs_index = {"version": "1.0", "runs": []}
        
        # Create run entry for index
        run_entry = {
            "runId": run_id,
            "createdAt": run_metadata["createdAt"],
            "status": run_metadata["status"],
            "summary": run_metadata["summary"].copy(),
            "symbolCount": len(run_metadata.get("params", {}).get("symbol_ids", []))
        }
        
        # Remove existing entry if it exists
        runs_index["runs"] = [r for r in runs_index["runs"] if r["runId"] != run_id]
        runs_index["runs"].append(run_entry)
        
        # Sort by creation date (newest first)
        runs_index["runs"].sort(key=lambda x: x["createdAt"], reverse=True)
        
        with open(self.runs_index_file, 'w') as f:
            json.dump(runs_index, f, indent=2)
    
    def _calculate_symbol_summary(
        self, 
        detections_by_page: Dict[str, List[Dict]], 
        confidence_scores: List[float], 
        iou_scores: List[float]
    ) -> Dict[str, Any]:
        """Calculate summary statistics for symbol detections"""
        total = sum(len(detections) for detections in detections_by_page.values())
        
        summary = {
            "totalDetections": total,
            "pagesWithDetections": len([p for p in detections_by_page.values() if len(p) > 0]),
            "acceptedCount": 0,
            "rejectedCount": 0,
            "pendingCount": total,
            "modifiedCount": 0
        }
        
        if confidence_scores:
            summary.update({
                "avgConfidence": sum(confidence_scores) / len(confidence_scores),
                "minConfidence": min(confidence_scores),
                "maxConfidence": max(confidence_scores)
            })
        else:
            summary.update({
                "avgConfidence": 0,
                "minConfidence": 0,
                "maxConfidence": 0
            })
        
        if iou_scores:
            summary.update({
                "avgIou": sum(iou_scores) / len(iou_scores),
                "minIou": min(iou_scores),
                "maxIou": max(iou_scores)
            })
        else:
            summary.update({
                "avgIou": 0,
                "minIou": 0,
                "maxIou": 0
            })
        
        return summary
    
    def _update_run_symbol_results(self, run_id: str, symbol_id: str, symbol_summary: Dict[str, Any]):
        """Update run metadata with symbol results"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")
        
        with open(metadata_file, 'r') as f:
            run_metadata = json.load(f)
        
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
        
        run_metadata["summary"].update({
            "totalDetections": total_detections,
            "symbolsWithDetections": symbols_with_detections,
            "avgConfidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "avgIou": sum(iou_scores) / len(iou_scores) if iou_scores else 0
        })
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(run_metadata, f, indent=2)
    
    def _find_symbol_for_detection(self, run_id: str, detection_id: str) -> Optional[str]:
        """Find which symbol a detection belongs to"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_id = item.replace("symbol_", "")
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    with open(symbol_file, 'r') as f:
                        symbol_data = json.load(f)
                    
                    # Search through all pages for this detection ID
                    for page_detections in symbol_data["detectionsByPage"].values():
                        for detection in page_detections:
                            if detection["detectionId"] == detection_id:
                                return symbol_id
        
        return None
    
    def _apply_symbol_detection_updates(self, run_id: str, symbol_id: str, updates: List[Dict[str, Any]]):
        """Apply updates to a symbol's detection file"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        symbol_file = os.path.join(run_dir, f"symbol_{symbol_id}", "detections.json")
        
        with open(symbol_file, 'r') as f:
            symbol_data = json.load(f)
        
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
                        elif action == "modify":
                            detection["status"] = "modified"
                            if "newCoords" in update:
                                detection["pdfCoords"] = update["newCoords"]
                        
                        detection["reviewedAt"] = datetime.now(timezone.utc).isoformat()
                        detection["reviewedBy"] = update.get("reviewedBy", "unknown")
                        break
        
        # Recalculate symbol summary
        symbol_data["summary"] = self._recalculate_symbol_summary(symbol_data["detectionsByPage"])
        
        # Save updated symbol data
        with open(symbol_file, 'w') as f:
            json.dump(symbol_data, f, indent=2)
    
    def _recalculate_symbol_summary(self, detections_by_page: Dict[str, List[Dict]]) -> Dict[str, Any]:
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
            "pagesWithDetections": len([p for p in detections_by_page.values() if len(p) > 0])
        }
    
    def _recalculate_run_summary(self, run_id: str):
        """Recalculate run summary statistics after status updates"""
        run_dir = os.path.join(self.detections_dir, f"run_{run_id}")
        metadata_file = os.path.join(run_dir, "run_metadata.json")
        
        with open(metadata_file, 'r') as f:
            run_metadata = json.load(f)
        
        # Reload all symbol data and recalculate
        total_accepted = 0
        total_rejected = 0
        total_pending = 0
        total_modified = 0
        
        for item in os.listdir(run_dir):
            if item.startswith("symbol_"):
                symbol_file = os.path.join(run_dir, item, "detections.json")
                if os.path.exists(symbol_file):
                    with open(symbol_file, 'r') as f:
                        symbol_data = json.load(f)
                    
                    summary = symbol_data["summary"]
                    total_accepted += summary.get("acceptedCount", 0)
                    total_rejected += summary.get("rejectedCount", 0)
                    total_pending += summary.get("pendingCount", 0)
                    total_modified += summary.get("modifiedCount", 0)
        
        # Update run summary
        run_metadata["summary"].update({
            "acceptedDetections": total_accepted,
            "rejectedDetections": total_rejected,
            "pendingDetections": total_pending,
            "modifiedDetections": total_modified
        })
        
        # Save updated run metadata
        with open(metadata_file, 'w') as f:
            json.dump(run_metadata, f, indent=2)
        
        # Update runs index
        self._update_runs_index(run_id, run_metadata)
    
    def complete_detection_run(self, run_id: str, success: bool = True, final_message: str = None):
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
        
        with open(metadata_file, 'r') as f:
            run_metadata = json.load(f)
        
        # Update status and completion info
        end_time = datetime.now(timezone.utc).isoformat()
        status = "completed" if success else "failed"
        
        run_metadata.update({
            "status": status,
            "endTime": end_time,
            "finalMessage": final_message or ("Detection completed successfully" if success else "Detection failed")
        })
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(run_metadata, f, indent=2)
        
        # Update runs index
        self._update_runs_index(run_id, run_metadata)
        
        print(f"✅ Detection run {run_id} marked as {status}")