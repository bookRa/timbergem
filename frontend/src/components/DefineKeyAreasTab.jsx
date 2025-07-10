import React, { useState, useRef, useEffect } from 'react';
import { fabric } from 'fabric';

const DefineKeyAreasTab = ({ 
    docInfo, 
    allAnnotations, 
    pageSummaries, 
    onAnnotationsChange, 
    onSummaryChange, 
    onSaveData 
}) => {
    const [selectedTool, setSelectedTool] = useState(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [canvasRefs, setCanvasRefs] = useState({});
    const [fabricCanvases, setFabricCanvases] = useState({});
    const [editingSummary, setEditingSummary] = useState({});

    const annotationTools = [
        { id: 'TitleBlock', label: 'Title Block', color: '#FF6B6B', icon: '📋' },
        { id: 'DrawingArea', label: 'Drawing Area', color: '#4ECDC4', icon: '📐' },
        { id: 'NotesArea', label: 'Notes Area', color: '#45B7D1', icon: '📝' },
        { id: 'Legend', label: 'Legend', color: '#96CEB4', icon: '🗺️' }
    ];

    useEffect(() => {
        // Initialize canvases for all pages after component mounts
        const timer = setTimeout(() => {
            for (let pageNum = 1; pageNum <= docInfo.pageCount; pageNum++) {
                initializeCanvas(pageNum);
            }
        }, 100);

        return () => {
            clearTimeout(timer);
            // Cleanup canvases
            Object.values(fabricCanvases).forEach(canvas => {
                if (canvas) canvas.dispose();
            });
        };
    }, [docInfo.pageCount]);

    const initializeCanvas = (pageNumber) => {
        const canvasId = `canvas-${pageNumber}`;
        const canvasElement = document.getElementById(canvasId);
        
        if (!canvasElement || fabricCanvases[pageNumber]) return;

        const canvas = new fabric.Canvas(canvasElement, {
            selection: true,
            preserveObjectStacking: true,
            width: 600,
            height: 800
        });

        setFabricCanvases(prev => ({
            ...prev,
            [pageNumber]: canvas
        }));

        // Load background image
        const imageUrl = `/data/processed/${docInfo.docId}/page_${pageNumber}.png`;
        fabric.Image.fromURL(imageUrl, (img) => {
            if (!canvas || canvas._disposed) return;
            
            const scale = Math.min(600 / img.width, 800 / img.height);
            img.scale(scale);
            
            canvas.setWidth(img.width * scale);
            canvas.setHeight(img.height * scale);
            
            canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                scaleX: scale,
                scaleY: scale
            });
        });

        // Load existing annotations
        const existingAnnotations = allAnnotations[pageNumber] || [];
        existingAnnotations.forEach(annotation => {
            const tool = annotationTools.find(t => t.id === annotation.tag);
            if (tool) {
                const rect = new fabric.Rect({
                    left: annotation.left,
                    top: annotation.top,
                    width: annotation.width,
                    height: annotation.height,
                    fill: 'transparent',
                    stroke: tool.color,
                    strokeWidth: 2,
                    strokeDashArray: [5, 5],
                    selectable: true,
                    hasControls: true,
                    hasBorders: true,
                    annotationTag: annotation.tag,
                    annotationId: annotation.id
                });

                canvas.add(rect);
            }
        });

        // Setup drawing interactions
        setupCanvasInteractions(canvas, pageNumber);
    };

    const setupCanvasInteractions = (canvas, pageNumber) => {
        let isDown = false;
        let origX, origY;
        let rect;

        canvas.on('mouse:down', (o) => {
            if (!selectedTool || !isDrawing) return;
            
            isDown = true;
            const pointer = canvas.getPointer(o.e);
            origX = pointer.x;
            origY = pointer.y;
            
            const tool = annotationTools.find(t => t.id === selectedTool);
            
            rect = new fabric.Rect({
                left: origX,
                top: origY,
                originX: 'left',
                originY: 'top',
                width: 1,
                height: 1,
                fill: 'transparent',
                stroke: tool.color,
                strokeWidth: 2,
                strokeDashArray: [5, 5],
                selectable: true,
                hasControls: true,
                hasBorders: true,
                annotationTag: selectedTool,
                annotationId: Date.now().toString()
            });
            
            canvas.add(rect);
        });

        canvas.on('mouse:move', (o) => {
            if (!isDown || !isDrawing) return;
            
            const pointer = canvas.getPointer(o.e);
            
            if (origX > pointer.x) {
                rect.set({ left: Math.abs(pointer.x) });
            }
            if (origY > pointer.y) {
                rect.set({ top: Math.abs(pointer.y) });
            }
            
            rect.set({ width: Math.abs(origX - pointer.x) });
            rect.set({ height: Math.abs(origY - pointer.y) });
            
            canvas.renderAll();
        });

        canvas.on('mouse:up', () => {
            if (!isDown || !isDrawing) return;
            isDown = false;
            
            // Update annotations
            updateAnnotationsFromCanvas(canvas, pageNumber);
            setIsDrawing(false);
            setSelectedTool(null);
        });

        canvas.on('object:modified', () => {
            updateAnnotationsFromCanvas(canvas, pageNumber);
        });
    };

    const updateAnnotationsFromCanvas = (canvas, pageNumber) => {
        const objects = canvas.getObjects();
        const annotations = objects
            .filter(obj => obj.annotationTag)
            .map(obj => ({
                id: obj.annotationId,
                tag: obj.annotationTag,
                left: obj.left,
                top: obj.top,
                width: obj.width * obj.scaleX,
                height: obj.height * obj.scaleY,
                pageNumber: pageNumber
            }));
        
        onAnnotationsChange(pageNumber, annotations);
    };

    const startDrawing = (toolId) => {
        setSelectedTool(toolId);
        setIsDrawing(true);
    };

    const deleteAnnotation = (pageNumber, annotationId) => {
        const canvas = fabricCanvases[pageNumber];
        if (!canvas) return;

        const objectToRemove = canvas.getObjects().find(obj => obj.annotationId === annotationId);
        if (objectToRemove) {
            canvas.remove(objectToRemove);
            updateAnnotationsFromCanvas(canvas, pageNumber);
        }
    };

    const generatePageSummary = async (pageNumber) => {
        try {
            const response = await fetch('/api/generate_summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    docId: docInfo.docId,
                    pageNumber: pageNumber
                })
            });
            
            const data = await response.json();
            onSummaryChange(pageNumber, data.summary);
        } catch (err) {
            console.error('Failed to generate summary:', err);
        }
    };

    const getThumbnailForAnnotation = (annotation) => {
        // This would generate a thumbnail from the canvas area
        // For now, return a placeholder
        return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
    };

    const renderSidebar = () => (
        <div className="sidebar">
            <div className="annotation-tools">
                <h3>Key Area Tools</h3>
                {annotationTools.map(tool => (
                    <button
                        key={tool.id}
                        className={`tool-button ${selectedTool === tool.id ? 'active' : ''}`}
                        onClick={() => startDrawing(tool.id)}
                        style={{ borderColor: tool.color }}
                    >
                        {tool.icon} {tool.label}
                    </button>
                ))}
            </div>

            <div className="annotation-list">
                <h3>Annotations</h3>
                {Object.entries(allAnnotations).map(([pageNumber, pageAnnotations]) => (
                    <div key={pageNumber} className="page-annotations">
                        <h4>Page {pageNumber}</h4>
                        {pageAnnotations.map(annotation => {
                            const tool = annotationTools.find(t => t.id === annotation.tag);
                            return (
                                <div key={annotation.id} className="annotation-item">
                                    <img 
                                        src={getThumbnailForAnnotation(annotation)}
                                        alt={`${tool?.label} thumbnail`}
                                        className="annotation-thumbnail"
                                    />
                                    <div className="annotation-info">
                                        <span style={{ color: tool?.color }}>
                                            {tool?.icon} {tool?.label}
                                        </span>
                                        <button 
                                            onClick={() => deleteAnnotation(parseInt(pageNumber), annotation.id)}
                                            className="delete-btn"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ))}
            </div>

            <div className="generate-section">
                <button onClick={onSaveData} className="generate-button">
                    Generate Knowledge Graph
                </button>
            </div>
        </div>
    );

    const renderPageContent = (pageNumber) => (
        <div key={pageNumber} className="page-content">
            <div className="page-header">
                <h3>Page {pageNumber}</h3>
            </div>
            
            <div className="page-layout">
                <div className="page-summary">
                    <h4>Page Summary</h4>
                    {editingSummary[pageNumber] ? (
                        <div>
                            <textarea
                                value={pageSummaries[pageNumber] || ''}
                                onChange={(e) => onSummaryChange(pageNumber, e.target.value)}
                                className="summary-textarea"
                                placeholder="Lorem ipsum dolor sit amet, consectetur adipiscing elit..."
                            />
                            <div className="summary-controls">
                                <button onClick={() => setEditingSummary(prev => ({ ...prev, [pageNumber]: false }))}>
                                    Save
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div>
                            <p className="summary-text">
                                {pageSummaries[pageNumber] || 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras in fermentum dui, vel bibendum leo. Aenean porttitor nibh quam, a gravida dui euismod quis. Donec lacinia convallis malesuada. Nam tincidunt consequat elit sit amet posuere. Proin auctor fringilla augue, vel tempor risus suscipit et. Nunc ultrices lectus a enim posuere, et hendrerit orci aliquam. Curabitur efficitur tristique malesuada.'}
                            </p>
                            <button 
                                onClick={() => setEditingSummary(prev => ({ ...prev, [pageNumber]: true }))}
                                className="edit-button"
                            >
                                Edit Page Notes
                            </button>
                            <button 
                                onClick={() => generatePageSummary(pageNumber)}
                                className="ai-button"
                            >
                                🤖 AI Generate
                            </button>
                        </div>
                    )}
                </div>

                <div className="page-canvas-container">
                    <canvas 
                        id={`canvas-${pageNumber}`}
                        className="page-canvas"
                    />
                </div>

                <div className="page-sections">
                    <div className="title-block">
                        <h4>Title Block:</h4>
                        <button className="add-button">Add</button>
                    </div>
                    <div className="drawing-area">
                        <h4>Drawing Area:</h4>
                        <button className="add-button">Add</button>
                    </div>
                    <div className="notes-area">
                        <h4>Notes Area:</h4>
                        <button className="add-button">Add</button>
                    </div>
                    <div className="legend">
                        <h4>Legend:</h4>
                        <button className="add-button">Add</button>
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="define-key-areas-tab">
            {renderSidebar()}
            
            <div className="pages-container">
                {Array.from({ length: docInfo.pageCount }, (_, i) => i + 1).map(pageNumber => 
                    renderPageContent(pageNumber)
                )}
            </div>
        </div>
    );
};

export default DefineKeyAreasTab; 