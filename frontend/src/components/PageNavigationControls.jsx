import React from 'react';

const PageNavigationControls = ({ 
    currentPage, 
    totalPages, 
    onPageChange,
    pagesWithDetections = [] 
}) => {
    const handlePrevPage = () => {
        if (currentPage > 1) {
            onPageChange(currentPage - 1);
        }
    };

    const handleNextPage = () => {
        if (currentPage < totalPages) {
            onPageChange(currentPage + 1);
        }
    };

    const handlePageSelect = (event) => {
        const selectedPage = parseInt(event.target.value);
        onPageChange(selectedPage);
    };

    const hasDetectionsOnPage = (pageNum) => {
        return pagesWithDetections.includes(pageNum);
    };

    return (
        <div className="page-navigation-controls">
            <button 
                className="page-nav-button"
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
            >
                ← Previous
            </button>
            
            <div className="page-selector">
                <label htmlFor="page-select">Page:</label>
                <select 
                    id="page-select"
                    value={currentPage} 
                    onChange={handlePageSelect}
                    className="page-select"
                >
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
                        <option key={pageNum} value={pageNum}>
                            {pageNum} {hasDetectionsOnPage(pageNum) ? '📍' : ''}
                        </option>
                    ))}
                </select>
            </div>
            
            <span className="page-info">
                Page {currentPage} of {totalPages}
            </span>
            
            <button 
                className="page-nav-button"
                onClick={handleNextPage}
                disabled={currentPage >= totalPages}
            >
                Next →
            </button>
            
            {pagesWithDetections.length > 0 && (
                <div className="detection-summary">
                    <span className="detection-count">
                        {pagesWithDetections.length} pages with detections
                    </span>
                </div>
            )}
        </div>
    );
};

export default PageNavigationControls;