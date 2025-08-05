# Phase 2: Basic Review Interface - Comprehensive Implementation Plan

## Overview

Phase 2 builds upon the robust symbol detection backend (Phase 1) to create an intuitive, efficient UI for reviewing detected symbols across all pages of a document. The interface must handle potentially hundreds of detections across multiple symbols and pages while maintaining excellent UX.

## Design Philosophy

### Core UX Principles
1. **Cognitive Load Management**: Only show what users need to see at each step
2. **Progressive Disclosure**: Start with overview, drill down to details
3. **Spatial Context**: Always provide visual reference to symbol location
4. **Batch Operations**: Enable efficient review of similar symbols
5. **Visual Feedback**: Clear status indicators for all detection states

### User Mental Model
```
Document → Symbols → Pages → Individual Detections
    ↓        ↓        ↓             ↓
 Overview → Review → Verify →    Accept/Reject
```

## Architectural Decisions

### State Management Strategy
- **Local State**: UI interactions, selections, filters
- **API State**: Detection results, status updates, progress
- **Derived State**: Computed summaries, filtered views
- **Persistent State**: User preferences, view settings

### Component Hierarchy
```
SymbolReviewTab
├── SymbolReviewHeader (stats, controls)
├── SymbolReviewContent
│   ├── SymbolSidebar
│   │   ├── SymbolOverview
│   │   ├── SymbolList
│   │   └── SymbolFilters
│   ├── DetectionMainView
│   │   ├── DetectionGrid
│   │   ├── PageNavigation
│   │   └── DetectionControls
│   └── TemplateReferencePanel
│       ├── TemplatePreview
│       ├── SymbolMetadata
│       └── DetectionSettings
└── SymbolReviewModals
    ├── DetectionProgressModal
    ├── BulkActionsModal
    └── DetectionDetailsModal
```

## Implementation Milestones

### Milestone 1: Core Infrastructure & Tab Structure (Days 1-3)

#### 1.1 Component Architecture Setup
**Files to Create:**
- `frontend/src/components/SymbolReviewTab.jsx` (main container)
- `frontend/src/components/symbolReview/SymbolReviewHeader.jsx`
- `frontend/src/components/symbolReview/SymbolReviewContent.jsx`
- `frontend/src/components/symbolReview/SymbolSidebar.jsx`
- `frontend/src/components/symbolReview/DetectionMainView.jsx`
- `frontend/src/components/symbolReview/TemplateReferencePanel.jsx`

**Key Features:**
```jsx
// SymbolReviewTab.jsx structure
const SymbolReviewTab = ({ docInfo, onProjectDataChange }) => {
    // State management
    const [detectionResults, setDetectionResults] = useState(null);
    const [selectedSymbol, setSelectedSymbol] = useState(null);
    const [selectedPage, setSelectedPage] = useState(1);
    const [detectionProgress, setDetectionProgress] = useState(null);
    const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
    const [filterSettings, setFilterSettings] = useState({
        status: 'all', // 'all' | 'pending' | 'accepted' | 'rejected'
        confidence: 0.0,
        sortBy: 'confidence' // 'confidence' | 'page' | 'position'
    });

    // API integration hooks
    const { 
        data: detectionRuns, 
        isLoading: runsLoading 
    } = useDetectionRuns(docInfo?.docId);
    
    const { 
        data: latestResults, 
        isLoading: resultsLoading 
    } = useDetectionResults(docInfo?.docId, detectionRuns?.[0]?.runId);

    // Real-time progress monitoring
    const { 
        data: progressData, 
        isLoading: progressLoading 
    } = useDetectionProgress(docInfo?.docId, {
        enabled: detectionProgress?.status === 'running',
        refetchInterval: 2000
    });

    return (
        <div className="symbol-review-tab">
            <SymbolReviewHeader 
                detectionResults={detectionResults}
                detectionProgress={detectionProgress}
                onStartDetection={handleStartDetection}
                onRefreshResults={handleRefreshResults}
            />
            <SymbolReviewContent
                docInfo={docInfo}
                detectionResults={detectionResults}
                selectedSymbol={selectedSymbol}
                selectedPage={selectedPage}
                viewMode={viewMode}
                filterSettings={filterSettings}
                onSymbolSelect={setSelectedSymbol}
                onPageSelect={setSelectedPage}
                onViewModeChange={setViewMode}
                onFilterChange={setFilterSettings}
                onDetectionUpdate={handleDetectionUpdate}
            />
        </div>
    );
};
```

#### 1.2 API Integration Layer
**Files to Create:**
- `frontend/src/hooks/useDetectionAPI.js`
- `frontend/src/utils/detectionHelpers.js`

**API Hook Implementation:**
```javascript
// useDetectionAPI.js
export const useDetectionRuns = (docId) => {
    return useQuery({
        queryKey: ['detectionRuns', docId],
        queryFn: () => axios.get(`/api/detection_runs/${docId}`),
        enabled: !!docId,
        staleTime: 30000 // 30 seconds
    });
};

export const useDetectionResults = (docId, runId) => {
    return useQuery({
        queryKey: ['detectionResults', docId, runId],
        queryFn: () => axios.get(`/api/detection_results/${docId}?runId=${runId}`),
        enabled: !!(docId && runId),
        staleTime: 60000 // 1 minute
    });
};

export const useDetectionProgress = (docId, options = {}) => {
    return useQuery({
        queryKey: ['detectionProgress', docId],
        queryFn: () => axios.get(`/api/detection_progress/${docId}`),
        enabled: !!docId && options.enabled,
        refetchInterval: options.refetchInterval || 5000,
        staleTime: 0 // Always fresh for progress
    });
};

export const useUpdateDetectionStatus = () => {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: ({ docId, runId, updates }) => 
            axios.post('/api/update_detection_status', { docId, runId, updates }),
        onSuccess: (_, { docId, runId }) => {
            // Invalidate related queries
            queryClient.invalidateQueries(['detectionResults', docId, runId]);
        }
    });
};

export const useStartDetection = () => {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: ({ docId, symbolIds, detectionParams }) =>
            axios.post('/api/run_symbol_detection', { 
                docId, 
                symbolIds, 
                detectionParams 
            }),
        onSuccess: (_, { docId }) => {
            queryClient.invalidateQueries(['detectionRuns', docId]);
            queryClient.invalidateQueries(['detectionProgress', docId]);
        }
    });
};
```

#### 1.3 Layout Foundation
**CSS Structure:**
```css
/* Symbol Review Tab Styles */
.symbol-review-tab {
    padding: 30px;
    max-width: 1600px;
    margin: 0 auto;
    min-height: calc(100vh - 200px);
}

.symbol-review-header {
    margin-bottom: 30px;
    padding: 20px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e1e5e9;
}

.symbol-review-content {
    display: grid;
    grid-template-columns: 320px 1fr 360px;
    gap: 24px;
    min-height: 600px;
}

.symbol-sidebar {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e1e5e9;
    overflow: hidden;
}

.detection-main-view {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e1e5e9;
    display: flex;
    flex-direction: column;
}

.template-reference-panel {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e1e5e9;
    overflow: hidden;
}

/* Responsive design */
@media (max-width: 1400px) {
    .symbol-review-content {
        grid-template-columns: 280px 1fr 320px;
        gap: 20px;
    }
}

@media (max-width: 1200px) {
    .symbol-review-content {
        grid-template-columns: 1fr;
        gap: 20px;
    }
    
    .template-reference-panel {
        order: -1;
    }
}
```

