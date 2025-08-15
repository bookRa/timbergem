import React from 'react';

const DetectionDetailsPanel = ({ 
    selectedDetection,
    onStatusUpdate,
    onDetectionDelete
}) => {
    if (!selectedDetection) {
        return (
            <div className="detection-details-panel">
                <h4>Detection Details</h4>
                <div className="no-selection">
                    <p>Select a detection on the canvas to view details</p>
                </div>
            </div>
        );
    }

    const handleAccept = () => {
        if (onStatusUpdate) {
            onStatusUpdate(selectedDetection.detectionId, 'accepted');
        }
    };

    const handleReject = () => {
        if (onStatusUpdate) {
            onStatusUpdate(selectedDetection.detectionId, 'rejected');
        }
    };

    const handleDelete = () => {
        if (onDetectionDelete && window.confirm('Are you sure you want to delete this detection?')) {
            onDetectionDelete(selectedDetection.detectionId);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'accepted': return '#28a745';
            case 'rejected': return '#dc3545';
            case 'pending': return '#ffc107';
            default: return '#6c757d';
        }
    };

    return (
        <div className="detection-details-panel">
            <h4>Detection Details</h4>
            
            <div className="detection-detail-item">
                <span className="detection-detail-label">ID:</span>
                <span className="detection-detail-value">
                    {selectedDetection.detectionId?.slice(-8) || 'Unknown'}
                </span>
            </div>
            
            <div className="detection-detail-item">
                <span className="detection-detail-label">Status:</span>
                <span 
                    className="detection-detail-value"
                    style={{ color: getStatusColor(selectedDetection.status) }}
                >
                    {selectedDetection.status?.toUpperCase() || 'PENDING'}
                </span>
            </div>
            
            <div className="detection-detail-item">
                <span className="detection-detail-label">IoU Score:</span>
                <span className="detection-detail-value">
                    {selectedDetection.iouScore ? `${(selectedDetection.iouScore * 100).toFixed(1)}%` : 'N/A'}
                </span>
            </div>
            
            <div className="detection-detail-item">
                <span className="detection-detail-label">Confidence:</span>
                <span className="detection-detail-value">
                    {selectedDetection.matchConfidence ? `${(selectedDetection.matchConfidence * 100).toFixed(1)}%` : 'N/A'}
                </span>
            </div>
            
            {selectedDetection.pdfCoords && (
                <>
                    <div className="detection-detail-item">
                        <span className="detection-detail-label">PDF Position:</span>
                        <span className="detection-detail-value">
                            ({selectedDetection.pdfCoords.left_points?.toFixed(1)}, {selectedDetection.pdfCoords.top_points?.toFixed(1)})
                        </span>
                    </div>
                    
                    <div className="detection-detail-item">
                        <span className="detection-detail-label">PDF Size:</span>
                        <span className="detection-detail-value">
                            {selectedDetection.pdfCoords.width_points?.toFixed(1)} × {selectedDetection.pdfCoords.height_points?.toFixed(1)} pts
                        </span>
                    </div>
                </>
            )}
            
            {selectedDetection.templateSize && (
                <div className="detection-detail-item">
                    <span className="detection-detail-label">Template Size:</span>
                    <span className="detection-detail-value">
                        {selectedDetection.templateSize[0]} × {selectedDetection.templateSize[1]} px
                    </span>
                </div>
            )}
            
            {selectedDetection.matchedAngle !== undefined && (
                <div className="detection-detail-item">
                    <span className="detection-detail-label">Rotation:</span>
                    <span className="detection-detail-value">
                        {selectedDetection.matchedAngle}°
                    </span>
                </div>
            )}
            
            {selectedDetection.isUserAdded && (
                <div className="detection-detail-item">
                    <span className="detection-detail-label">Source:</span>
                    <span className="detection-detail-value" style={{ color: '#007bff' }}>
                        User Added
                    </span>
                </div>
            )}
            
            <div className="detection-actions">
                {selectedDetection.status !== 'accepted' && (
                    <button 
                        className="btn btn-success"
                        onClick={handleAccept}
                    >
                        ✓ Accept Detection
                    </button>
                )}
                
                {selectedDetection.status !== 'rejected' && (
                    <button 
                        className="btn btn-warning"
                        onClick={handleReject}
                    >
                        ✗ Reject Detection
                    </button>
                )}
                
                <button 
                    className="btn btn-danger"
                    onClick={handleDelete}
                >
                    🗑️ Delete Detection
                </button>
            </div>
            
            {selectedDetection.createdAt && (
                <div className="detection-timestamp">
                    <small className="text-muted">
                        Created: {new Date(selectedDetection.createdAt).toLocaleString()}
                    </small>
                </div>
            )}
        </div>
    );
};

export default DetectionDetailsPanel;