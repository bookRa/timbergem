"""
Real-time progress tracking for symbol detection operations.

This module provides detailed progress tracking for long-running detection
operations, allowing the UI to show real-time updates and estimated completion times.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import time


class DetectionProgress:
    """
    Manages real-time progress tracking for detection operations.
    
    This class provides thread-safe progress tracking that can be monitored
    by the UI for real-time updates during long-running detection processes.
    """
    
    def __init__(self, run_id: str, run_dir: str):
        """
        Initialize progress tracking for a detection run.
        
        Args:
            run_id: Unique identifier for the detection run
            run_dir: Directory where progress file will be stored
        """
        self.run_id = run_id
        self.run_dir = run_dir
        self.progress_file = os.path.join(run_dir, "progress.json")
        self.lock = threading.Lock()
        
        # Initialize progress tracking
        self.progress_data = {
            "runId": run_id,
            "status": "initializing",
            "startTime": datetime.now(timezone.utc).isoformat(),
            "endTime": None,
            "currentStep": "Initializing detection process...",
            "totalSteps": 0,
            "completedSteps": 0,
            "progressPercent": 0.0,
            "currentSymbol": None,
            "currentPage": None,
            "estimatedTimeRemaining": None,
            "processingRate": 0.0,  # Steps per second
            "symbolProgress": {},
            "pageProgress": {},
            "errors": [],
            "warnings": [],
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
        self._save_progress()
        
        print(f"📊 Progress tracking initialized for run {run_id}")
    
    def start_detection(self, total_symbols: int, total_pages: int, symbol_names: List[str] = None):
        """
        Initialize detection progress tracking with total counts.
        
        Args:
            total_symbols: Total number of symbols to process
            total_pages: Total number of pages to process
            symbol_names: Optional list of symbol names for better tracking
        """
        with self.lock:
            self.progress_data.update({
                "status": "running",
                "totalSteps": total_symbols * total_pages,
                "totalSymbols": total_symbols,
                "totalPages": total_pages,
                "currentStep": f"Starting detection for {total_symbols} symbols across {total_pages} pages...",
                "symbolNames": symbol_names or []
            })
            
            # Initialize symbol progress tracking
            if symbol_names:
                self.progress_data["symbolProgress"] = {
                    name: {
                        "status": "pending",
                        "completedPages": 0,
                        "totalDetections": 0,
                        "startTime": None,
                        "endTime": None
                    } for name in symbol_names
                }
            
            # Initialize page progress tracking
            self.progress_data["pageProgress"] = {
                str(page): {
                    "completedSymbols": 0,
                    "totalDetections": 0,
                    "status": "pending"
                } for page in range(1, total_pages + 1)
            }
            
            self._save_progress()
        
        print(f"🚀 Detection started: {total_symbols} symbols × {total_pages} pages = {total_symbols * total_pages} total operations")
    
    def start_symbol_processing(self, symbol_name: str, symbol_index: int, total_symbols: int):
        """
        Update progress when starting to process a new symbol.
        
        Args:
            symbol_name: Name of the symbol being processed
            symbol_index: 0-based index of current symbol
            total_symbols: Total number of symbols
        """
        with self.lock:
            self.progress_data.update({
                "currentSymbol": symbol_name,
                "currentPage": None,
                "currentStep": f"Processing symbol {symbol_index + 1}/{total_symbols}: {symbol_name}"
            })
            
            # Update symbol progress
            if symbol_name in self.progress_data["symbolProgress"]:
                self.progress_data["symbolProgress"][symbol_name].update({
                    "status": "processing",
                    "startTime": datetime.now(timezone.utc).isoformat()
                })
            
            self._update_timestamps()
            self._save_progress()
        
        print(f"🔧 Processing symbol: {symbol_name} ({symbol_index + 1}/{total_symbols})")
    
    def update_page_progress(self, page_num: int, detections_found: int, total_pages: int):
        """
        Update progress when completing a page for the current symbol.
        
        Args:
            page_num: Page number being processed
            detections_found: Number of detections found on this page
            total_pages: Total number of pages
        """
        with self.lock:
            current_symbol = self.progress_data.get("currentSymbol")
            
            self.progress_data.update({
                "currentPage": page_num,
                "currentStep": f"Page {page_num}/{total_pages} - Found {detections_found} detections"
            })
            
            # Update page progress
            page_key = str(page_num)
            if page_key in self.progress_data["pageProgress"]:
                self.progress_data["pageProgress"][page_key]["completedSymbols"] += 1
                self.progress_data["pageProgress"][page_key]["totalDetections"] += detections_found
                
                # Mark page as completed if all symbols processed
                if self.progress_data["pageProgress"][page_key]["completedSymbols"] >= self.progress_data.get("totalSymbols", 0):
                    self.progress_data["pageProgress"][page_key]["status"] = "completed"
            
            # Update symbol progress
            if current_symbol and current_symbol in self.progress_data["symbolProgress"]:
                self.progress_data["symbolProgress"][current_symbol]["completedPages"] += 1
                self.progress_data["symbolProgress"][current_symbol]["totalDetections"] += detections_found
            
            self._update_timestamps()
            self._save_progress()
    
    def complete_step(self):
        """Mark a detection step as completed and update progress calculations"""
        with self.lock:
            self.progress_data["completedSteps"] += 1
            self._calculate_progress()
            self._update_timestamps()
            self._save_progress()
    
    def complete_symbol_processing(self, symbol_name: str, total_detections: int):
        """
        Mark symbol processing as complete.
        
        Args:
            symbol_name: Name of the completed symbol
            total_detections: Total detections found for this symbol
        """
        with self.lock:
            if symbol_name in self.progress_data["symbolProgress"]:
                self.progress_data["symbolProgress"][symbol_name].update({
                    "status": "completed",
                    "endTime": datetime.now(timezone.utc).isoformat(),
                    "totalDetections": total_detections
                })
            
            completed_symbols = sum(
                1 for s in self.progress_data["symbolProgress"].values() 
                if s["status"] == "completed"
            )
            
            self.progress_data["currentStep"] = f"Completed {symbol_name} - {total_detections} detections found"
            
            self._update_timestamps()
            self._save_progress()
        
        print(f"✅ Completed symbol: {symbol_name} ({total_detections} detections)")
    
    def add_error(self, error_message: str, context: Dict[str, Any] = None):
        """
        Add an error to the progress tracking.
        
        Args:
            error_message: Description of the error
            context: Additional context information
        """
        with self.lock:
            error_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "error",
                "message": error_message,
                "context": context or {}
            }
            self.progress_data["errors"].append(error_entry)
            
            # Keep only last 50 errors to prevent file bloat
            if len(self.progress_data["errors"]) > 50:
                self.progress_data["errors"] = self.progress_data["errors"][-50:]
            
            self._update_timestamps()
            self._save_progress()
        
        print(f"❌ Error logged: {error_message}")
    
    def add_warning(self, warning_message: str, context: Dict[str, Any] = None):
        """
        Add a warning to the progress tracking.
        
        Args:
            warning_message: Description of the warning
            context: Additional context information
        """
        with self.lock:
            warning_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "warning",
                "message": warning_message,
                "context": context or {}
            }
            self.progress_data["warnings"].append(warning_entry)
            
            # Keep only last 50 warnings
            if len(self.progress_data["warnings"]) > 50:
                self.progress_data["warnings"] = self.progress_data["warnings"][-50:]
            
            self._update_timestamps()
            self._save_progress()
        
        print(f"⚠️ Warning logged: {warning_message}")
    
    def complete_detection(self, success: bool = True, final_message: str = None):
        """
        Mark the entire detection process as completed.
        
        Args:
            success: Whether the detection completed successfully
            final_message: Optional final status message
        """
        with self.lock:
            end_time = datetime.now(timezone.utc).isoformat()
            
            if success:
                status = "completed"
                if not final_message:
                    total_detections = sum(
                        s.get("totalDetections", 0) 
                        for s in self.progress_data["symbolProgress"].values()
                    )
                    final_message = f"Detection completed successfully - {total_detections} total detections found"
            else:
                status = "failed"
                if not final_message:
                    final_message = "Detection failed - see errors for details"
            
            self.progress_data.update({
                "status": status,
                "endTime": end_time,
                "progressPercent": 100.0 if success else self.progress_data["progressPercent"],
                "currentStep": final_message,
                "currentSymbol": None,
                "currentPage": None
            })
            
            self._calculate_final_statistics()
            self._update_timestamps()
            self._save_progress()
        
        print(f"🏁 Detection {'completed' if success else 'failed'}: {final_message}")
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress data.
        
        Returns:
            Dict containing complete progress information
        """
        with self.lock:
            return self.progress_data.copy()
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a lightweight progress summary for quick updates.
        
        Returns:
            Dict containing essential progress information
        """
        with self.lock:
            return {
                "runId": self.progress_data["runId"],
                "status": self.progress_data["status"],
                "progressPercent": self.progress_data["progressPercent"],
                "currentStep": self.progress_data["currentStep"],
                "estimatedTimeRemaining": self.progress_data["estimatedTimeRemaining"],
                "processingRate": self.progress_data["processingRate"],
                "completedSteps": self.progress_data["completedSteps"],
                "totalSteps": self.progress_data["totalSteps"],
                "errorCount": len(self.progress_data["errors"]),
                "warningCount": len(self.progress_data["warnings"]),
                "lastUpdated": self.progress_data["lastUpdated"]
            }
    
    def _calculate_progress(self):
        """Calculate current progress percentage and estimated time"""
        if self.progress_data["totalSteps"] > 0:
            progress_percent = (self.progress_data["completedSteps"] / self.progress_data["totalSteps"]) * 100
            self.progress_data["progressPercent"] = round(progress_percent, 2)
            
            # Calculate processing rate and estimated time remaining
            if self.progress_data["completedSteps"] > 0:
                start_time = datetime.fromisoformat(self.progress_data["startTime"].replace('Z', '+00:00'))
                elapsed_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if elapsed_seconds > 0:
                    steps_per_second = self.progress_data["completedSteps"] / elapsed_seconds
                    self.progress_data["processingRate"] = round(steps_per_second, 4)
                    
                    remaining_steps = self.progress_data["totalSteps"] - self.progress_data["completedSteps"]
                    
                    if steps_per_second > 0:
                        estimated_seconds = remaining_steps / steps_per_second
                        self.progress_data["estimatedTimeRemaining"] = self._format_duration(estimated_seconds)
                    else:
                        self.progress_data["estimatedTimeRemaining"] = "Calculating..."
    
    def _calculate_final_statistics(self):
        """Calculate final statistics when detection is complete"""
        if self.progress_data["startTime"] and self.progress_data["endTime"]:
            start_time = datetime.fromisoformat(self.progress_data["startTime"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(self.progress_data["endTime"].replace('Z', '+00:00'))
            total_duration = (end_time - start_time).total_seconds()
            
            self.progress_data["finalStatistics"] = {
                "totalDurationSeconds": total_duration,
                "totalDurationFormatted": self._format_duration(total_duration),
                "averageProcessingRate": round(self.progress_data["completedSteps"] / total_duration, 4) if total_duration > 0 else 0,
                "totalDetections": sum(
                    s.get("totalDetections", 0) 
                    for s in self.progress_data["symbolProgress"].values()
                ),
                "symbolsProcessed": len([
                    s for s in self.progress_data["symbolProgress"].values() 
                    if s["status"] == "completed"
                ]),
                "pagesProcessed": len([
                    p for p in self.progress_data["pageProgress"].values() 
                    if p["status"] == "completed"
                ]),
                "errorCount": len(self.progress_data["errors"]),
                "warningCount": len(self.progress_data["warnings"])
            }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _update_timestamps(self):
        """Update the last updated timestamp"""
        self.progress_data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    
    def _save_progress(self):
        """Save progress data to file (thread-safe)"""
        try:
            # Write to temporary file first, then rename for atomicity
            temp_file = self.progress_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.progress_data, f, indent=2)
            
            # Atomic rename
            os.rename(temp_file, self.progress_file)
            
        except Exception as e:
            print(f"⚠️ Failed to save progress: {e}")


class ProgressMonitor:
    """
    Utility class for monitoring progress from external processes.
    
    This class provides methods to read and monitor progress files
    without interfering with the main progress tracking.
    """
    
    @staticmethod
    def load_progress(progress_file: str) -> Optional[Dict[str, Any]]:
        """
        Load progress data from file.
        
        Args:
            progress_file: Path to progress file
            
        Returns:
            Progress data dict or None if file doesn't exist
        """
        if not os.path.exists(progress_file):
            return None
        
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Failed to load progress file: {e}")
            return None
    
    @staticmethod
    def wait_for_completion(
        progress_file: str, 
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        poll_interval: float = 1.0,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for detection to complete, optionally calling callback with updates.
        
        Args:
            progress_file: Path to progress file
            callback: Optional callback function called with progress updates
            poll_interval: How often to check for updates (seconds)
            timeout: Maximum time to wait (seconds), None for no timeout
            
        Returns:
            Final progress data or None if timeout/error
        """
        start_time = time.time()
        
        while True:
            progress = ProgressMonitor.load_progress(progress_file)
            
            if progress:
                if callback:
                    callback(progress)
                
                status = progress.get("status")
                if status in ["completed", "failed"]:
                    return progress
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                print(f"⏰ Progress monitoring timed out after {timeout} seconds")
                return None
            
            time.sleep(poll_interval)
    
    @staticmethod
    def get_progress_summary(progress_file: str) -> Optional[Dict[str, Any]]:
        """
        Get a lightweight progress summary.
        
        Args:
            progress_file: Path to progress file
            
        Returns:
            Progress summary or None if file doesn't exist
        """
        progress = ProgressMonitor.load_progress(progress_file)
        if not progress:
            return None
        
        return {
            "runId": progress.get("runId"),
            "status": progress.get("status"),
            "progressPercent": progress.get("progressPercent", 0),
            "currentStep": progress.get("currentStep"),
            "estimatedTimeRemaining": progress.get("estimatedTimeRemaining"),
            "errorCount": len(progress.get("errors", [])),
            "warningCount": len(progress.get("warnings", [])),
            "lastUpdated": progress.get("lastUpdated")
        }