### Milestone 2: Symbol List Sidebar (Days 4-6)

#### 2.1 Symbol Overview Dashboard
**Component: SymbolOverview.jsx**
```jsx
const SymbolOverview = ({ detectionResults, onStartDetection }) => {
    const summary = useMemo(() => {
        if (!detectionResults) return null;
        
        const stats = {
            totalSymbols: Object.keys(detectionResults.symbolResults || {}).length,
            totalDetections: 0,
            pendingCount: 0,
            acceptedCount: 0,
            rejectedCount: 0,
            avgConfidence: 0
        };
        
        Object.values(detectionResults.symbolResults || {}).forEach(symbol => {
            Object.values(symbol.detectionsByPage || {}).forEach(pageDetections => {
                pageDetections.forEach(detection => {
                    stats.totalDetections++;
                    switch(detection.status) {
                        case 'accepted': stats.acceptedCount++; break;
                        case 'rejected': stats.rejectedCount++; break;
                        default: stats.pendingCount++;
                    }
                });
            });
        });
        
        return stats;
    }, [detectionResults]);

    return (
        <div className="symbol-overview">
            <div className="overview-header">
                <h3>Detection Overview</h3>
                <div className="overview-actions">
                    <button 
                        className="btn-secondary btn-sm"
                        onClick={onStartDetection}
                        disabled={!detectionResults}
                    >
                        🔄 Re-run Detection
                    </button>
                </div>
            </div>
            
            {summary && (
                <div className="overview-stats">
                    <div className="stat-grid">
                        <div className="stat-item">
                            <span className="stat-number">{summary.totalSymbols}</span>
                            <span className="stat-label">Symbol Types</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-number">{summary.totalDetections}</span>
                            <span className="stat-label">Total Detections</span>
                        </div>
                        <div className="stat-item pending">
                            <span className="stat-number">{summary.pendingCount}</span>
                            <span className="stat-label">Pending Review</span>
                        </div>
                        <div className="stat-item accepted">
                            <span className="stat-number">{summary.acceptedCount}</span>
                            <span className="stat-label">Accepted</span>
                        </div>
                    </div>
                    
                    <div className="progress-bar">
                        <div className="progress-track">
                            <div 
                                className="progress-fill accepted"
                                style={{ 
                                    width: `${(summary.acceptedCount / summary.totalDetections) * 100}%` 
                                }}
                            />
                            <div 
                                className="progress-fill rejected"
                                style={{ 
                                    width: `${(summary.rejectedCount / summary.totalDetections) * 100}%`,
                                    left: `${(summary.acceptedCount / summary.totalDetections) * 100}%`
                                }}
                            />
                        </div>
                        <div className="progress-legend">
                            <span className="legend-item accepted">
                                Accepted ({Math.round((summary.acceptedCount / summary.totalDetections) * 100)}%)
                            </span>
                            <span className="legend-item rejected">
                                Rejected ({Math.round((summary.rejectedCount / summary.totalDetections) * 100)}%)
                            </span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
```

#### 2.2 Symbol List with Detection Counts
**Component: SymbolList.jsx**
```jsx
const SymbolList = ({ 
    detectionResults, 
    selectedSymbol, 
    onSymbolSelect, 
    filterSettings 
}) => {
    const symbolSummaries = useMemo(() => {
        if (!detectionResults?.symbolResults) return [];
        
        return Object.entries(detectionResults.symbolResults).map(([symbolId, symbolData]) => {
            const detections = Object.values(symbolData.detectionsByPage || {}).flat();
            
            return {
                id: symbolId,
                name: symbolData.symbolInfo?.name || 'Unknown Symbol',
                totalDetections: detections.length,
                pendingCount: detections.filter(d => !d.status || d.status === 'pending').length,
                acceptedCount: detections.filter(d => d.status === 'accepted').length,
                rejectedCount: detections.filter(d => d.status === 'rejected').length,
                avgConfidence: detections.length > 0 
                    ? detections.reduce((sum, d) => sum + d.matchConfidence, 0) / detections.length 
                    : 0,
                pagesWithDetections: Object.keys(symbolData.detectionsByPage || {}).length,
                symbolInfo: symbolData.symbolInfo
            };
        }).sort((a, b) => {
            switch(filterSettings.sortBy) {
                case 'confidence':
                    return b.avgConfidence - a.avgConfidence;
                case 'count':
                    return b.totalDetections - a.totalDetections;
                case 'name':
                    return a.name.localeCompare(b.name);
                default:
                    return 0;
            }
        });
    }, [detectionResults, filterSettings.sortBy]);

    return (
        <div className="symbol-list">
            <div className="symbol-list-header">
                <h4>Symbols ({symbolSummaries.length})</h4>
                <div className="sort-controls">
                    <select 
                        value={filterSettings.sortBy}
                        onChange={(e) => onFilterChange({
                            ...filterSettings,
                            sortBy: e.target.value
                        })}
                        className="sort-select"
                    >
                        <option value="confidence">By Confidence</option>
                        <option value="count">By Count</option>
                        <option value="name">By Name</option>
                    </select>
                </div>
            </div>
            
            <div className="symbol-items">
                {symbolSummaries.map(symbol => (
                    <div 
                        key={symbol.id}
                        className={`symbol-item ${selectedSymbol?.id === symbol.id ? 'selected' : ''}`}
                        onClick={() => onSymbolSelect(symbol)}
                    >
                        <div className="symbol-item-header">
                            <h5 className="symbol-name">{symbol.name}</h5>
                            <span className="symbol-total">{symbol.totalDetections}</span>
                        </div>
                        
                        <div className="symbol-stats">
                            <div className="stat-chips">
                                <span className="stat-chip pending">
                                    {symbol.pendingCount} pending
                                </span>
                                <span className="stat-chip accepted">
                                    {symbol.acceptedCount} ✓
                                </span>
                                {symbol.rejectedCount > 0 && (
                                    <span className="stat-chip rejected">
                                        {symbol.rejectedCount} ✗
                                    </span>
                                )}
                            </div>
                            
                            <div className="confidence-bar">
                                <div className="confidence-track">
                                    <div 
                                        className="confidence-fill"
                                        style={{ width: `${symbol.avgConfidence * 100}%` }}
                                    />
                                </div>
                                <span className="confidence-value">
                                    {Math.round(symbol.avgConfidence * 100)}%
                                </span>
                            </div>
                        </div>
                        
                        <div className="symbol-meta">
                            <span className="pages-count">
                                📄 {symbol.pagesWithDetections} pages
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
```

