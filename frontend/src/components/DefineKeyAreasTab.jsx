import React, { useState, useRef, useEffect } from 'react';
import { fabric } from 'fabric';

const DefineKeyAreasTab = ({ 
    docInfo, 
    allAnnotations, 
    pageSummaries, 
    onAnnotationsChange, 
    onSummaryChange, 
    onSaveData,
    pixmapStatus = {},
    onPixmapCheck = () => {}
}) => {
    const [selectedTool, setSelectedTool] = useState(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [drawingPage, setDrawingPage] = useState(null); // Track which page is in drawing mode
    const [canvasRefs, setCanvasRefs] = useState({});
    const [fabricCanvases, setFabricCanvases] = useState({});
    const [editingSummary, setEditingSummary] = useState({});
    const [selectedAnnotation, setSelectedAnnotation] = useState(null); // Track selected annotation
    const [canvasDimensions, setCanvasDimensions] = useState({}); // Track canvas dimensions for coordinate mapping
    
    // Use refs to store current state for event handlers
    const stateRef = useRef({ selectedTool: null, isDrawing: false, drawingPage: null });

    // Update ref whenever state changes
    useEffect(() => {
        stateRef.current = { selectedTool, isDrawing, drawingPage };
    }, [selectedTool, isDrawing, drawingPage]);

    // Reload canvas backgrounds when pixmaps become available
    useEffect(() => {
        Object.entries(pixmapStatus).forEach(([pageNum, status]) => {
            const pageNumber = parseInt(pageNum);
            if (status === 'ready' && fabricCanvases[pageNumber]) {
                const canvas = fabricCanvases[pageNumber];
                if (!canvas.backgroundImage) {
                    console.log(`Loading background for page ${pageNumber} (pixmap now ready)`);
                    const legacyImageUrl = `/data/processed/${docInfo.docId}/page_${pageNumber}.png`;
                    fabric.Image.fromURL(legacyImageUrl, (img) => {
                        if (!canvas || canvas._disposed) return;
                        
                        // Same dynamic sizing logic as in initializeCanvas
                        const imageAspectRatio = img.width / img.height;
                        const maxCanvasWidth = 800;
                        const maxCanvasHeight = 600;
                        
                        let actualCanvasWidth, actualCanvasHeight, scale;
                        
                        if (imageAspectRatio > (maxCanvasWidth / maxCanvasHeight)) {
                            actualCanvasWidth = maxCanvasWidth;
                            actualCanvasHeight = maxCanvasWidth / imageAspectRatio;
                            scale = maxCanvasWidth / img.width;
                        } else {
                            actualCanvasHeight = maxCanvasHeight;
                            actualCanvasWidth = maxCanvasHeight * imageAspectRatio;
                            scale = maxCanvasHeight / img.height;
                        }
                        
                        img.scale(scale);
                        canvas.setWidth(actualCanvasWidth);
                        canvas.setHeight(actualCanvasHeight);
                        
                        setCanvasDimensions(prev => ({
                            ...prev,
                            [pageNumber]: {
                                width: actualCanvasWidth,
                                height: actualCanvasHeight
                            }
                        }));
                        
                        canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                            scaleX: scale,
                            scaleY: scale
                        });
                        
                        console.log(`Background loaded for page ${pageNumber}`);
                    });
                }
            }
        });
    }, [pixmapStatus, fabricCanvases, docInfo.docId]);

    const annotationTools = [
        { id: 'TitleBlock', label: 'Title Block', color: '#FF6B6B', icon: '📋' },
        { id: 'DrawingArea', label: 'Drawing Area', color: '#4ECDC4', icon: '📐' },
        { id: 'NotesArea', label: 'Notes Area', color: '#45B7D1', icon: '📝' },
        { id: 'Legend', label: 'Legend', color: '#96CEB4', icon: '🗺️' }
    ];

    useEffect(() => {
        let attempts = 0;
        const maxAttempts = 5;
        
        const initializeAllCanvases = () => {
            attempts++;
            console.log(`Canvas initialization attempt ${attempts}`);
            
            let successCount = 0;
            for (let pageNum = 1; pageNum <= docInfo.totalPages; pageNum++) {
                const canvasElement = document.getElementById(`canvas-${pageNum}`);
                if (canvasElement && !fabricCanvases[pageNum]) {
                    initializeCanvas(pageNum);
                    successCount++;
                }
            }
            
            console.log(`Initialized ${successCount} canvases on attempt ${attempts}`);
            
            // Retry if not all canvases were initialized and we haven't exceeded max attempts
            if (successCount < docInfo.totalPages && attempts < maxAttempts) {
                setTimeout(initializeAllCanvases, 500);
            }
        };
        
        // Start initialization after a delay
        const timer = setTimeout(initializeAllCanvases, 300);

        return () => {
            clearTimeout(timer);
            // Cleanup canvases
            Object.values(fabricCanvases).forEach(canvas => {
                if (canvas) canvas.dispose();
            });
        };
    }, [docInfo.totalPages, docInfo.docId]);

    const initializeCanvas = (pageNumber) => {
        const canvasId = `canvas-${pageNumber}`;
        const canvasElement = document.getElementById(canvasId);
        
        if (!canvasElement) {
            console.log(`Canvas element not found for page ${pageNumber}`);
            return;
        }
        
        if (fabricCanvases[pageNumber]) {
            console.log(`Canvas already exists for page ${pageNumber}`);
            return;
        }

        console.log(`Initializing canvas for page ${pageNumber}`);

        // Start with a temporary canvas size - we'll resize after loading the image
        const canvas = new fabric.Canvas(canvasElement, {
            selection: true,
            preserveObjectStacking: true,
            width: 800,  // Temporary initial size
            height: 600  // Will be adjusted based on actual image dimensions
        });

        // Store canvas in state immediately
        setFabricCanvases(prev => {
            const newCanvases = { ...prev, [pageNumber]: canvas };
            console.log('Updated canvases:', Object.keys(newCanvases));
            return newCanvases;
        });

        // Check if pixmap is ready before loading background image
        const pageStatus = pixmapStatus[pageNumber];
        if (pageStatus !== 'ready') {
            console.log(`Page ${pageNumber} pixmap not ready yet (status: ${pageStatus}), skipping background load`);
            return;
        }

        // Load background image - try legacy format first, then high-res pixmap
        const legacyImageUrl = `/data/processed/${docInfo.docId}/page_${pageNumber}.png`;
        
        fabric.Image.fromURL(legacyImageUrl, (img) => {
            if (!canvas || canvas._disposed) return;
            
            // DYNAMIC CANVAS SIZING: Calculate optimal canvas size based on image aspect ratio
            const imageAspectRatio = img.width / img.height;
            const maxCanvasWidth = 800;   // Maximum width for UI layout
            const maxCanvasHeight = 600;  // Maximum height for UI layout
            
            let actualCanvasWidth, actualCanvasHeight, scale;
            
            // Determine optimal canvas dimensions based on aspect ratio
            if (imageAspectRatio > (maxCanvasWidth / maxCanvasHeight)) {
                // Image is wider (landscape) - fit to width
                actualCanvasWidth = maxCanvasWidth;
                actualCanvasHeight = maxCanvasWidth / imageAspectRatio;
                scale = maxCanvasWidth / img.width;
            } else {
                // Image is taller (portrait) - fit to height
                actualCanvasHeight = maxCanvasHeight;
                actualCanvasWidth = maxCanvasHeight * imageAspectRatio;
                scale = maxCanvasHeight / img.height;
            }
            
            // Scale the image to match canvas
            img.scale(scale);
            
            // Set canvas to exact scaled image dimensions
            canvas.setWidth(actualCanvasWidth);
            canvas.setHeight(actualCanvasHeight);
            
            // Store canvas dimensions for coordinate mapping - these MUST match what annotations use
            setCanvasDimensions(prev => ({
                ...prev,
                [pageNumber]: {
                    width: actualCanvasWidth,
                    height: actualCanvasHeight
                }
            }));
            
            console.log(`Canvas ${pageNumber} initialized: ${actualCanvasWidth.toFixed(1)}x${actualCanvasHeight.toFixed(1)} (scale: ${scale.toFixed(3)})`);
            console.log(`  Image: ${img.width}x${img.height}, Aspect ratio: ${imageAspectRatio.toFixed(3)}`);
            
            canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                scaleX: scale,
                scaleY: scale
            });
        }, (error) => {
            console.log(`Failed to load legacy image for page ${pageNumber}, trying high-res pixmap`);
            
            // Try high-res pixmap format
            const pixmapImageUrl = `/data/processed/${docInfo.docId}/page_${pageNumber}/page_${pageNumber}_pixmap.png`;
            
            fabric.Image.fromURL(pixmapImageUrl, (img) => {
                if (!canvas || canvas._disposed) return;
                
                // Same sizing logic for high-res pixmap
                const imageAspectRatio = img.width / img.height;
                const maxCanvasWidth = 800;
                const maxCanvasHeight = 600;
                
                let actualCanvasWidth, actualCanvasHeight, scale;
                
                if (imageAspectRatio > (maxCanvasWidth / maxCanvasHeight)) {
                    actualCanvasWidth = maxCanvasWidth;
                    actualCanvasHeight = maxCanvasWidth / imageAspectRatio;
                    scale = maxCanvasWidth / img.width;
                } else {
                    actualCanvasHeight = maxCanvasHeight;
                    actualCanvasWidth = maxCanvasHeight * imageAspectRatio;
                    scale = maxCanvasHeight / img.height;
                }
                
                img.scale(scale);
                canvas.setWidth(actualCanvasWidth);
                canvas.setHeight(actualCanvasHeight);
                
                setCanvasDimensions(prev => ({
                    ...prev,
                    [pageNumber]: {
                        width: actualCanvasWidth,
                        height: actualCanvasHeight
                    }
                }));
                
                console.log(`Canvas ${pageNumber} initialized with high-res pixmap: ${actualCanvasWidth.toFixed(1)}x${actualCanvasHeight.toFixed(1)}`);
                
                canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                    scaleX: scale,
                    scaleY: scale
                });
            }, (pixmapError) => {
                console.error(`Failed to load both legacy and high-res images for page ${pageNumber}:`, error, pixmapError);
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
                    strokeWidth: 3,
                    strokeDashArray: [8, 4],
                    strokeUniform: true, // Keep stroke width consistent during scaling
                    selectable: true,
                    hasControls: true,
                    hasBorders: true,
                    annotationTag: annotation.tag,
                    annotationId: annotation.id
                });

                canvas.add(rect);
            }
        });

        // Setup basic canvas interactions
        setupCanvasInteractions(canvas, pageNumber);
        
        console.log(`Canvas ${pageNumber} initialized and interactions set up`);
    };

    const setupCanvasInteractions = (canvas, pageNumber) => {
        let isDown = false;
        let origX, origY;
        let rect;

        // Store page number on canvas for reference
        canvas.pageNumber = pageNumber;

        canvas.on('mouse:down', (o) => {
            // Get current state from ref
            const { selectedTool: currentTool, isDrawing: currentDrawing, drawingPage: currentDrawingPage } = stateRef.current;
            
            console.log(`Canvas ${pageNumber} clicked`);
            console.log('Current state from ref:', { currentTool, currentDrawing, currentDrawingPage });
            
            // Only allow drawing if we're in drawing mode AND this is the correct page
            if (!currentTool || !currentDrawing || currentDrawingPage !== pageNumber) {
                console.log(`Canvas click blocked for page ${pageNumber}`);
                return;
            }
            
            console.log(`Starting to draw ${currentTool} on page ${pageNumber}`);
            
            isDown = true;
            const pointer = canvas.getPointer(o.e);
            origX = pointer.x;
            origY = pointer.y;
            
            const tool = annotationTools.find(t => t.id === currentTool);
            if (!tool) return;
            
            rect = new fabric.Rect({
                left: origX,
                top: origY,
                originX: 'left',
                originY: 'top',
                width: 1,
                height: 1,
                fill: 'transparent',
                stroke: tool.color,
                strokeWidth: 3,
                strokeDashArray: [8, 4],
                strokeUniform: true, // Keep stroke width consistent during scaling
                selectable: true,
                hasControls: true,
                hasBorders: true,
                annotationTag: currentTool,
                annotationId: `${Date.now()}-${pageNumber}`
            });
            
            canvas.add(rect);
            canvas.setActiveObject(rect);
            canvas.requestRenderAll();
        });

        canvas.on('mouse:move', (o) => {
            if (!isDown || !rect) return;
            
            const pointer = canvas.getPointer(o.e);
            
            // Calculate the rectangle dimensions
            const left = Math.min(origX, pointer.x);
            const top = Math.min(origY, pointer.y);
            const width = Math.abs(origX - pointer.x);
            const height = Math.abs(origY - pointer.y);
            
            rect.set({ 
                left: left,
                top: top,
                width: width, 
                height: height 
            });
            
            canvas.requestRenderAll();
        });

        canvas.on('mouse:up', () => {
            if (!isDown) return;
            isDown = false;
            
            console.log('Mouse up - finishing annotation');
            
            // Only finish drawing if we actually created a meaningful rectangle
            if (rect && (rect.width > 10 && rect.height > 10)) {
                console.log('Creating annotation with dimensions:', rect.width, 'x', rect.height);
                // Update annotations
                updateAnnotationsFromCanvas(canvas, pageNumber);
            } else if (rect) {
                console.log('Removing small rectangle');
                // Remove tiny rectangles
                canvas.remove(rect);
            }
            
            // Reset drawing state
            rect = null;
            setIsDrawing(false);
            setSelectedTool(null);
            setDrawingPage(null);
            canvas.requestRenderAll();
        });

        canvas.on('object:modified', () => {
            updateAnnotationsFromCanvas(canvas, pageNumber);
        });

        // Handle annotation selection
        canvas.on('selection:created', (e) => {
            const selectedObject = e.selected[0];
            if (selectedObject && selectedObject.annotationId) {
                console.log('Annotation selected on canvas:', selectedObject.annotationId);
                setSelectedAnnotation(selectedObject.annotationId);
            }
        });

        canvas.on('selection:updated', (e) => {
            const selectedObject = e.selected[0];
            if (selectedObject && selectedObject.annotationId) {
                console.log('Annotation selection updated:', selectedObject.annotationId);
                setSelectedAnnotation(selectedObject.annotationId);
            }
        });

        canvas.on('selection:cleared', () => {
            console.log('Canvas selection cleared');
            setSelectedAnnotation(null);
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

    const startDrawing = (toolId, pageNumber) => {
        console.log(`Starting drawing mode: ${toolId} on page ${pageNumber}`);
        setSelectedTool(toolId);
        setIsDrawing(true);
        setDrawingPage(pageNumber);
        
        // Focus on the specific page canvas
        const canvas = fabricCanvases[pageNumber];
        if (canvas) {
            canvas.discardActiveObject();
            canvas.renderAll();
            console.log(`Canvas found and focused for page ${pageNumber}`);
        } else {
            console.log(`No canvas found for page ${pageNumber}`);
        }
    };

    const deleteAnnotation = (pageNumber, annotationId) => {
        const canvas = fabricCanvases[pageNumber];
        if (!canvas) return;

        const objectToRemove = canvas.getObjects().find(obj => obj.annotationId === annotationId);
        if (objectToRemove) {
            canvas.remove(objectToRemove);
            updateAnnotationsFromCanvas(canvas, pageNumber);
            
            // Clear selection if the deleted annotation was selected
            if (selectedAnnotation === annotationId) {
                setSelectedAnnotation(null);
            }
        }
    };

    const selectAnnotationFromSidebar = (pageNumber, annotationId) => {
        console.log(`Selecting annotation ${annotationId} on page ${pageNumber} from sidebar`);
        
        // Scroll to the page
        const pageElement = document.getElementById(`page-content-${pageNumber}`);
        if (pageElement) {
            pageElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }

        // Select the annotation on the canvas
        const canvas = fabricCanvases[pageNumber];
        if (canvas) {
            const objectToSelect = canvas.getObjects().find(obj => obj.annotationId === annotationId);
            if (objectToSelect) {
                canvas.discardActiveObject();
                canvas.setActiveObject(objectToSelect);
                canvas.requestRenderAll();
                setSelectedAnnotation(annotationId);
                console.log('Annotation selected and page scrolled');
            }
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

    const generateHighResClippings = async () => {
        try {
            // Collect all annotations from all pages
            const allAnnotationsFlat = [];
            Object.entries(allAnnotations).forEach(([pageNumber, pageAnnotations]) => {
                pageAnnotations.forEach(annotation => {
                    allAnnotationsFlat.push(annotation);
                });
            });

            if (allAnnotationsFlat.length === 0) {
                alert('No annotations to process. Please create some key area annotations first.');
                return;
            }

            console.log('🔍 FRONTEND DEBUG - Generating clippings for annotations:', allAnnotationsFlat);
            console.log('🔍 FRONTEND DEBUG - Canvas dimensions:', canvasDimensions);
            
            // Debug: log annotation details for verification
            allAnnotationsFlat.forEach((annotation, index) => {
                const pageDims = canvasDimensions[annotation.pageNumber];
                console.log(`🔍 FRONTEND DEBUG - Annotation ${index + 1} (${annotation.tag} on page ${annotation.pageNumber}):`);
                console.log(`  📍 Coords: (${annotation.left}, ${annotation.top}) ${annotation.width}x${annotation.height}`);
                console.log(`  📐 Canvas dims: ${pageDims?.width}x${pageDims?.height}`);
                
                // Get the actual canvas element and check its properties
                const canvasElement = document.getElementById(`canvas-${annotation.pageNumber}`);
                if (canvasElement) {
                    console.log(`  🖼️  Canvas element: ${canvasElement.width}x${canvasElement.height} (actual DOM)`);
                    console.log(`  📏 Canvas style: ${canvasElement.style.width} x ${canvasElement.style.height}`);
                    
                    // Check if there's a Fabric canvas and get its dimensions
                    const fabricCanvas = fabricCanvases[annotation.pageNumber];
                    if (fabricCanvas) {
                        console.log(`  🎨 Fabric canvas: ${fabricCanvas.width}x${fabricCanvas.height}`);
                        console.log(`  🖼️  Background image:`, fabricCanvas.backgroundImage ? 
                            `${fabricCanvas.backgroundImage.width}x${fabricCanvas.backgroundImage.height} (scale: ${fabricCanvas.backgroundImage.scaleX}x${fabricCanvas.backgroundImage.scaleY})` : 
                            'None');
                        
                        // Get all objects on the canvas for comparison
                        const objects = fabricCanvas.getObjects();
                        console.log(`  📦 Canvas objects (${objects.length}):`);
                        objects.forEach((obj, objIndex) => {
                            if (obj.annotationTag) {
                                console.log(`    ${objIndex + 1}. ${obj.annotationTag}: (${obj.left}, ${obj.top}) ${obj.width}x${obj.height}`);
                            }
                        });
                    }
                }
            });

            const response = await fetch('/api/generate_clippings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    docId: docInfo.docId,
                    annotations: allAnnotationsFlat,
                    canvasDimensions: canvasDimensions
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                console.log('Clippings generated successfully:', data);
                alert(`✅ Generated ${data.clippings.length} high-resolution clippings!`);
                
                // Still call the original save function
                if (onSaveData) {
                    await onSaveData();
                }
            } else {
                console.error('Failed to generate clippings:', data.error);
                alert(`❌ Failed to generate clippings: ${data.error}`);
            }
        } catch (err) {
            console.error('Error generating clippings:', err);
            alert('❌ Error generating clippings. Check console for details.');
        }
    };

    const getThumbnailForAnnotation = (annotation) => {
        // Generate a simple colored thumbnail representing the annotation
        const tool = annotationTools.find(t => t.id === annotation.tag);
        const color = tool?.color || '#ccc';
        
        // Create a simple SVG thumbnail without emojis to avoid btoa encoding issues
        const svg = `
            <svg width="40" height="30" xmlns="http://www.w3.org/2000/svg">
                <rect x="2" y="2" width="36" height="26" fill="transparent" stroke="${color}" stroke-width="2" stroke-dasharray="3,2"/>
                <circle cx="20" cy="15" r="3" fill="${color}"/>
            </svg>
        `;
        
        // Use encodeURIComponent instead of btoa to handle any characters safely
        return `data:image/svg+xml,${encodeURIComponent(svg)}`;
    };

    const renderSidebar = () => (
        <div className="sidebar">
            <div className="annotation-list">
                <h3>All Annotations</h3>
                {Object.keys(allAnnotations).length === 0 ? (
                    <p className="empty-state">No annotations yet. Use the "Add" buttons next to each page to create key area annotations.</p>
                ) : (
                    Object.entries(allAnnotations).map(([pageNumber, pageAnnotations]) => (
                        <div key={pageNumber} className="page-annotations">
                            <h4>Page {pageNumber}</h4>
                            {pageAnnotations.map(annotation => {
                                const tool = annotationTools.find(t => t.id === annotation.tag);
                                const isSelected = selectedAnnotation === annotation.id;
                                return (
                                    <div 
                                        key={annotation.id} 
                                        className={`annotation-item ${isSelected ? 'selected' : ''}`}
                                        onClick={() => selectAnnotationFromSidebar(parseInt(pageNumber), annotation.id)}
                                        style={{ cursor: 'pointer' }}
                                    >
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
                                                onClick={(e) => {
                                                    e.stopPropagation(); // Prevent triggering selection
                                                    deleteAnnotation(parseInt(pageNumber), annotation.id);
                                                }}
                                                className="delete-btn"
                                            >
                                                🗑️
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ))
                )}
            </div>

            <div className="generate-section">
                <button onClick={generateHighResClippings} className="generate-button">
                    Generate Knowledge Graph
                </button>
            </div>
        </div>
    );

    const renderPageStatus = (pageNumber) => {
        const status = pixmapStatus[pageNumber];
        
        switch (status) {
            case 'ready':
                return (
                    <div className="page-status ready">
                        ✅ Image ready
                    </div>
                );
            case 'loading':
                return (
                    <div className="page-status loading">
                        🔄 Loading image...
                    </div>
                );
            case 'error':
                return (
                    <div className="page-status error">
                        ❌ Image failed to load
                        <button 
                            onClick={() => onPixmapCheck(pageNumber)}
                            className="retry-button"
                        >
                            Retry
                        </button>
                    </div>
                );
            default:
                return (
                    <div className="page-status not-available">
                        ⏳ Image not yet available
                        <button 
                            onClick={() => onPixmapCheck(pageNumber)}
                            className="check-button"
                        >
                            Check
                        </button>
                    </div>
                );
        }
    };

    const renderPageContent = (pageNumber) => (
        <div key={pageNumber} id={`page-content-${pageNumber}`} className="page-content">
            <div className="page-header">
                <h3>Page {pageNumber}</h3>
                {renderPageStatus(pageNumber)}
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
                        data-page={pageNumber}
                    />
                </div>

                <div className="page-sections">
                    <div className="title-block">
                        <h4>📋 Title Block:</h4>
                        <button 
                            className={`add-button ${selectedTool === 'TitleBlock' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                            onClick={() => startDrawing('TitleBlock', pageNumber)}
                        >
                            {selectedTool === 'TitleBlock' && isDrawing && drawingPage === pageNumber ? 'Click & Drag on Canvas' : 'Add'}
                        </button>
                    </div>
                    <div className="drawing-area">
                        <h4>📐 Drawing Area:</h4>
                        <button 
                            className={`add-button ${selectedTool === 'DrawingArea' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                            onClick={() => startDrawing('DrawingArea', pageNumber)}
                        >
                            {selectedTool === 'DrawingArea' && isDrawing && drawingPage === pageNumber ? 'Click & Drag on Canvas' : 'Add'}
                        </button>
                    </div>
                    <div className="notes-area">
                        <h4>📝 Notes Area:</h4>
                        <button 
                            className={`add-button ${selectedTool === 'NotesArea' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                            onClick={() => startDrawing('NotesArea', pageNumber)}
                        >
                            {selectedTool === 'NotesArea' && isDrawing && drawingPage === pageNumber ? 'Click & Drag on Canvas' : 'Add'}
                        </button>
                    </div>
                    <div className="legend">
                        <h4>🗺️ Legend:</h4>
                        <button 
                            className={`add-button ${selectedTool === 'Legend' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                            onClick={() => startDrawing('Legend', pageNumber)}
                        >
                            {selectedTool === 'Legend' && isDrawing && drawingPage === pageNumber ? 'Click & Drag on Canvas' : 'Add'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="define-key-areas-tab">
            {renderSidebar()}
            
            <div className="pages-container">
                {Array.from({ length: docInfo.totalPages }, (_, i) => i + 1).map(pageNumber => 
                    renderPageContent(pageNumber)
                )}
            </div>
        </div>
    );
};

export default DefineKeyAreasTab; 