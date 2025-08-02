"""
TimberGem Symbol Detection Module

This module provides symbol detection capabilities by integrating the gem_v5 
detection algorithm with TimberGem's coordinate mapping system.

Key Components:
- SymbolDetectionAlgorithm: Core detection algorithm adapted from gem_v5.py
- DetectionCandidate: Data structure for detection results
- SymbolDetectionEngine: Public interface for detection operations
"""

from .detection_algorithm import SymbolDetectionAlgorithm, DetectionCandidate
from .detection_engine import SymbolDetectionEngine
from .detection_storage import DetectionStorage
from .detection_progress import DetectionProgress, ProgressMonitor
from .detection_coordinator import DetectionCoordinator

__all__ = [
    'SymbolDetectionAlgorithm',
    'DetectionCandidate', 
    'SymbolDetectionEngine',
    'DetectionStorage',
    'DetectionProgress',
    'ProgressMonitor',
    'DetectionCoordinator'
]

# Version info
__version__ = '1.0.0'
__author__ = 'TimberGem Team'
__description__ = 'Symbol detection system for construction document analysis'