#### 2.3 Filter and Search Controls
**Component: SymbolFilters.jsx**
```jsx
const SymbolFilters = ({ filterSettings, onFilterChange, symbolCount }) => {
    return (
        <div className="symbol-filters">
            <div className="filter-group">
                <label>Status Filter</label>
                <div className="filter-buttons">
                    <button 
                        className={`filter-btn ${filterSettings.status === 'all' ? 'active' : ''}`}
                        onClick={() => onFilterChange({ ...filterSettings, status: 'all' })}
                    >
                        All ({symbolCount.total})
                    </button>
                    <button 
                        className={`filter-btn pending ${filterSettings.status === 'pending' ? 'active' : ''}`}
                        onClick={() => onFilterChange({ ...filterSettings, status: 'pending' })}
                    >
                        Pending ({symbolCount.pending})
                    </button>
                    <button 
                        className={`filter-btn accepted ${filterSettings.status === 'accepted' ? 'active' : ''}`}
                        onClick={() => onFilterChange({ ...filterSettings, status: 'accepted' })}
                    >
                        Accepted ({symbolCount.accepted})
                    </button>
                </div>
            </div>
            
            <div className="filter-group">
                <label>Confidence Threshold</label>
                <div className="confidence-slider">
                    <input 
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={filterSettings.confidence}
                        onChange={(e) => onFilterChange({
                            ...filterSettings,
                            confidence: parseFloat(e.target.value)
                        })}
                        className="slider"
                    />
                    <div className="slider-labels">
                        <span>0%</span>
                        <span className="current-value">
                            {Math.round(filterSettings.confidence * 100)}%+
                        </span>
                        <span>100%</span>
                    </div>
                </div>
            </div>
        </div>
    );
};
```

### Milestone 3: Detection Grid View (Days 7-10)

#### 3.1 Grid Layout with Status Indicators
**Component: DetectionGrid.jsx**
```jsx
const DetectionGrid = ({ 
    detections, 
    selectedDetections, 
    onDetectionSelect,
    onDetectionUpdate,
    viewMode,
    docInfo 
}) => {
    const [imageCache, setImageCache] = useState(new Map());
    
    // Preload page images for visible detections
    useEffect(() => {
        const visiblePages = [...new Set(detections.map(d => d.pageNumber))];
        visiblePages.forEach(pageNum => {
            if (!imageCache.has(pageNum)) {
                preloadPageImage(docInfo.docId, pageNum).then(imageUrl => {
                    setImageCache(prev => new Map(prev).set(pageNum, imageUrl));
                });
            }
        });
    }, [detections, docInfo.docId, imageCache]);

    const groupedDetections = useMemo(() => {
        return detections.reduce((groups, detection) => {
            const pageNum = detection.pageNumber;
            if (!groups[pageNum]) groups[pageNum] = [];
            groups[pageNum].push(detection);
            return groups;
        }, {});
    }, [detections]);

    return (
        <div className={`detection-grid ${viewMode}`}>
            {Object.entries(groupedDetections).map(([pageNum, pageDetections]) => (
                <div key={pageNum} className="page-group">
                    <div className="page-group-header">
                        <h4>Page {pageNum}</h4>
                        <span className="detection-count">
                            {pageDetections.length} detection{pageDetections.length !== 1 ? 's' : ''}
                        </span>
                        <div className="page-actions">
                            <button 
                                className="btn-sm btn-secondary"
                                onClick={() => handleBulkAction(pageDetections, 'accept')}
                            >
                                ✓ Accept All
                            </button>
                            <button 
                                className="btn-sm btn-secondary"
                                onClick={() => handleBulkAction(pageDetections, 'reject')}
                            >
                                ✗ Reject All
                            </button>
                        </div>
                    </div>
                    
                    <div className="detection-items">
                        {pageDetections.map(detection => (
                            <DetectionCard
                                key={detection.detectionId}
                                detection={detection}
                                pageImage={imageCache.get(parseInt(pageNum))}
                                isSelected={selectedDetections.includes(detection.detectionId)}
                                onSelect={() => onDetectionSelect(detection.detectionId)}
                                onUpdate={onDetectionUpdate}
                                docInfo={docInfo}
                            />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};
```

#### 3.2 Individual Detection Cards
**Component: DetectionCard.jsx**
```jsx
const DetectionCard = ({ 
    detection, 
    pageImage, 
    isSelected, 
    onSelect, 
    onUpdate,
    docInfo 
}) => {
    const [showDetails, setShowDetails] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false);
    
    const getStatusColor = (status) => {
        switch(status) {
            case 'accepted': return '#28a745';
            case 'rejected': return '#dc3545';
            case 'modified': return '#ffc107';
            default: return '#6c757d';
        }
    };

    const handleStatusUpdate = async (newStatus) => {
        setIsUpdating(true);
        try {
            await onUpdate({
                detectionId: detection.detectionId,
                action: newStatus,
                reviewedBy: 'current_user' // TODO: get from auth context
            });
        } finally {
            setIsUpdating(false);
        }
    };

    return (
        <div className={`detection-card ${isSelected ? 'selected' : ''} ${detection.status || 'pending'}`}>
            <div className="detection-header">
                <div className="detection-meta">
                    <span className="detection-id">#{detection.detectionId.slice(-6)}</span>
                    <span className="confidence-badge">
                        {Math.round(detection.matchConfidence * 100)}%
                    </span>
                </div>
                <div className="detection-actions">
                    <button 
                        className="action-btn details"
                        onClick={() => setShowDetails(!showDetails)}
                        title="Show details"
                    >
                        ℹ️
                    </button>
                    <input 
                        type="checkbox"
                        checked={isSelected}
                        onChange={onSelect}
                        className="selection-checkbox"
                    />
                </div>
            </div>
            
            <div className="detection-preview">
                <DetectionThumbnail 
                    pageImage={pageImage}
                    pdfCoords={detection.pdfCoords}
                    docInfo={docInfo}
                    detection={detection}
                />
                <div className="detection-overlay">
                    <div 
                        className="status-indicator"
                        style={{ backgroundColor: getStatusColor(detection.status) }}
                    >
                        {detection.status === 'accepted' && '✓'}
                        {detection.status === 'rejected' && '✗'}
                        {detection.status === 'modified' && '📝'}
                        {(!detection.status || detection.status === 'pending') && '⏳'}
                    </div>
                </div>
            </div>
            
            <div className="detection-info">
                <div className="coordinates">
                    <small>
                        PDF: ({Math.round(detection.pdfCoords.left)}, {Math.round(detection.pdfCoords.top)})
                        {detection.pdfCoords.width}×{detection.pdfCoords.height}
                    </small>
                </div>
                <div className="metrics">
                    <span className="iou-score">IoU: {detection.iouScore?.toFixed(3)}</span>
                </div>
            </div>
            
            <div className="detection-controls">
                <button 
                    className="btn-accept"
                    onClick={() => handleStatusUpdate('accept')}
                    disabled={isUpdating || detection.status === 'accepted'}
                    title="Accept detection"
                >
                    ✓ Accept
                </button>
                <button 
                    className="btn-reject"
                    onClick={() => handleStatusUpdate('reject')}
                    disabled={isUpdating || detection.status === 'rejected'}
                    title="Reject detection"
                >
                    ✗ Reject
                </button>
                <button 
                    className="btn-modify"
                    onClick={() => handleModifyDetection(detection)}
                    disabled={isUpdating}
                    title="Modify detection position"
                >
                    📝 Modify
                </button>
            </div>
            
            {showDetails && (
                <div className="detection-details">
                    <div className="detail-row">
                        <label>Confidence:</label>
                        <span>{(detection.matchConfidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="detail-row">
                        <label>IoU Score:</label>
                        <span>{detection.iouScore?.toFixed(3) || 'N/A'}</span>
                    </div>
                    <div className="detail-row">
                        <label>Template Size:</label>
                        <span>{detection.templateSize?.width}×{detection.templateSize?.height}</span>
                    </div>
                    <div className="detail-row">
                        <label>Created:</label>
                        <span>{new Date(detection.createdAt).toLocaleString()}</span>
                    </div>
                    {detection.reviewedAt && (
                        <div className="detail-row">
                            <label>Reviewed:</label>
                            <span>{new Date(detection.reviewedAt).toLocaleString()}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
```

