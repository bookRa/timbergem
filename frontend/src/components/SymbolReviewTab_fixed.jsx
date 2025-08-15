import React, { useState, useEffect } from 'react';
import axios from 'axios';
import InteractiveDetectionCanvas from './InteractiveDetectionCanvas';
import PageNavigationControls from './PageNavigationControls';
import SymbolFilterControls from './SymbolFilterControls';
import DetectionDetailsPanel from './DetectionDetailsPanel';

const SymbolReviewTab = ({ 
    docInfo, 
    projectData,
    onProjectDataChange 
}) => {
    // Core state management
    const [detectionResults, setDetectionResults] = useState(null);
    const [detectionRuns, setDetectionRuns] = useState([]);
    const [detectionProgress, setDetectionProgress] = useState(null);
    const [selectedSymbol, setSelectedSymbol] = useState(null);
    const [selectedPage, setSelectedPage] = useState(1);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Canvas-specific state
    const [selectedDetection, setSelectedDetection] = useState(null);
    const [pageImageUrl, setPageImageUrl] = useState(null);
    const [viewMode, setViewMode] = useState('canvas'); // 'canvas' | 'list'
    const [statusFilter, setStatusFilter] = useState('all');
    const [confidenceThreshold, setConfidenceThreshold] = useState(0);
    
    // Filter settings
    const [filterSettings, setFilterSettings] = useState({
        status: 'all', // 'all' | 'pending' | 'accepted' | 'rejected'
        confidence: 0.0,
        sortBy: 'confidence' // 'confidence' | 'count' | 'name'
    });

    // Load detection runs when document changes
    useEffect(() => {
        if (docInfo?.docId) {
            loadDetectionRuns();
        }
    }, [docInfo?.docId]);

    // Load latest results when runs change
    useEffect(() => {
        if (detectionRuns.length > 0) {
            const latestRun = detectionRuns[0];
            if (latestRun.status === 'completed') {
                loadDetectionResults(latestRun.runId);
            }
        }
    }, [detectionRuns]);

    // Load page image when page changes
    useEffect(() => {
        if (docInfo?.docId && selectedPage) {
            loadPageImage(selectedPage);
        }
    }, [docInfo?.docId, selectedPage]);

    const loadDetectionRuns = async () => {
        try {
            setIsLoading(true);
            const response = await axios.get(`/api/detection_runs/${docInfo.docId}`);
            setDetectionRuns(response.data.runs || []);
        } catch (err) {
            console.error('Failed to load detection runs:', err);
            setError('Failed to load detection runs');
        } finally {
            setIsLoading(false);
        }
    };

    const loadDetectionResults = async (runId) => {
        try {
            setIsLoading(true);
            const response = await axios.get(`/api/detection_results/${docInfo.docId}/${runId}`);
            setDetectionResults(response.data);
        } catch (err) {
            console.error('Failed to load detection results:', err);
            setError('Failed to load detection results');
        } finally {
            setIsLoading(false);
        }
    };

    const startDetection = async () => {
        const detectionParams = {
            matchThreshold: 0.28,
            iouThreshold: 0.2,
            scaleVariancePx: 2
        };

        try {
            setIsLoading(true);
            setError(null);
            
            const response = await axios.post('/api/run_symbol_detection', {
                docId: docInfo.docId,
                symbols: 'all',
                detectionParams
            });
            
            console.log('Detection started:', response.data);
            monitorProgress();
        } catch (err) {
            console.error('Failed to start detection:', err);
            setError('Failed to start symbol detection');
        } finally {
            setIsLoading(false);
        }
    };

    const monitorProgress = () => {
        const checkProgress = async () => {
            try {
                const progressResponse = await axios.get(`/api/detection_progress/${docInfo.docId}`);
                const progress = progressResponse.data;
                
                setDetectionProgress(progress);
                
                if (progress.status === 'completed') {
                    loadDetectionRuns();
                } else if (progress.status === 'running') {
                    setTimeout(checkProgress, 2000);
                }
            } catch (err) {
                console.error('Failed to check progress:', err);
            }
        };
        
        checkProgress();
    };

    // Load page image for canvas
    const loadPageImage = async (pageNumber) => {
        try {
            const response = await axios.get(`/api/get_page_image/${docInfo.docId}/${pageNumber}`);
            setPageImageUrl(response.data.imagePath);
        } catch (err) {
            console.error('Failed to load page image:', err);
            setPageImageUrl(null);
        }
    };

    // Handle detection coordinate updates from canvas
    const handleDetectionUpdate = async (detectionId, newPdfCoords) => {
        if (!detectionResults?.runId) return;

        try {
            await axios.post('/api/update_detection_coordinates', {
                docId: docInfo.docId,
                runId: detectionResults.runId,
                detectionId,
                pdfCoords: newPdfCoords
            });

            // Refresh detection results
            loadDetectionResults(detectionResults.runId);
        } catch (err) {
            console.error('Failed to update detection coordinates:', err);
            setError('Failed to update detection coordinates');
        }
    };

    // Handle detection status updates
    const handleDetectionStatusUpdate = async (detectionId, newStatus) => {
        if (!detectionResults?.runId) return;

        try {
            await axios.post('/api/update_detection_status', {
                docId: docInfo.docId,
                runId: detectionResults.runId,
                detectionId,
                status: newStatus
            });

            // Refresh detection results
            loadDetectionResults(detectionResults.runId);
        } catch (err) {
            console.error('Failed to update detection status:', err);
            setError('Failed to update detection status');
        }
    };

    // Handle adding new detection
    const handleDetectionAdd = async (pdfCoords) => {
        if (!detectionResults?.runId || !selectedSymbol) return;

        try {
            await axios.post('/api/add_user_detection', {
                docId: docInfo.docId,
                runId: detectionResults.runId,
                symbolId: selectedSymbol,
                pdfCoords,
                pageNumber: selectedPage
            });

            // Refresh detection results
            loadDetectionResults(detectionResults.runId);
        } catch (err) {
            console.error('Failed to add detection:', err);
            setError('Failed to add detection');
        }
    };

    // Handle detection deletion
    const handleDetectionDelete = async (detectionId) => {
        if (!detectionResults?.runId) return;

        try {
            await axios.post('/api/delete_detection', {
                docId: docInfo.docId,
                runId: detectionResults.runId,
                detectionId
            });

            // Refresh detection results
            loadDetectionResults(detectionResults.runId);
            setSelectedDetection(null);
        } catch (err) {
            console.error('Failed to delete detection:', err);
            setError('Failed to delete detection');
        }
    };

    // Get current page detections with filtering
    const getCurrentPageDetections = () => {
        if (!detectionResults?.symbolResults) return [];

        let allDetections = [];
        
        Object.entries(detectionResults.symbolResults).forEach(([symbolId, symbolData]) => {
            // Filter by selected symbol if specified
            if (selectedSymbol && symbolId !== selectedSymbol) return;
            
            const pageDetections = symbolData.detectionsByPage?.[selectedPage] || [];
            
            pageDetections.forEach(detection => {
                // Apply status filter
                if (statusFilter !== 'all' && detection.status !== statusFilter) return;
                
                // Apply confidence threshold
                if (detection.iouScore < confidenceThreshold) return;
                
                allDetections.push({
                    ...detection,
                    symbolId,
                    symbolInfo: symbolData.symbolInfo
                });
            });
        });
        
        return allDetections;
    };

    // Get available symbols from detection results
    const getAvailableSymbols = () => {
        if (!detectionResults?.symbolResults) return [];
        
        return Object.entries(detectionResults.symbolResults).map(([symbolId, symbolData]) => ({
            symbolId,
            symbolInfo: symbolData.symbolInfo
        }));
    };

    // Get pages with detections
    const getPagesWithDetections = () => {
        if (!detectionResults?.symbolResults) return [];
        
        const pagesSet = new Set();
        Object.values(detectionResults.symbolResults).forEach(symbolData => {
            Object.keys(symbolData.detectionsByPage || {}).forEach(pageNum => {
                pagesSet.add(parseInt(pageNum));
            });
        });
        
        return Array.from(pagesSet).sort((a, b) => a - b);
    };

    // Get template dimensions for selected symbol
    const getTemplateInfoForSymbol = (symbolId) => {
        if (!detectionResults?.symbolResults?.[symbolId]) return null;
        
        const symbolData = detectionResults.symbolResults[symbolId];
        return {
            dimensions: symbolData.symbolInfo?.symbol_template_dimensions,
            templateInfo: symbolData.symbolInfo?.template_info
        };
    };

    // Helper variables
    const hasDetectionRuns = detectionRuns.length > 0;

    // Calculate overview statistics
    const overviewStats = React.useMemo(() => {
        if (!detectionResults?.symbolResults) {
            return {
                totalSymbols: 0,
                totalDetections: 0,
                pendingCount: 0,
                acceptedCount: 0,
                rejectedCount: 0,
                pagesWithDetections: 0,
                completionPercent: 0
            };
        }

        let totalDetections = 0;
        let pendingCount = 0;
        let acceptedCount = 0;
        let rejectedCount = 0;
        const pagesWithDetections = new Set();

        Object.values(detectionResults.symbolResults).forEach(symbol => {
            Object.values(symbol.detectionsByPage || {}).forEach(pageDetections => {
                pageDetections.forEach(detection => {
                    totalDetections++;
                    pagesWithDetections.add(detection.pageNumber);
                    
                    switch (detection.status) {
                        case 'pending':
                            pendingCount++;
                            break;
                        case 'accepted':
                            acceptedCount++;
                            break;
                        case 'rejected':
                            rejectedCount++;
                            break;
                    }
                });
            });
        });

        const reviewedCount = acceptedCount + rejectedCount;
        const completionPercent = totalDetections > 0 ? (reviewedCount / totalDetections) * 100 : 0;

        return {
            totalSymbols: Object.keys(detectionResults.symbolResults).length,
            totalDetections,
            pendingCount,
            acceptedCount,
            rejectedCount,
            pagesWithDetections: pagesWithDetections.size,
            completionPercent
        };
    }, [detectionResults]);

    // Render main content based on state
    const renderMainContent = () => {
        if (isLoading && !detectionResults) {
            return (
                <div className="loading-state">
                    <div className="loading-spinner" />
                    <p>Loading detection data...</p>
                </div>
            );
        }

        if (detectionResults) {
            return (
                <div className="review-content-loaded">
                    {/* View Mode Toggle */}
                    <div className="view-mode-controls">
                        <button 
                            className={`btn ${viewMode === 'canvas' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setViewMode('canvas')}
                        >
                            🎨 Canvas View
                        </button>
                        <button 
                            className={`btn ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setViewMode('list')}
                        >
                            📋 List View
                        </button>
                    </div>

                    {viewMode === 'canvas' ? (
                        <div className="symbol-review-canvas-layout">
                            <div className="canvas-main-area">
                                {/* Filters and Navigation */}
                                <SymbolFilterControls
                                    symbols={getAvailableSymbols()}
                                    selectedSymbol={selectedSymbol}
                                    statusFilter={statusFilter}
                                    confidenceThreshold={confidenceThreshold}
                                    onSymbolChange={setSelectedSymbol}
                                    onStatusChange={setStatusFilter}
                                    onConfidenceChange={setConfidenceThreshold}
                                />

                                <PageNavigationControls
                                    currentPage={selectedPage}
                                    totalPages={docInfo?.totalPages || 1}
                                    onPageChange={setSelectedPage}
                                    pagesWithDetections={getPagesWithDetections()}
                                />

                                {/* Interactive Canvas */}
                                <InteractiveDetectionCanvas
                                    pageImageUrl={pageImageUrl}
                                    detections={getCurrentPageDetections()}
                                    templateImage={null} // TODO: Load template image
                                    templateDimensions={selectedSymbol ? getTemplateInfoForSymbol(selectedSymbol)?.dimensions : null}
                                    pageMetadata={null} // TODO: Load page metadata
                                    onDetectionUpdate={handleDetectionUpdate}
                                    onDetectionAdd={handleDetectionAdd}
                                    onDetectionDelete={handleDetectionDelete}
                                    onDetectionSelect={setSelectedDetection}
                                />
                            </div>

                            {/* Detection Details Panel */}
                            <DetectionDetailsPanel
                                selectedDetection={selectedDetection}
                                onStatusUpdate={handleDetectionStatusUpdate}
                                onDetectionDelete={handleDetectionDelete}
                            />
                        </div>
                    ) : (
                        <div className="review-content-list">
                            <div className="detection-results-summary">
                                <h3>✅ Detection Complete</h3>
                                <div className="results-stats">
                                    <div className="stat-card">
                                        <span className="stat-number">{overviewStats.totalDetections || 0}</span>
                                        <span className="stat-label">Total Detections</span>
                                    </div>
                                    <div className="stat-card">
                                        <span className="stat-number">{Object.keys(detectionResults.symbolResults || {}).length}</span>
                                        <span className="stat-label">Symbol Types</span>
                                    </div>
                                    <div className="stat-card">
                                        <span className="stat-number">{overviewStats.pagesWithDetections || 0}</span>
                                        <span className="stat-label">Pages with Detections</span>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Detection Details */}
                            {detectionResults.symbolResults && Object.entries(detectionResults.symbolResults).map(([symbolId, symbolData]) => (
                                <div key={symbolId} className="symbol-results-section">
                                    <div className="symbol-header">
                                        <h4>🔍 {symbolData.symbolInfo?.name || 'Unknown Symbol'}</h4>
                                        <div className="symbol-stats">
                                            <span className="detection-count">
                                                {symbolData.summary?.totalDetections || 0} detections found
                                            </span>
                                            {symbolData.summary?.avgIou && (
                                                <span className="avg-confidence">
                                                    Avg IoU: {(symbolData.summary.avgIou * 100).toFixed(1)}%
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    
                                    {/* Detection List */}
                                    {symbolData.detectionsByPage && Object.entries(symbolData.detectionsByPage).map(([pageNum, detections]) => (
                                        <div key={pageNum} className="page-detections">
                                            <h5>📄 Page {pageNum}</h5>
                                            <div className="detections-grid">
                                                {detections.map((detection, detIndex) => (
                                                    <div key={detection.detectionId || detIndex} className="detection-card">
                                                        <div className="detection-header">
                                                            <span className="detection-id">#{detIndex + 1}</span>
                                                            <span className={`status-badge status-${detection.status}`}>
                                                                {detection.status}
                                                            </span>
                                                        </div>
                                                        <div className="detection-metrics">
                                                            <div className="metric">
                                                                <span className="metric-label">IoU Score:</span>
                                                                <span className="metric-value">{(detection.iouScore * 100).toFixed(1)}%</span>
                                                            </div>
                                                            <div className="metric">
                                                                <span className="metric-label">Confidence:</span>
                                                                <span className="metric-value">{(detection.matchConfidence * 100).toFixed(1)}%</span>
                                                            </div>
                                                        </div>
                                                        <div className="detection-location">
                                                            <div className="coordinate-info">
                                                                <strong>PDF:</strong> ({detection.pdfCoords?.left_points?.toFixed(1)}, {detection.pdfCoords?.top_points?.toFixed(1)})
                                                                <br />
                                                                <strong>Size:</strong> {detection.pdfCoords?.width_points?.toFixed(1)} × {detection.pdfCoords?.height_points?.toFixed(1)} pts
                                                            </div>
                                                        </div>
                                                        <div className="detection-actions">
                                                            <button 
                                                                className="btn-accept"
                                                                onClick={() => handleDetectionStatusUpdate(detection.detectionId, 'accepted')}
                                                            >
                                                                ✓ Accept
                                                            </button>
                                                            <button 
                                                                className="btn-reject"
                                                                onClick={() => handleDetectionStatusUpdate(detection.detectionId, 'rejected')}
                                                            >
                                                                ✗ Reject
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                    
                                    {(!symbolData.detectionsByPage || Object.keys(symbolData.detectionsByPage).length === 0) && (
                                        <div className="no-detections">
                                            <p>No detections found for this symbol.</p>
                                        </div>
                                    )}
                                </div>
                            ))}
                            
                            <div className="debug-info">
                                <details>
                                    <summary>🐛 Debug Information</summary>
                                    <pre>{JSON.stringify({
                                        runId: detectionResults.runId,
                                        status: detectionResults.status,
                                        symbolCount: Object.keys(detectionResults.symbolResults || {}).length,
                                        totalDetections: overviewStats.totalDetections,
                                        fullResults: detectionResults
                                    }, null, 2)}</pre>
                                </details>
                            </div>
                        </div>
                    )}
                </div>
            );
        }

        if (hasDetectionRuns) {
            return (
                <div className="no-results-state">
                    <h3>No Completed Detection Runs</h3>
                    <p>Start a detection run to review symbol detections.</p>
                    <div className="runs-info">
                        <h4>Available Runs:</h4>
                        <ul>
                            {detectionRuns.map(run => (
                                <li key={run.runId}>
                                    Run {run.runId.slice(-6)} - {run.status} 
                                    ({new Date(run.createdAt).toLocaleDateString()})
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            );
        }

        return (
            <div className="empty-state">
                <h3>No Detection Runs Found</h3>
                <p>Start your first symbol detection to begin reviewing results.</p>
                <button 
                    className="btn-primary btn-lg"
                    onClick={startDetection}
                    disabled={isLoading}
                >
                    🔍 Start Symbol Detection
                </button>
            </div>
        );
    };

    if (!docInfo) {
        return (
            <div className="symbol-review-tab">
                <div className="empty-state">
                    <h3>No Document Selected</h3>
                    <p>Please upload and process a document first.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="symbol-review-tab">
            <div className="symbol-review-header">
                <div className="header-top">
                    <div className="header-title">
                        <h2>Symbol Review</h2>
                        <p className="header-subtitle">
                            Review and validate detected symbols across all pages
                        </p>
                    </div>
                    <div className="header-actions">
                        <button 
                            className="btn-secondary btn-sm"
                            onClick={loadDetectionRuns}
                            disabled={isLoading}
                        >
                            🔄 Refresh
                        </button>
                        <button 
                            className="btn-primary"
                            onClick={startDetection}
                            disabled={isLoading || detectionProgress?.status === 'running'}
                        >
                            {detectionProgress?.status === 'running' ? '⏳ Running...' : '🔍 Start Detection'}
                        </button>
                    </div>
                </div>

                {/* Overview Statistics */}
                <div className="detection-overview-stats">
                    <div className="overview-stat">
                        <span className="stat-number">{overviewStats.totalSymbols}</span>
                        <span className="stat-label">Symbol Types</span>
                    </div>
                    <div className="overview-stat">
                        <span className="stat-number">{overviewStats.totalDetections}</span>
                        <span className="stat-label">Total Detections</span>
                    </div>
                    <div className="overview-stat pending">
                        <span className="stat-number">{overviewStats.pendingCount}</span>
                        <span className="stat-label">Pending Review</span>
                    </div>
                    <div className="overview-stat accepted">
                        <span className="stat-number">{overviewStats.acceptedCount}</span>
                        <span className="stat-label">Accepted</span>
                    </div>
                    <div className="overview-stat rejected">
                        <span className="stat-number">{overviewStats.rejectedCount}</span>
                        <span className="stat-label">Rejected</span>
                    </div>
                    <div className="overview-stat">
                        <span className="stat-number">{Math.round(overviewStats.completionPercent)}%</span>
                        <span className="stat-label">Reviewed</span>
                    </div>
                </div>

                {/* Progress Display */}
                {detectionProgress && detectionProgress.status === 'running' && (
                    <div className="detection-progress-banner">
                        <div className="progress-info">
                            <span className="progress-status">🔄 {detectionProgress.currentStep}</span>
                            <span className="progress-percent">{Math.round(detectionProgress.progressPercent)}%</span>
                        </div>
                        <div className="progress-bar">
                            <div 
                                className="progress-fill"
                                style={{ width: `${detectionProgress.progressPercent}%` }}
                            />
                        </div>
                        {detectionProgress.estimatedTimeRemaining && (
                            <div className="progress-eta">
                                ⏱️ {detectionProgress.estimatedTimeRemaining} remaining
                            </div>
                        )}
                    </div>
                )}

                {/* Error Display */}
                {error && (
                    <div className="error-banner">
                        <span className="error-icon">❌</span>
                        <span className="error-message">{error}</span>
                        <button 
                            className="error-dismiss"
                            onClick={() => setError(null)}
                        >
                            ×
                        </button>
                    </div>
                )}
            </div>

            {/* Main Content Area */}
            <div className="symbol-review-content">
                {renderMainContent()}
            </div>
        </div>
    );
};

export default SymbolReviewTab;