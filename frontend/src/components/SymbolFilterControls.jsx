import React from 'react';

const SymbolFilterControls = ({ 
    symbols = [],
    selectedSymbol,
    statusFilter,
    confidenceThreshold,
    onSymbolChange,
    onStatusChange,
    onConfidenceChange 
}) => {
    return (
        <div className="symbol-filter-controls">
            <div className="filter-group">
                <label htmlFor="symbol-filter">Symbol:</label>
                <select 
                    id="symbol-filter"
                    value={selectedSymbol || 'all'} 
                    onChange={(e) => onSymbolChange(e.target.value === 'all' ? null : e.target.value)}
                >
                    <option value="all">All Symbols</option>
                    {symbols.map(symbol => (
                        <option key={symbol.symbolId} value={symbol.symbolId}>
                            {symbol.symbolInfo?.name || 'Unknown Symbol'}
                        </option>
                    ))}
                </select>
            </div>
            
            <div className="filter-group">
                <label htmlFor="status-filter">Status:</label>
                <select 
                    id="status-filter"
                    value={statusFilter} 
                    onChange={(e) => onStatusChange(e.target.value)}
                >
                    <option value="all">All Status</option>
                    <option value="pending">Pending</option>
                    <option value="accepted">Accepted</option>
                    <option value="rejected">Rejected</option>
                </select>
            </div>
            
            <div className="filter-group">
                <label htmlFor="confidence-filter">Min IoU:</label>
                <input 
                    id="confidence-filter"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={confidenceThreshold}
                    onChange={(e) => onConfidenceChange(parseFloat(e.target.value))}
                    className="confidence-slider"
                />
                <span className="confidence-value">
                    {(confidenceThreshold * 100).toFixed(0)}%
                </span>
            </div>
            
            <div className="filter-actions">
                <button 
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                        onSymbolChange(null);
                        onStatusChange('all');
                        onConfidenceChange(0);
                    }}
                >
                    Clear Filters
                </button>
            </div>
        </div>
    );
};

export default SymbolFilterControls;