#### 3.3 Detection Thumbnail with Positioning
**Component: DetectionThumbnail.jsx**
```jsx
const DetectionThumbnail = ({ 
    pageImage, 
    pdfCoords, 
    docInfo, 
    detection,
    size = 120 
}) => {
    const canvasRef = useRef(null);
    const [isLoading, setIsLoading] = useState(true);
    
    useEffect(() => {
        if (!pageImage || !pdfCoords) return;
        
        const canvas = canvasRef.current;
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = () => {
            // Clear canvas
            ctx.clearRect(0, 0, size, size);
            
            // Calculate the region to extract around the detection
            const padding = 20; // pixels of context around detection
            const scale = img.width / docInfo.pageWidth; // Image pixels per PDF point
            
            // Convert PDF coordinates to image coordinates
            const imgCoords = {
                left: pdfCoords.left * scale,
                top: pdfCoords.top * scale,
                width: pdfCoords.width * scale,
                height: pdfCoords.height * scale
            };
            
            // Calculate extraction region with padding
            const extractX = Math.max(0, imgCoords.left - padding);
            const extractY = Math.max(0, imgCoords.top - padding);
            const extractW = Math.min(
                img.width - extractX, 
                imgCoords.width + (2 * padding)
            );
            const extractH = Math.min(
                img.height - extractY, 
                imgCoords.height + (2 * padding)
            );
            
            // Draw the extracted region to fit canvas
            ctx.drawImage(
                img,
                extractX, extractY, extractW, extractH,
                0, 0, size, size
            );
            
            // Draw detection bounding box
            const boxScale = size / extractW;
            const boxX = (imgCoords.left - extractX) * boxScale;
            const boxY = (imgCoords.top - extractY) * boxScale;
            const boxW = imgCoords.width * boxScale;
            const boxH = imgCoords.height * boxScale;
            
            ctx.strokeStyle = getStatusColor(detection.status);
            ctx.lineWidth = 2;
            ctx.strokeRect(boxX, boxY, boxW, boxH);
            
            // Add confidence overlay
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(boxX, boxY - 15, boxW, 15);
            ctx.fillStyle = 'white';
            ctx.font = '10px monospace';
            ctx.fillText(
                `${Math.round(detection.matchConfidence * 100)}%`,
                boxX + 2, boxY - 3
            );
            
            setIsLoading(false);
        };
        
        img.src = pageImage;
    }, [pageImage, pdfCoords, docInfo, detection, size]);
    
    const getStatusColor = (status) => {
        switch(status) {
            case 'accepted': return '#28a745';
            case 'rejected': return '#dc3545';
            case 'modified': return '#ffc107';
            default: return '#007bff';
        }
    };

    return (
        <div className="detection-thumbnail">
            {isLoading && (
                <div className="thumbnail-loading">
                    <div className="loading-spinner" />
                </div>
            )}
            <canvas 
                ref={canvasRef}
                width={size}
                height={size}
                className="thumbnail-canvas"
                style={{ display: isLoading ? 'none' : 'block' }}
            />
        </div>
    );
};
```

### Milestone 4: Template Reference Panel (Days 11-13)

#### 4.1 Template Preview Component
**Component: TemplatePreview.jsx**
```jsx
const TemplatePreview = ({ selectedSymbol, detectionResults }) => {
    const [templateImage, setTemplateImage] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    
    useEffect(() => {
        if (!selectedSymbol || !detectionResults) return;
        
        const loadTemplateImage = async () => {
            setIsLoading(true);
            try {
                const symbolData = detectionResults.symbolResults[selectedSymbol.id];
                if (symbolData?.symbolInfo?.relative_path) {
                    const imageUrl = `/data/processed/${detectionResults.docId}/${symbolData.symbolInfo.relative_path}`;
                    setTemplateImage(imageUrl);
                }
            } catch (error) {
                console.error('Failed to load template image:', error);
            } finally {
                setIsLoading(false);
            }
        };
        
        loadTemplateImage();
    }, [selectedSymbol, detectionResults]);

    if (!selectedSymbol) {
        return (
            <div className="template-preview empty">
                <div className="empty-state">
                    <h4>Select a Symbol</h4>
                    <p>Choose a symbol from the list to view its template and detection information.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="template-preview">
            <div className="template-header">
                <h4>{selectedSymbol.name}</h4>
                <div className="template-stats">
                    <span className="stat-chip">
                        {selectedSymbol.totalDetections} detections
                    </span>
                    <span className="stat-chip confidence">
                        {Math.round(selectedSymbol.avgConfidence * 100)}% avg
                    </span>
                </div>
            </div>
            
            <div className="template-image-container">
                {isLoading ? (
                    <div className="template-loading">
                        <div className="loading-spinner" />
                        <span>Loading template...</span>
                    </div>
                ) : templateImage ? (
                    <img 
                        src={templateImage}
                        alt={`Template for ${selectedSymbol.name}`}
                        className="template-image"
                    />
                ) : (
                    <div className="template-error">
                        <span>Template image not available</span>
                    </div>
                )}
            </div>
            
            <div className="template-info">
                <div className="info-row">
                    <label>Symbol Type:</label>
                    <span>{selectedSymbol.symbolInfo?.description || 'No description'}</span>
                </div>
                <div className="info-row">
                    <label>Template Size:</label>
                    <span>
                        {selectedSymbol.symbolInfo?.symbol_template_dimensions?.width_pixels_300dpi || 'N/A'}×
                        {selectedSymbol.symbolInfo?.symbol_template_dimensions?.height_pixels_300dpi || 'N/A'} px
                    </span>
                </div>
                <div className="info-row">
                    <label>Source Page:</label>
                    <span>Page {selectedSymbol.symbolInfo?.page_number || 'Unknown'}</span>
                </div>
            </div>
        </div>
    );
};
```

