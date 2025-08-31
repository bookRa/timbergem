import React from 'react';

const SymbolFilterControls = ({ 
    symbols = [],
    selectedSymbol,
    statusFilters = [],
    iouRange = [0, 1],
    onSymbolChange,
    onStatusChange,
    onIouRangeChange,
    docId
}) => {
    const handleStatusToggle = (status) => {
        const set = new Set(statusFilters);
        if (set.has(status)) {
            set.delete(status);
        } else {
            set.add(status);
        }
        onStatusChange(Array.from(set));
    };

    const minVal = Math.max(0, Math.min(iouRange[0], 1));
    const maxVal = Math.max(0, Math.min(iouRange[1], 1));

    // Two distinct sliders UI; enforce min ≤ max via clamping in handlers

    const handleMinChange = (val) => {
        const v = Math.min(parseFloat(val), maxVal);
        onIouRangeChange([v, maxVal]);
    };

    const handleMaxChange = (val) => {
        const v = Math.max(parseFloat(val), minVal);
        onIouRangeChange([minVal, v]);
    };

    const resetIou = () => onIouRangeChange([0, 1]);

    return (
        <div className="symbol-filter-controls" style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Symbol selection as radio with previews */}
            <div className="filter-group" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 600, fontSize: 12 }}>Symbol:</span>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #e9ecef', borderRadius: 8, padding: '4px 8px' }}>
                    <input
                        type="radio"
                        name="symbol-radio"
                        checked={!selectedSymbol}
                        onChange={() => onSymbolChange(null)}
                    />
                    <span style={{ fontSize: 12 }}>All Symbols</span>
                </label>
                {symbols.map(symbol => {
                    const previewRel = symbol.symbolInfo?.template_info?.template_relative_path;
                    const previewUrl = (docId && previewRel) ? `/data/processed/${docId}/${previewRel}` : null;
                    return (
                        <label key={symbol.symbolId} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #e9ecef', borderRadius: 8, padding: '4px 8px' }}>
                            <input
                                type="radio"
                                name="symbol-radio"
                                checked={selectedSymbol === symbol.symbolId}
                                onChange={() => onSymbolChange(symbol.symbolId)}
                            />
                            {previewUrl && (
                                <img src={previewUrl} alt={symbol.symbolInfo?.name || 'symbol'} style={{ width: 28, height: 28, objectFit: 'contain', background: '#fff', border: '1px solid #f1f3f5', borderRadius: 4 }} />
                            )}
                            <span style={{ fontSize: 12 }}>{symbol.symbolInfo?.name || 'Unknown'}</span>
                        </label>
                    );
                })}
            </div>

            {/* Status multi-select checkboxes */}
            <div className="filter-group" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 600, fontSize: 12 }}>Status:</span>
                {['pending', 'accepted', 'rejected'].map(st => (
                    <label key={st} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #e9ecef', borderRadius: 8, padding: '4px 8px' }}>
                        <input type="checkbox" checked={statusFilters.includes(st)} onChange={() => handleStatusToggle(st)} />
                        <span style={{ fontSize: 12, textTransform: 'capitalize' }}>{st}</span>
                    </label>
                ))}
            </div>

            {/* IoU two sliders: Min and Max (min ≤ max) */}
            <div className="filter-group" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 12 }}>IoU:</span>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 12 }}>Min</span>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={minVal}
                        onChange={(e) => handleMinChange(e.target.value)}
                        style={{ width: 120 }}
                    />
                </label>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 12 }}>Max</span>
                    <input
                        type="range"
                        min={minVal}
                        max="1"
                        step="0.01"
                        value={maxVal}
                        onChange={(e) => handleMaxChange(e.target.value)}
                        style={{ width: 120 }}
                    />
                </label>
                <span style={{ fontSize: 12, whiteSpace: 'nowrap' }}>{Math.round(minVal * 100)}% - {Math.round(maxVal * 100)}%</span>
                <button className="btn btn-secondary btn-sm" onClick={resetIou}>Reset</button>
            </div>

            <div className="filter-actions" style={{ marginLeft: 'auto' }}>
                <button 
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                        onSymbolChange(null);
                        onStatusChange(['pending', 'accepted', 'rejected']);
                        onIouRangeChange([0, 1]);
                    }}
                >
                    Clear Filters
                </button>
            </div>
        </div>
    );
};

export default SymbolFilterControls;