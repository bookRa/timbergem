import React, { useState, useRef, useEffect, useCallback } from 'react';

const InteractiveDetectionCanvas = ({ 
    pageImageUrl, 
    detections = [], 
    templateImage,
    templateDimensions,
    pageMetadata,
    onDetectionUpdate,
    onDetectionAdd,
    onDetectionDelete,
    onDetectionSelect
}) => {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const imageRef = useRef(null);

    const [canvasState, setCanvasState] = useState({
        scale: 1.0,
        offset: { x: 0, y: 0 },
        selectedDetection: null,
        isAddingDetection: false,
        dragState: null,
        imageLoaded: false,
        canvasSize: { width: 800, height: 600 }
    });

    // Load and setup page image
    useEffect(() => {
        if (!pageImageUrl) return;

        const img = new Image();
        img.onload = () => {
            imageRef.current = img;
            setupCanvas(img);
            setCanvasState(prev => ({ ...prev, imageLoaded: true }));
        };
        img.onerror = () => {
            console.error('Failed to load page image:', pageImageUrl);
        };
        img.src = pageImageUrl;
    }, [pageImageUrl]);

    // Setup canvas dimensions and scaling
    const setupCanvas = useCallback((img) => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        
        if (!canvas || !container || !img) return;

        // Get container size - use actual container dimensions with minimal padding
        const containerRect = container.getBoundingClientRect();
        const containerWidth = containerRect.width - 24; // Minimal padding (12px each side)
        const containerHeight = containerRect.height - 80; // Reduced space for controls

        // Calculate scale to fit image within container with reasonable sizing
        const scaleX = containerWidth / img.width;
        const scaleY = containerHeight / img.height;
        const scale = Math.min(scaleX, scaleY, 3); // Allow up to 1.5x scaling for better visibility

        // Set canvas size
        const canvasWidth = img.width * scale;
        const canvasHeight = img.height * scale;
        
        // Debug canvas setup
        console.log('🎨 Canvas setup:', {
            scale: scale.toFixed(2),
            canvasSize: `${canvasWidth.toFixed(0)}×${canvasHeight.toFixed(0)}`
        });
        
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        canvas.style.width = `${canvasWidth}px`;
        canvas.style.height = `${canvasHeight}px`;

        // Update canvas state
        setCanvasState(prev => ({
            ...prev,
            scale,
            canvasSize: { width: canvasWidth, height: canvasHeight },
            imageSize: { width: img.width, height: img.height }
        }));

        // Initial render
        renderCanvas();
    }, []);

    // Main canvas rendering function
    const renderCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        const img = imageRef.current;
        
        if (!canvas || !img || !canvasState.imageLoaded) return;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 1. Draw page image as background
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // Canvas is ready and rendering

        // 2. Draw detection overlays
        detections.forEach(detection => {
            renderDetectionOverlay(ctx, detection);
        });

        // 3. Draw template preview if adding detection
        if (canvasState.isAddingDetection && canvasState.previewPosition) {
            renderTemplatePreview(ctx, canvasState.previewPosition);
        }
    }, [detections, canvasState, templateDimensions]);

    // Render individual detection overlay
    const renderDetectionOverlay = (ctx, detection) => {
        if (!detection.pdfCoords) {
            console.log('⚠️ Detection missing pdfCoords:', detection);
            return;
        }

        // Convert PDF coords to canvas coords
        const canvasCoords = pdfToCanvas(detection.pdfCoords);
        const { x, y, width, height } = canvasCoords;
        
        // Render detection box

        // Get styling based on detection status and selection
        const isSelected = canvasState.selectedDetection?.detectionId === detection.detectionId;
        const style = getDetectionStyle(detection.status, isSelected);

        // Draw bounding box
        ctx.save();
        ctx.strokeStyle = style.borderColor;
        ctx.lineWidth = style.borderWidth;
        ctx.fillStyle = style.fillColor;
        
        ctx.fillRect(x, y, width, height);
        ctx.strokeRect(x, y, width, height);

        // Draw confidence label
        ctx.fillStyle = style.borderColor;
        ctx.font = '12px Arial';
        ctx.fillText(
            `IoU: ${(detection.iouScore * 100).toFixed(1)}%`,
            x + 2, y - 5
        );

        // Draw resize handles if selected
        if (isSelected) {
            renderSelectionHandles(ctx, x, y, width, height);
        }

        ctx.restore();
    };

    // Render template preview for adding new detections
    const renderTemplatePreview = (ctx, position) => {
        if (!templateDimensions) {
            console.log('⚠️ No template dimensions available for preview');
            return;
        }

        console.log('🎯 Rendering template preview:', { templateDimensions, position });

        const templateSize = {
            width: (templateDimensions.width_pixels_300dpi * canvasState.scale),
            height: (templateDimensions.height_pixels_300dpi * canvasState.scale)
        };

        const x = position.x - templateSize.width / 2;
        const y = position.y - templateSize.height / 2;

        ctx.save();
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 2;
        ctx.fillStyle = 'rgba(0, 123, 255, 0.2)';
        ctx.setLineDash([5, 5]);
        
        ctx.fillRect(x, y, templateSize.width, templateSize.height);
        ctx.strokeRect(x, y, templateSize.width, templateSize.height);
        
        ctx.restore();
    };

    // Render selection handles for editing
    const renderSelectionHandles = (ctx, x, y, width, height) => {
        const handleSize = 8;
        const handles = [
            { x: x - handleSize/2, y: y - handleSize/2 }, // Top-left
            { x: x + width - handleSize/2, y: y - handleSize/2 }, // Top-right
            { x: x - handleSize/2, y: y + height - handleSize/2 }, // Bottom-left
            { x: x + width - handleSize/2, y: y + height - handleSize/2 }, // Bottom-right
        ];

        ctx.fillStyle = '#007bff';
        handles.forEach(handle => {
            ctx.fillRect(handle.x, handle.y, handleSize, handleSize);
        });
    };

    // Get styling for detection overlay
    const getDetectionStyle = (status, isSelected) => {
        const styles = {
            pending: { borderColor: '#ffc107', fillColor: 'rgba(255,193,7,0.2)' },
            accepted: { borderColor: '#28a745', fillColor: 'rgba(40,167,69,0.2)' },
            rejected: { borderColor: '#dc3545', fillColor: 'rgba(220,53,69,0.2)' }
        };
        
        const style = styles[status] || styles.pending;
        return {
            ...style,
            borderWidth: isSelected ? 3 : 2
        };
    };

    // Convert PDF coordinates to canvas coordinates
    const pdfToCanvas = (pdfCoords) => {
        if (!canvasState.scale) {
            return { x: 0, y: 0, width: 0, height: 0 };
        }

        // PDF to image coordinates (300 DPI)
        // Note: PDF coordinates are in points (72 DPI), image is 300 DPI
        const dpiScale = 300 / 72;
        const imageX = pdfCoords.left_points * dpiScale;
        const imageY = pdfCoords.top_points * dpiScale;
        const imageWidth = pdfCoords.width_points * dpiScale;
        const imageHeight = pdfCoords.height_points * dpiScale;

        // Image to canvas coordinates
        const canvasCoords = {
            x: imageX * canvasState.scale,
            y: imageY * canvasState.scale,
            width: imageWidth * canvasState.scale,
            height: imageHeight * canvasState.scale
        };

        // PDF→Canvas coordinate conversion complete

        return canvasCoords;
    };

    // Convert canvas coordinates to PDF coordinates
    const canvasToPdf = (canvasCoords) => {
        if (!canvasState.scale) {
            return { left_points: 0, top_points: 0, width_points: 0, height_points: 0 };
        }

        // Canvas to image coordinates
        const imageX = canvasCoords.x / canvasState.scale;
        const imageY = canvasCoords.y / canvasState.scale;
        const imageWidth = canvasCoords.width / canvasState.scale;
        const imageHeight = canvasCoords.height / canvasState.scale;

        // Image to PDF coordinates (convert from 300 DPI to 72 DPI)
        const dpiScale = 72 / 300;
        return {
            left_points: imageX * dpiScale,
            top_points: imageY * dpiScale,
            width_points: imageWidth * dpiScale,
            height_points: imageHeight * dpiScale
        };
    };

    // Get canvas coordinates from mouse event
    const getCanvasCoordinates = (event) => {
        const canvas = canvasRef.current;
        if (!canvas) return { x: 0, y: 0 };

        const rect = canvas.getBoundingClientRect();
        return {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
    };

    // Check if point is inside detection bounding box
    const isPointInDetection = (point, detection) => {
        const canvasCoords = pdfToCanvas(detection.pdfCoords);
        return (
            point.x >= canvasCoords.x &&
            point.x <= canvasCoords.x + canvasCoords.width &&
            point.y >= canvasCoords.y &&
            point.y <= canvasCoords.y + canvasCoords.height
        );
    };

    // Mouse event handlers
    const handleMouseDown = (event) => {
        const clickPoint = getCanvasCoordinates(event);

        if (canvasState.isAddingDetection) {
            // Add new detection at click point
            handleAddDetection(clickPoint);
            return;
        }

        // Find clicked detection
        const clickedDetection = detections.find(det => 
            isPointInDetection(clickPoint, det)
        );

        if (clickedDetection) {
            setCanvasState(prev => ({
                ...prev,
                selectedDetection: clickedDetection,
                dragState: {
                    isDragging: true,
                    startPoint: clickPoint,
                    startCoords: pdfToCanvas(clickedDetection.pdfCoords)
                }
            }));
            
            if (onDetectionSelect) {
                onDetectionSelect(clickedDetection);
            }
        } else {
            // Clear selection
            setCanvasState(prev => ({
                ...prev,
                selectedDetection: null
            }));
            
            if (onDetectionSelect) {
                onDetectionSelect(null);
            }
        }
    };

    const handleMouseMove = (event) => {
        const currentPoint = getCanvasCoordinates(event);

        // Update preview position for add mode
        if (canvasState.isAddingDetection) {
            setCanvasState(prev => ({
                ...prev,
                previewPosition: currentPoint
            }));
            renderCanvas();
            return;
        }

        // Handle dragging
        if (canvasState.dragState?.isDragging && canvasState.selectedDetection) {
            const deltaX = currentPoint.x - canvasState.dragState.startPoint.x;
            const deltaY = currentPoint.y - canvasState.dragState.startPoint.y;

            const newCanvasCoords = {
                x: canvasState.dragState.startCoords.x + deltaX,
                y: canvasState.dragState.startCoords.y + deltaY,
                width: canvasState.dragState.startCoords.width,
                height: canvasState.dragState.startCoords.height
            };

            // Convert to PDF coordinates and update detection
            const newPdfCoords = canvasToPdf(newCanvasCoords);
            
            // Create updated detection for local state
            const updatedDetection = {
                ...canvasState.selectedDetection,
                pdfCoords: newPdfCoords
            };

            setCanvasState(prev => ({
                ...prev,
                selectedDetection: updatedDetection
            }));

            renderCanvas();
        }
    };

    const handleMouseUp = (event) => {
        if (canvasState.dragState?.isDragging && canvasState.selectedDetection) {
            // Finalize the drag operation
            const newPdfCoords = canvasState.selectedDetection.pdfCoords;
            
            if (onDetectionUpdate) {
                onDetectionUpdate(canvasState.selectedDetection.detectionId, newPdfCoords);
            }
        }

        setCanvasState(prev => ({
            ...prev,
            dragState: null
        }));
    };

    // Handle adding new detection
    const handleAddDetection = (clickPoint) => {
        if (!templateDimensions) return;

        const templateSize = {
            width: (templateDimensions.width_pixels_300dpi * canvasState.scale),
            height: (templateDimensions.height_pixels_300dpi * canvasState.scale)
        };

        const canvasCoords = {
            x: clickPoint.x - templateSize.width / 2,
            y: clickPoint.y - templateSize.height / 2,
            width: templateSize.width,
            height: templateSize.height
        };

        const pdfCoords = canvasToPdf(canvasCoords);

        if (onDetectionAdd) {
            onDetectionAdd(pdfCoords);
        }

        // Exit add mode
        setCanvasState(prev => ({
            ...prev,
            isAddingDetection: false,
            previewPosition: null
        }));
    };

    // Control functions
    const startAddMode = () => {
        setCanvasState(prev => ({
            ...prev,
            isAddingDetection: true,
            selectedDetection: null
        }));
    };

    const cancelAddMode = () => {
        setCanvasState(prev => ({
            ...prev,
            isAddingDetection: false,
            previewPosition: null
        }));
    };

    const resetView = () => {
        if (imageRef.current) {
            setupCanvas(imageRef.current);
        }
    };

    // Re-render when detections or canvas state changes
    useEffect(() => {
        renderCanvas();
    }, [renderCanvas]);

    return (
        <div ref={containerRef} className="interactive-detection-canvas">
            <div className="canvas-container">
                <canvas 
                    ref={canvasRef}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    className="detection-canvas"
                    style={{ 
                        cursor: canvasState.isAddingDetection ? 'crosshair' : 'default',
                        border: '1px solid #dee2e6'
                    }}
                />
                {!canvasState.imageLoaded && (
                    <div className="canvas-loading">
                        <div className="loading-spinner" />
                        <p>Loading page image...</p>
                    </div>
                )}
            </div>
            
            <div className="canvas-controls">
                <button 
                    className={`btn ${canvasState.isAddingDetection ? 'btn-danger' : 'btn-primary'}`}
                    onClick={canvasState.isAddingDetection ? cancelAddMode : startAddMode}
                    disabled={!templateDimensions}
                >
                    {canvasState.isAddingDetection ? '✕ Cancel Add' : '+ Add Detection'}
                </button>
                
                <button 
                    className="btn btn-secondary"
                    onClick={resetView}
                >
                    🔄 Reset View
                </button>
                
                {canvasState.selectedDetection && (
                    <button 
                        className="btn btn-danger"
                        onClick={() => {
                            if (onDetectionDelete) {
                                onDetectionDelete(canvasState.selectedDetection.detectionId);
                            }
                            setCanvasState(prev => ({ ...prev, selectedDetection: null }));
                        }}
                    >
                        🗑️ Delete Selected
                    </button>
                )}
                
                <div className="canvas-info">
                    <span>Scale: {(canvasState.scale * 100).toFixed(1)}%</span>
                    {canvasState.selectedDetection && (
                        <span>Selected: {canvasState.selectedDetection.detectionId?.slice(-6)}</span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default InteractiveDetectionCanvas;