#### 4.2 Symbol Metadata and Detection Settings
**Component: SymbolMetadata.jsx**
```jsx
const SymbolMetadata = ({ selectedSymbol, onUpdateSettings }) => {
    const [detectionSettings, setDetectionSettings] = useState({
        matchThreshold: 0.30,
        iouThreshold: 0.32,
        scaleVariancePx: 2,
        rotationRange: [-1, 1],
        rotationStep: 1
    });
    
    const [showAdvanced, setShowAdvanced] = useState(false);

    if (!selectedSymbol) return null;

    return (
        <div className="symbol-metadata">
            <div className="metadata-section">
                <h5>Detection Statistics</h5>
                <div className="stats-grid">
                    <div className="stat-item">
                        <span className="stat-label">Total Found</span>
                        <span className="stat-value">{selectedSymbol.totalDetections}</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Pages</span>
                        <span className="stat-value">{selectedSymbol.pagesWithDetections}</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Avg Confidence</span>
                        <span className="stat-value">{Math.round(selectedSymbol.avgConfidence * 100)}%</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-label">Pending</span>
                        <span className="stat-value pending">{selectedSymbol.pendingCount}</span>
                    </div>
                </div>
            </div>
            
            <div className="metadata-section">
                <div className="section-header">
                    <h5>Detection Settings</h5>
                    <button 
                        className="btn-link"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                    >
                        {showAdvanced ? '▼ Hide' : '▶ Show'} Advanced
                    </button>
                </div>
                
                <div className="settings-form">
                    <div className="form-group">
                        <label>Match Threshold</label>
                        <div className="threshold-control">
                            <input 
                                type="range"
                                min="0.1"
                                max="0.9"
                                step="0.05"
                                value={detectionSettings.matchThreshold}
                                onChange={(e) => setDetectionSettings(prev => ({
                                    ...prev,
                                    matchThreshold: parseFloat(e.target.value)
                                }))}
                                className="threshold-slider"
                            />
                            <span className="threshold-value">
                                {Math.round(detectionSettings.matchThreshold * 100)}%
                            </span>
                        </div>
                        <small className="form-help">
                            Lower values find more matches but may include false positives
                        </small>
                    </div>
                    
                    {showAdvanced && (
                        <>
                            <div className="form-group">
                                <label>IoU Threshold</label>
                                <div className="threshold-control">
                                    <input 
                                        type="range"
                                        min="0.1"
                                        max="0.7"
                                        step="0.05"
                                        value={detectionSettings.iouThreshold}
                                        onChange={(e) => setDetectionSettings(prev => ({
                                            ...prev,
                                            iouThreshold: parseFloat(e.target.value)
                                        }))}
                                        className="threshold-slider"
                                    />
                                    <span className="threshold-value">
                                        {Math.round(detectionSettings.iouThreshold * 100)}%
                                    </span>
                                </div>
                            </div>
                            
                            <div className="form-group">
                                <label>Scale Variance</label>
                                <input 
                                    type="number"
                                    min="0"
                                    max="10"
                                    value={detectionSettings.scaleVariancePx}
                                    onChange={(e) => setDetectionSettings(prev => ({
                                        ...prev,
                                        scaleVariancePx: parseInt(e.target.value)
                                    }))}
                                    className="form-input small"
                                />
                                <small className="form-help">pixels</small>
                            </div>
                        </>
                    )}
                    
                    <div className="form-actions">
                        <button 
                            className="btn-primary btn-sm"
                            onClick={() => onUpdateSettings(selectedSymbol.id, detectionSettings)}
                        >
                            Re-detect with New Settings
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
```

### Milestone 5: Basic Accept/Reject Functionality (Days 14-16)

#### 5.1 Batch Operations Component
**Component: BatchOperations.jsx**
```jsx
const BatchOperations = ({ 
    selectedDetections, 
    onBatchUpdate, 
    onClearSelection 
}) => {
    const [isProcessing, setIsProcessing] = useState(false);
    
    const handleBatchAction = async (action) => {
        if (selectedDetections.length === 0) return;
        
        setIsProcessing(true);
        try {
            const updates = selectedDetections.map(detectionId => ({
                detectionId,
                action,
                reviewedBy: 'current_user' // TODO: get from auth context
            }));
            
            await onBatchUpdate(updates);
            onClearSelection();
        } finally {
            setIsProcessing(false);
        }
    };

    if (selectedDetections.length === 0) {
        return (
            <div className="batch-operations empty">
                <span className="selection-hint">
                    Select detections to perform batch operations
                </span>
            </div>
        );
    }

    return (
        <div className="batch-operations active">
            <div className="selection-summary">
                <span className="selection-count">
                    {selectedDetections.length} detection{selectedDetections.length !== 1 ? 's' : ''} selected
                </span>
                <button 
                    className="btn-link clear-selection"
                    onClick={onClearSelection}
                    disabled={isProcessing}
                >
                    Clear selection
                </button>
            </div>
            
            <div className="batch-actions">
                <button 
                    className="btn-batch accept"
                    onClick={() => handleBatchAction('accept')}
                    disabled={isProcessing}
                >
                    ✓ Accept All ({selectedDetections.length})
                </button>
                <button 
                    className="btn-batch reject"
                    onClick={() => handleBatchAction('reject')}
                    disabled={isProcessing}
                >
                    ✗ Reject All ({selectedDetections.length})
                </button>
            </div>
            
            {isProcessing && (
                <div className="batch-processing">
                    <div className="loading-spinner small" />
                    <span>Updating {selectedDetections.length} detections...</span>
                </div>
            )}
        </div>
    );
};
```

#### 5.2 Detection Progress Modal
**Component: DetectionProgressModal.jsx**
```jsx
const DetectionProgressModal = ({ 
    isOpen, 
    onClose, 
    progressData, 
    docInfo 
}) => {
    const [autoClose, setAutoClose] = useState(true);
    
    // Auto-close when detection completes
    useEffect(() => {
        if (autoClose && progressData?.status === 'completed') {
            const timer = setTimeout(() => {
                onClose();
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [progressData?.status, autoClose, onClose]);

    if (!isOpen || !progressData) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content detection-progress-modal">
                <div className="modal-header">
                    <h3>Symbol Detection Progress</h3>
                    <button 
                        className="modal-close"
                        onClick={onClose}
                    >
                        ×
                    </button>
                </div>
                
                <div className="modal-body">
                    <div className="progress-overview">
                        <div className="progress-circle">
                            <svg viewBox="0 0 36 36" className="circular-chart">
                                <path 
                                    className="circle-bg"
                                    d="M18 2.0845
                                       a 15.9155 15.9155 0 0 1 0 31.831
                                       a 15.9155 15.9155 0 0 1 0 -31.831"
                                />
                                <path 
                                    className="circle"
                                    strokeDasharray={`${progressData.progressPercent}, 100`}
                                    d="M18 2.0845
                                       a 15.9155 15.9155 0 0 1 0 31.831
                                       a 15.9155 15.9155 0 0 1 0 -31.831"
                                />
                                <text 
                                    x="18" 
                                    y="20.35" 
                                    className="percentage"
                                >
                                    {Math.round(progressData.progressPercent)}%
                                </text>
                            </svg>
                        </div>
                        
                        <div className="progress-details">
                            <div className="status-badge">
                                {progressData.status === 'running' && '🔄 Running'}
                                {progressData.status === 'completed' && '✅ Completed'}
                                {progressData.status === 'failed' && '❌ Failed'}
                            </div>
                            
                            <div className="current-step">
                                {progressData.currentStep}
                            </div>
                            
                            <div className="progress-stats">
                                <span>{progressData.completedSteps} / {progressData.totalSteps} steps</span>
                                {progressData.estimatedTimeRemaining && (
                                    <span>~ {progressData.estimatedTimeRemaining} remaining</span>
                                )}
                            </div>
                        </div>
                    </div>
                    
                    {progressData.status === 'completed' && (
                        <div className="completion-summary">
                            <h4>Detection Complete!</h4>
                            <div className="summary-stats">
                                <div className="summary-stat">
                                    <span className="stat-number">{progressData.totalDetections || 0}</span>
                                    <span className="stat-label">Total Detections</span>
                                </div>
                                <div className="summary-stat">
                                    <span className="stat-number">{progressData.symbolsProcessed || 0}</span>
                                    <span className="stat-label">Symbols Processed</span>
                                </div>
                                <div className="summary-stat">
                                    <span className="stat-number">{progressData.pagesProcessed || 0}</span>
                                    <span className="stat-label">Pages Analyzed</span>
                                </div>
                            </div>
                        </div>
                    )}
                    
                    {(progressData.errorCount > 0 || progressData.warningCount > 0) && (
                        <div className="progress-issues">
                            {progressData.errorCount > 0 && (
                                <div className="issue-item error">
                                    ❌ {progressData.errorCount} error{progressData.errorCount !== 1 ? 's' : ''}
                                </div>
                            )}
                            {progressData.warningCount > 0 && (
                                <div className="issue-item warning">
                                    ⚠️ {progressData.warningCount} warning{progressData.warningCount !== 1 ? 's' : ''}
                                </div>
                            )}
                        </div>
                    )}
                </div>
                
                <div className="modal-footer">
                    <label className="auto-close-toggle">
                        <input 
                            type="checkbox"
                            checked={autoClose}
                            onChange={(e) => setAutoClose(e.target.checked)}
                        />
                        Auto-close when complete
                    </label>
                    <button 
                        className="btn-secondary"
                        onClick={onClose}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};
```

## Phase 2 Complete CSS Styles

```css
/* Symbol Review Tab Base Styles */
.symbol-review-tab {
    padding: 30px;
    max-width: 1600px;
    margin: 0 auto;
    min-height: calc(100vh - 200px);
}

/* Header Styles */
.symbol-review-header {
    margin-bottom: 30px;
    padding: 24px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #e1e5e9;
}

.header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.header-title h2 {
    color: #1a2a4c;
    font-size: 1.8rem;
    margin: 0;
}

.header-subtitle {
    color: #666;
    font-size: 1rem;
    margin: 5px 0 0 0;
}

.header-actions {
    display: flex;
    gap: 12px;
}

.detection-overview-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 16px;
}

.overview-stat {
    text-align: center;
    padding: 16px;
    background: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #e9ecef;
}

.overview-stat.pending { border-left: 4px solid #ffc107; }
.overview-stat.accepted { border-left: 4px solid #28a745; }
.overview-stat.rejected { border-left: 4px solid #dc3545; }

.stat-number {
    display: block;
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a2a4c;
    line-height: 1;
}

.stat-label {
    display: block;
    font-size: 0.85rem;
    color: #6c757d;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Content Layout */
.symbol-review-content {
    display: grid;
    grid-template-columns: 320px 1fr 360px;
    gap: 24px;
    min-height: 600px;
}

/* Symbol Sidebar */
.symbol-sidebar {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #e1e5e9;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.symbol-overview {
    padding: 20px;
    border-bottom: 1px solid #e9ecef;
}

.overview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.overview-header h3 {
    color: #1a2a4c;
    font-size: 1.1rem;
    margin: 0;
}

.overview-stats {
    margin-bottom: 16px;
}

.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
}

.stat-item {
    text-align: center;
    padding: 8px;
    background: #f8f9fa;
    border-radius: 6px;
}

.stat-item.pending { background: #fff3cd; border: 1px solid #ffeaa7; }
.stat-item.accepted { background: #d4edda; border: 1px solid #c3e6cb; }

.stat-item .stat-number {
    font-size: 1.2rem;
    font-weight: 600;
    color: #1a2a4c;
}

.stat-item .stat-label {
    font-size: 0.75rem;
    color: #6c757d;
    margin-top: 2px;
}

.progress-bar {
    margin-top: 12px;
}

.progress-track {
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    position: relative;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    position: absolute;
    top: 0;
    transition: all 0.3s ease;
}

.progress-fill.accepted { background: #28a745; }
.progress-fill.rejected { background: #dc3545; }

.progress-legend {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 0.75rem;
}

.legend-item.accepted { color: #28a745; }
.legend-item.rejected { color: #dc3545; }

/* Symbol List */
.symbol-list {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.symbol-list-header {
    padding: 16px 20px;
    border-bottom: 1px solid #e9ecef;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.symbol-list-header h4 {
    color: #1a2a4c;
    font-size: 1rem;
    margin: 0;
}

.sort-select {
    padding: 4px 8px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 0.85rem;
    background: white;
}

.symbol-items {
    flex: 1;
    overflow-y: auto;
    padding: 0;
}

.symbol-item {
    padding: 16px 20px;
    border-bottom: 1px solid #f1f3f4;
    cursor: pointer;
    transition: all 0.2s ease;
}

.symbol-item:hover {
    background: #f8f9fa;
}

.symbol-item.selected {
    background: #e7f3ff;
    border-left: 4px solid #007bff;
}

.symbol-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.symbol-name {
    color: #1a2a4c;
    font-size: 0.95rem;
    font-weight: 500;
    margin: 0;
}

.symbol-total {
    background: #007bff;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 500;
}

.symbol-stats {
    margin-bottom: 8px;
}

.stat-chips {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
}

.stat-chip {
    padding: 2px 6px;
    border-radius: 10px;
    font-size: 0.7rem;
    font-weight: 500;
}

.stat-chip.pending {
    background: #fff3cd;
    color: #856404;
}

.stat-chip.accepted {
    background: #d4edda;
    color: #155724;
}

.stat-chip.rejected {
    background: #f8d7da;
    color: #721c24;
}

.confidence-bar {
    display: flex;
    align-items: center;
    gap: 8px;
}

.confidence-track {
    flex: 1;
    height: 4px;
    background: #e9ecef;
    border-radius: 2px;
    overflow: hidden;
}

.confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
    transition: width 0.3s ease;
}

.confidence-value {
    font-size: 0.75rem;
    color: #6c757d;
    font-weight: 500;
    min-width: 35px;
}

.symbol-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.pages-count {
    font-size: 0.75rem;
    color: #6c757d;
}

/* Symbol Filters */
.symbol-filters {
    padding: 16px 20px;
    border-top: 1px solid #e9ecef;
    background: #f8f9fa;
}

.filter-group {
    margin-bottom: 16px;
}

.filter-group:last-child {
    margin-bottom: 0;
}

.filter-group label {
    display: block;
    font-size: 0.85rem;
    font-weight: 500;
    color: #495057;
    margin-bottom: 8px;
}

.filter-buttons {
    display: flex;
    gap: 4px;
}

.filter-btn {
    flex: 1;
    padding: 6px 8px;
    border: 1px solid #ced4da;
    background: white;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
}

.filter-btn:hover {
    background: #e9ecef;
}

.filter-btn.active {
    background: #007bff;
    color: white;
    border-color: #007bff;
}

.filter-btn.pending.active {
    background: #ffc107;
    border-color: #ffc107;
    color: #212529;
}

.filter-btn.accepted.active {
    background: #28a745;
    border-color: #28a745;
}

.confidence-slider {
    position: relative;
}

.slider {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #e9ecef;
    outline: none;
    -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #007bff;
    cursor: pointer;
}

.slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #007bff;
    cursor: pointer;
    border: none;
}

.slider-labels {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
    font-size: 0.7rem;
    color: #6c757d;
}

.current-value {
    font-weight: 600;
    color: #007bff;
}

/* Detection Main View */
.detection-main-view {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #e1e5e9;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.detection-view-header {
    padding: 20px 24px;
    border-bottom: 1px solid #e9ecef;
    background: #f8f9fa;
}

.view-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.view-title h4 {
    color: #1a2a4c;
    font-size: 1.1rem;
    margin: 0;
}

.view-mode-toggle {
    display: flex;
    border: 1px solid #ced4da;
    border-radius: 6px;
    overflow: hidden;
}

.view-mode-btn {
    padding: 6px 12px;
    border: none;
    background: white;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s ease;
}

.view-mode-btn.active {
    background: #007bff;
    color: white;
}

.batch-operations {
    padding: 12px;
    background: #fff3cd;
    border-radius: 6px;
    border: 1px solid #ffeaa7;
}

.batch-operations.empty {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    text-align: center;
}

.selection-hint {
    color: #6c757d;
    font-size: 0.85rem;
}

.batch-operations.active {
    background: #d1ecf1;
    border: 1px solid #bee5eb;
}

.selection-summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.selection-count {
    font-weight: 500;
    color: #0c5460;
}

.clear-selection {
    color: #007bff;
    text-decoration: none;
    font-size: 0.85rem;
    border: none;
    background: none;
    cursor: pointer;
}

.batch-actions {
    display: flex;
    gap: 8px;
}

.btn-batch {
    flex: 1;
    padding: 6px 12px;
    border: none;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-batch.accept {
    background: #28a745;
    color: white;
}

.btn-batch.accept:hover {
    background: #218838;
}

.btn-batch.reject {
    background: #dc3545;
    color: white;
}

.btn-batch.reject:hover {
    background: #c82333;
}

.batch-processing {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #bee5eb;
    font-size: 0.85rem;
    color: #0c5460;
}

/* Detection Grid */
.detection-grid {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
}

.page-group {
    margin-bottom: 32px;
}

.page-group:last-child {
    margin-bottom: 0;
}

.page-group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e9ecef;
}

.page-group-header h4 {
    color: #1a2a4c;
    font-size: 1.1rem;
    margin: 0;
}

.detection-count {
    color: #6c757d;
    font-size: 0.9rem;
}

.page-actions {
    display: flex;
    gap: 8px;
}

.detection-items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
}

.detection-items.list {
    grid-template-columns: 1fr;
}

/* Detection Cards */
.detection-card {
    border: 2px solid #e9ecef;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.2s ease;
    background: white;
}

.detection-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.detection-card.selected {
    border-color: #007bff;
    box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
}

.detection-card.accepted {
    border-left: 4px solid #28a745;
}

.detection-card.rejected {
    border-left: 4px solid #dc3545;
}

.detection-card.modified {
    border-left: 4px solid #ffc107;
}

.detection-header {
    padding: 12px;
    background: #f8f9fa;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e9ecef;
}

.detection-meta {
    display: flex;
    gap: 8px;
    align-items: center;
}

.detection-id {
    font-family: monospace;
    font-size: 0.8rem;
    color: #6c757d;
}

.confidence-badge {
    padding: 2px 6px;
    background: #007bff;
    color: white;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 500;
}

.detection-actions {
    display: flex;
    gap: 8px;
    align-items: center;
}

.action-btn {
    padding: 4px 8px;
    border: none;
    background: #e9ecef;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: background 0.2s ease;
}

.action-btn:hover {
    background: #dee2e6;
}

.selection-checkbox {
    width: 16px;
    height: 16px;
    cursor: pointer;
}

.detection-preview {
    position: relative;
    height: 140px;
    background: #f8f9fa;
    display: flex;
    align-items: center;
    justify-content: center;
}

.detection-overlay {
    position: absolute;
    top: 8px;
    right: 8px;
}

.status-indicator {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
    font-weight: bold;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.detection-info {
    padding: 8px 12px;
    font-size: 0.8rem;
    color: #6c757d;
    background: #f8f9fa;
    border-top: 1px solid #e9ecef;
}

.coordinates {
    margin-bottom: 4px;
}

.metrics {
    display: flex;
    justify-content: space-between;
}

.detection-controls {
    padding: 12px;
    display: flex;
    gap: 6px;
}

.detection-controls button {
    flex: 1;
    padding: 6px 8px;
    border: none;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-accept {
    background: #28a745;
    color: white;
}

.btn-accept:hover:not(:disabled) {
    background: #218838;
}

.btn-reject {
    background: #dc3545;
    color: white;
}

.btn-reject:hover:not(:disabled) {
    background: #c82333;
}

.btn-modify {
    background: #ffc107;
    color: #212529;
}

.btn-modify:hover:not(:disabled) {
    background: #e0a800;
}

.detection-controls button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.detection-details {
    padding: 12px;
    background: #f8f9fa;
    border-top: 1px solid #e9ecef;
    font-size: 0.8rem;
}

.detail-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
}

.detail-row:last-child {
    margin-bottom: 0;
}

.detail-row label {
    font-weight: 500;
    color: #495057;
}

.detail-row span {
    color: #6c757d;
}

/* Detection Thumbnail */
.detection-thumbnail {
    width: 120px;
    height: 120px;
    position: relative;
    border-radius: 4px;
    overflow: hidden;
}

.thumbnail-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    background: #f8f9fa;
}

.loading-spinner {
    width: 24px;
    height: 24px;
    border: 2px solid #e9ecef;
    border-top: 2px solid #007bff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.loading-spinner.small {
    width: 16px;
    height: 16px;
    border-width: 2px;
}

.thumbnail-canvas {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* Template Reference Panel */
.template-reference-panel {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #e1e5e9;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.template-preview {
    padding: 20px;
    border-bottom: 1px solid #e9ecef;
}

.template-preview.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
}

.empty-state {
    text-align: center;
    color: #6c757d;
}

.empty-state h4 {
    color: #495057;
    margin-bottom: 8px;
}

.template-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
}

.template-header h4 {
    color: #1a2a4c;
    font-size: 1.1rem;
    margin: 0;
}

.template-stats {
    display: flex;
    gap: 6px;
}

.template-image-container {
    margin-bottom: 16px;
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid #e9ecef;
}

.template-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: #6c757d;
    font-size: 0.9rem;
}

.template-image {
    max-width: 100%;
    max-height: 200px;
    object-fit: contain;
    border-radius: 4px;
}

.template-error {
    color: #6c757d;
    font-size: 0.9rem;
    text-align: center;
}

.template-info {
    font-size: 0.85rem;
}

.info-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    padding: 4px 0;
    border-bottom: 1px solid #f1f3f4;
}

.info-row:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.info-row label {
    font-weight: 500;
    color: #495057;
}

.info-row span {
    color: #6c757d;
}

/* Symbol Metadata */
.symbol-metadata {
    flex: 1;
    overflow-y: auto;
}

.metadata-section {
    padding: 20px;
    border-bottom: 1px solid #e9ecef;
}

.metadata-section:last-child {
    border-bottom: none;
}

.metadata-section h5 {
    color: #1a2a4c;
    font-size: 1rem;
    margin: 0 0 16px 0;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.section-header h5 {
    margin: 0;
}

.btn-link {
    color: #007bff;
    text-decoration: none;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.85rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
}

.settings-form {
    font-size: 0.85rem;
}

.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    font-weight: 500;
    color: #495057;
    margin-bottom: 6px;
}

.threshold-control {
    display: flex;
    align-items: center;
    gap: 8px;
}

.threshold-slider {
    flex: 1;
}

.threshold-value {
    min-width: 40px;
    font-weight: 500;
    color: #007bff;
    text-align: right;
}

.form-help {
    display: block;
    margin-top: 4px;
    color: #6c757d;
    font-size: 0.75rem;
    line-height: 1.3;
}

.form-input {
    width: 100%;
    padding: 6px 8px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 0.85rem;
}

.form-input.small {
    width: 80px;
}

.form-actions {
    margin-top: 16px;
}

/* Detection Progress Modal */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow: hidden;
}

.modal-header {
    padding: 20px 24px;
    border-bottom: 1px solid #e9ecef;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-header h3 {
    color: #1a2a4c;
    font-size: 1.3rem;
    margin: 0;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #6c757d;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background 0.2s ease;
}

.modal-close:hover {
    background: #f8f9fa;
}

.modal-body {
    padding: 24px;
}

.progress-overview {
    display: flex;
    gap: 24px;
    margin-bottom: 24px;
}

.progress-circle {
    flex-shrink: 0;
}

.circular-chart {
    width: 80px;
    height: 80px;
}

.circle-bg {
    fill: none;
    stroke: #e9ecef;
    stroke-width: 2.8;
}

.circle {
    fill: none;
    stroke: #007bff;
    stroke-width: 2.8;
    stroke-linecap: round;
    transition: stroke-dasharray 0.3s ease;
    transform: rotate(-90deg);
    transform-origin: 50% 50%;
}

.percentage {
    fill: #1a2a4c;
    font-size: 0.5em;
    text-anchor: middle;
    font-weight: bold;
}

.progress-details {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 8px;
}

.status-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 500;
    background: #e7f3ff;
    color: #0056b3;
    align-self: flex-start;
}

.current-step {
    font-size: 0.95rem;
    color: #495057;
    font-weight: 500;
}

.progress-stats {
    font-size: 0.85rem;
    color: #6c757d;
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.completion-summary {
    text-align: center;
    padding: 20px;
    background: #d4edda;
    border-radius: 8px;
    margin-bottom: 16px;
}

.completion-summary h4 {
    color: #155724;
    margin-bottom: 16px;
}

.summary-stats {
    display: flex;
    justify-content: space-around;
    gap: 16px;
}

.summary-stat {
    text-align: center;
}

.summary-stat .stat-number {
    display: block;
    font-size: 1.5rem;
    font-weight: bold;
    color: #155724;
}

.summary-stat .stat-label {
    display: block;
    font-size: 0.8rem;
    color: #155724;
    margin-top: 4px;
}

.progress-issues {
    padding: 12px;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid #e9ecef;
}

.issue-item {
    font-size: 0.85rem;
    margin-bottom: 4px;
}

.issue-item:last-child {
    margin-bottom: 0;
}

.issue-item.error {
    color: #721c24;
}

.issue-item.warning {
    color: #856404;
}

.modal-footer {
    padding: 16px 24px;
    border-top: 1px solid #e9ecef;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8f9fa;
}

.auto-close-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
    color: #495057;
    cursor: pointer;
}

.auto-close-toggle input {
    margin: 0;
}

/* Button Styles */
.btn-primary {
    background: #007bff;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s ease;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-secondary {
    background: #6c757d;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s ease;
}

.btn-secondary:hover {
    background: #545b62;
}

.btn-sm {
    padding: 6px 12px;
    font-size: 0.8rem;
}

/* Animations */
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Responsive Design */
@media (max-width: 1400px) {
    .symbol-review-content {
        grid-template-columns: 280px 1fr 320px;
        gap: 20px;
    }
    
    .detection-items {
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    }
}

@media (max-width: 1200px) {
    .symbol-review-content {
        grid-template-columns: 1fr;
        gap: 20px;
    }
    
    .template-reference-panel {
        order: -1;
    }
    
    .detection-items {
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    }
}

@media (max-width: 768px) {
    .symbol-review-tab {
        padding: 20px;
    }
    
    .symbol-review-header {
        padding: 16px;
    }
    
    .detection-overview-stats {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .detection-items {
        grid-template-columns: 1fr;
    }
    
    .modal-content {
        width: 95%;
        margin: 20px;
    }
}
```

## Risk Mitigation & Testing Strategy

### Performance Risks
1. **Large Detection Sets**: Implement virtual scrolling for 500+ detections
2. **Image Loading**: Lazy loading with intersection observer
3. **Real-time Updates**: Debounced API calls, optimistic updates

### UX Risks  
1. **Cognitive Overload**: Progressive disclosure, filtering, batch operations
2. **Context Loss**: Always-visible symbol reference, breadcrumb navigation
3. **Slow Operations**: Progress indicators, background processing

### Technical Risks
1. **Coordinate Accuracy**: Extensive testing with coordinate transformer
2. **State Synchronization**: Optimistic updates with rollback capability
3. **API Failures**: Retry logic, offline capability, error boundaries

## Success Metrics

### Performance Metrics
- Grid rendering: <100ms for 50 detections
- Image loading: <500ms average
- API response: <200ms for status updates

### User Experience Metrics  
- Time to complete review: <30 seconds per symbol type
- Error rate: <2% false accepts/rejects
- User satisfaction: >4.5/5 in testing

### Technical Metrics
- Test coverage: >90%
- API reliability: >99.9%
- Coordinate accuracy: 100% transformation correctness

This comprehensive plan provides a solid foundation for implementing an efficient, intuitive Symbol Review interface that handles the complexity of reviewing potentially hundreds of detections while maintaining excellent user experience and performance.