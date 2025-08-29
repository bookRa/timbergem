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
    onDetectionSelect,
    onDetectionStatusUpdate,
    onRequestDetails,
    onlyInViewport = false,
    onSelectionChange,
    clearSelectionTick
}) => {
    const canvasRef = useRef(null);
    // Scrollable viewport that contains the canvas; zoom/pan happen inside this frame
    const viewportRef = useRef(null);
    // Backward-compat alias while we transition from old naming
    const containerRef = viewportRef;
    const imageRef = useRef(null);

    const MIN_SCALE = 0.05; // allow true fit in very wide containers
    const MAX_SCALE = 3.0;

    const [canvasState, setCanvasState] = useState({
        scale: 1.0,
        offset: { x: 0, y: 0 },
        selectedDetection: null,
        selectedIds: new Set(),
        isAddingDetection: false,
        dragState: null,
        imageLoaded: false,
        canvasSize: { width: 800, height: 600 },
        lasso: null, // { x, y, w, h, active }
        quickReview: false
    });

    // Load and setup page image
    useEffect(() => {
        if (!pageImageUrl) return;

        const img = new Image();
        img.onload = () => {
            imageRef.current = img;
            fitToContainer(img);
            setCanvasState(prev => ({ ...prev, imageLoaded: true }));
        };
        img.onerror = () => {
            console.error('Failed to load page image:', pageImageUrl);
        };
        img.src = pageImageUrl;
    }, [pageImageUrl]);

    // Recompute canvas sizing on container or window resize
    useEffect(() => {
        const handleResize = () => {
            if (imageRef.current) {
                fitToContainer(imageRef.current);
            }
        };
        window.addEventListener('resize', handleResize);
        let ro;
        if (containerRef.current) {
            ro = new ResizeObserver(() => handleResize());
            ro.observe(containerRef.current);
        }
        return () => {
            window.removeEventListener('resize', handleResize);
            if (ro) ro.disconnect();
        };
    }, []);

    const applyScale = useCallback((img, scale) => {
        const canvas = canvasRef.current;
        if (!canvas || !img) return;

        const clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale));
        const canvasWidth = img.width * clamped;
        const canvasHeight = img.height * clamped;

        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        canvas.style.width = `${canvasWidth}px`;
        canvas.style.height = `${canvasHeight}px`;

        setCanvasState(prev => ({
            ...prev,
            scale: clamped,
            canvasSize: { width: canvasWidth, height: canvasHeight },
            imageSize: { width: img.width, height: img.height }
        }));
        // Do not call renderCanvas here; the useEffect that depends on renderCanvas will handle drawing
    }, []);

    // Zoom keeping the cursor focus stable within the viewport
    const zoomAtViewportPoint = useCallback((deltaScale, clientX, clientY) => {
        const img = imageRef.current;
        const viewport = viewportRef.current;
        const canvas = canvasRef.current;
        if (!img || !viewport || !canvas) return;

        const prevScale = canvasState.scale || 1;
        const nextScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, prevScale * deltaScale));
        if (nextScale === prevScale) return;

        // Compute cursor position relative to the canvas content
        const viewportRect = viewport.getBoundingClientRect();
        const cursorX = clientX - viewportRect.left + viewport.scrollLeft;
        const cursorY = clientY - viewportRect.top + viewport.scrollTop;
        const contentX = cursorX / prevScale;
        const contentY = cursorY / prevScale;

        // Apply new scale (updates canvas size)
        applyScale(img, nextScale);

        // Maintain the same content point under the cursor
        const newScrollLeft = contentX * nextScale - (clientX - viewportRect.left);
        const newScrollTop = contentY * nextScale - (clientY - viewportRect.top);
        requestAnimationFrame(() => {
            viewport.scrollLeft = newScrollLeft;
            viewport.scrollTop = newScrollTop;
        });
        // No direct call to renderCanvas here; canvasState changes from applyScale
        // will trigger the render effect.
    }, [applyScale, canvasState.scale]);

    // Calculate a scale that CONTAINS the image in the container (no scroll by default)
    const fitToContainer = useCallback((img) => {
        const canvas = canvasRef.current;
        const viewport = viewportRef.current;
        if (!canvas || !viewport || !img) return;

        const rect = viewport.getBoundingClientRect();
        const availableW = Math.max(rect.width - 16, 100);
        const availableH = Math.max(rect.height - 16, 140);

        const scaleX = availableW / img.width;
        const scaleY = availableH / img.height;
        const fitScale = Math.min(scaleX, scaleY);

        const bounded = Math.min(MAX_SCALE, Math.max(MIN_SCALE, fitScale));
        applyScale(img, bounded);
        requestAnimationFrame(() => {
            viewport.scrollLeft = 0;
            viewport.scrollTop = 0;
        });
    }, [applyScale]);

    // Zoom utilities (ensure they exist and are used by buttons)
    const handleZoomIn = useCallback(() => {
        if (!imageRef.current || !viewportRef.current) return;
        const vp = viewportRef.current.getBoundingClientRect();
        zoomAtViewportPoint(1.2, vp.left + vp.width / 2, vp.top + vp.height / 2);
    }, [zoomAtViewportPoint]);

    const handleZoomOut = useCallback(() => {
        if (!imageRef.current || !viewportRef.current) return;
        const vp = viewportRef.current.getBoundingClientRect();
        zoomAtViewportPoint(1/1.2, vp.left + vp.width / 2, vp.top + vp.height / 2);
    }, [zoomAtViewportPoint]);

    const handleFit = useCallback(() => {
        if (!imageRef.current) return;
        fitToContainer(imageRef.current);
    }, [fitToContainer]);

    // Fit to width helper (not yet wired to a button; available for future use)
    const handleFitWidth = useCallback(() => {
        const img = imageRef.current; const viewport = viewportRef.current;
        if (!img || !viewport) return;
        const rect = viewport.getBoundingClientRect();
        const scaleX = Math.max(50, rect.width - 16) / img.width;
        const clamped = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scaleX));
        applyScale(img, clamped);
        requestAnimationFrame(() => { viewport.scrollLeft = 0; });
    }, [applyScale]);

    // Wheel zoom (Cmd/Ctrl + wheel) and trackpad pinch-zoom (often sets ctrlKey)
    useEffect(() => {
        const viewport = viewportRef.current;
        if (!viewport) return;
        const onWheel = (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 1.1 : 1/1.1;
                zoomAtViewportPoint(delta, e.clientX, e.clientY);
            }
        };
        viewport.addEventListener('wheel', onWheel, { passive: false });
        return () => viewport.removeEventListener('wheel', onWheel);
    }, [zoomAtViewportPoint]);

    // Space+drag to pan
    useEffect(() => {
        const viewport = viewportRef.current;
        if (!viewport) return;
        let isPanning = false;
        let lastX = 0, lastY = 0;
        const onKeyDown = (e) => { if (e.code === 'Space') viewport.classList.add('panning'); };
        const onKeyUp = (e) => { if (e.code === 'Space') viewport.classList.remove('panning'); };
        const onMouseDown = (e) => {
            if (e.button === 1 || viewport.classList.contains('panning')) {
                isPanning = true; lastX = e.clientX; lastY = e.clientY; e.preventDefault();
            }
        };
        const onMouseMove = (e) => {
            if (!isPanning) return;
            const dx = e.clientX - lastX; const dy = e.clientY - lastY;
            lastX = e.clientX; lastY = e.clientY;
            viewport.scrollLeft -= dx; viewport.scrollTop -= dy;
        };
        const onMouseUp = () => { isPanning = false; };
        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
        viewport.addEventListener('mousedown', onMouseDown);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        return () => {
            window.removeEventListener('keydown', onKeyDown);
            window.removeEventListener('keyup', onKeyUp);
            viewport.removeEventListener('mousedown', onMouseDown);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };
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

        // 2. Draw detection overlays with optional viewport culling
        let visibleRect = null;
        if (onlyInViewport && viewportRef.current) {
            const vp = viewportRef.current;
            const left = vp.scrollLeft;
            const top = vp.scrollTop;
            const right = left + vp.clientWidth;
            const bottom = top + vp.clientHeight;
            const pad = 200; // small buffer to reduce pop-in
            visibleRect = { left: left - pad, top: top - pad, right: right + pad, bottom: bottom + pad };
        }

        detections.forEach(detection => {
            if (visibleRect) {
                const c = pdfToCanvas(detection.pdfCoords);
                const dr = { left: c.x, top: c.y, right: c.x + c.width, bottom: c.y + c.height };
                const intersect = !(dr.left > visibleRect.right || dr.right < visibleRect.left || dr.top > visibleRect.bottom || dr.bottom < visibleRect.top);
                if (!intersect) return;
            }
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
        const isSelected = canvasState.selectedIds.has(detection.detectionId) || canvasState.selectedDetection?.detectionId === detection.detectionId;
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
            { x: x - handleSize / 2, y: y - handleSize / 2 }, // Top-left
            { x: x + width - handleSize / 2, y: y - handleSize / 2 }, // Top-right
            { x: x - handleSize / 2, y: y + height - handleSize / 2 }, // Bottom-left
            { x: x + width - handleSize / 2, y: y + height - handleSize / 2 }, // Bottom-right
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
            // Quick-review mode
            if (canvasState.quickReview) {
                if (event.altKey) {
                    onDetectionStatusUpdate && onDetectionStatusUpdate(clickedDetection.detectionId, 'rejected');
                } else {
                    onDetectionStatusUpdate && onDetectionStatusUpdate(clickedDetection.detectionId, 'accepted');
                }
                return;
            }

            // Shift+click toggles selection
            if (event.shiftKey) {
                setCanvasState(prev => {
                    const nextSet = new Set(prev.selectedIds);
                    if (nextSet.has(clickedDetection.detectionId)) nextSet.delete(clickedDetection.detectionId);
                    else nextSet.add(clickedDetection.detectionId);
                    return { ...prev, selectedIds: nextSet, selectedDetection: clickedDetection };
                });
                onDetectionSelect && onDetectionSelect(clickedDetection);
                return;
            }

            setCanvasState(prev => ({
                ...prev,
                selectedDetection: clickedDetection,
                selectedIds: new Set([clickedDetection.detectionId]),
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
            // Shift+drag lasso to multi-select
            if (event.shiftKey) {
                setCanvasState(prev => ({ ...prev, lasso: { x: clickPoint.x, y: clickPoint.y, w: 0, h: 0, active: true }, selectedIds: new Set() }));
                return;
            }
            // Clear selection
            setCanvasState(prev => ({
                ...prev,
                selectedDetection: null,
                selectedIds: new Set()
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

        // Lasso update
        if (canvasState.lasso?.active) {
            const lx = canvasState.lasso.x;
            const ly = canvasState.lasso.y;
            const w = currentPoint.x - lx;
            const h = currentPoint.y - ly;
            setCanvasState(prev => ({ ...prev, lasso: { ...prev.lasso, w, h } }));
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
        // Finish lasso selection
        if (canvasState.lasso?.active) {
            const { x, y, w, h } = canvasState.lasso;
            const rect = {
                left: Math.min(x, x + w),
                top: Math.min(y, y + h),
                right: Math.max(x, x + w),
                bottom: Math.max(y, y + h)
            };
            const hits = new Set();
            detections.forEach(det => {
                const cc = pdfToCanvas(det.pdfCoords);
                const dr = { left: cc.x, top: cc.y, right: cc.x + cc.width, bottom: cc.y + cc.height };
                const overlap = !(dr.left > rect.right || dr.right < rect.left || dr.top > rect.bottom || dr.bottom < rect.top);
                if (overlap) hits.add(det.detectionId);
            });
            const first = detections.find(d => hits.has(d.detectionId)) || null;
            setCanvasState(prev => ({ ...prev, lasso: null, selectedIds: hits, selectedDetection: first }));
            onDetectionSelect && onDetectionSelect(first);
            return;
        }

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
            fitToContainer(imageRef.current);
        }
    };

    // Schedule renders to batch frequent updates
    const renderScheduled = useRef(false);
    const scheduleRender = useCallback(() => {
        if (renderScheduled.current) return;
        renderScheduled.current = true;
        requestAnimationFrame(() => {
            renderScheduled.current = false;
            renderCanvas();
        });
    }, [renderCanvas]);

    // Re-render when detections or canvas state changes
    useEffect(() => {
        scheduleRender();
    }, [scheduleRender]);

    // Derived helpers
    const getSelectedCanvasRect = () => {
        if (!canvasState.selectedDetection) return null;
        const cc = pdfToCanvas(canvasState.selectedDetection.pdfCoords);
        return { left: cc.x, top: cc.y, width: cc.width, height: cc.height };
    };

    const isDetectionSelected = (det) => canvasState.selectedIds.has(det.detectionId);
    const clearSelection = () => setCanvasState(prev => ({ ...prev, selectedIds: new Set(), selectedDetection: null }));

    // Notify parent on selection changes
    useEffect(() => {
        if (onSelectionChange) {
            try {
                onSelectionChange(Array.from(canvasState.selectedIds));
            } catch (_) {}
        }
    }, [canvasState.selectedIds, onSelectionChange]);

    // Respond to external clear selection tick
    const lastClearTickRef = useRef(null);
    useEffect(() => {
        if (clearSelectionTick !== undefined && clearSelectionTick !== lastClearTickRef.current) {
            lastClearTickRef.current = clearSelectionTick;
            clearSelection();
        }
    }, [clearSelectionTick]);

    const orderedDetections = React.useMemo(() => {
        return [...detections].sort((a, b) => {
            const ca = a.pdfCoords, cb = b.pdfCoords;
            if (!ca || !cb) return 0;
            const ay = ca.top_points, by = cb.top_points;
            if (Math.abs(ay - by) > 2) return ay - by;
            return ca.left_points - cb.left_points;
        });
    }, [detections]);

    // Keyboard shortcuts: A/R/D for selected or multi-selected detections, arrows to navigate
    useEffect(() => {
        const onKeyDown = (e) => {
            // avoid when typing
            const tag = (e.target && e.target.tagName) || '';
            if (tag === 'INPUT' || tag === 'TEXTAREA') return;

            const sel = canvasState.selectedDetection;
            if (e.key === 'a' || e.key === 'A') {
                const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : (sel ? [sel.detectionId] : []);
                if (ids.length > 0 && onDetectionStatusUpdate) {
                    Promise.resolve(onDetectionStatusUpdate(ids, 'accepted')).then(() => {
                        clearSelection();
                    });
                }
            } else if (e.key === 'r' || e.key === 'R') {
                const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : (sel ? [sel.detectionId] : []);
                if (ids.length > 0 && onDetectionStatusUpdate) {
                    Promise.resolve(onDetectionStatusUpdate(ids, 'rejected')).then(() => {
                        clearSelection();
                    });
                }
            } else if (e.key === 'd' || e.key === 'D') {
                const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : (sel ? [sel.detectionId] : []);
                if (ids.length > 0) {
                    const runDeletes = async () => {
                        if (onDetectionDelete) {
                            for (const id of ids) {
                                // eslint-disable-next-line no-await-in-loop
                                await onDetectionDelete(id);
                            }
                        }
                        clearSelection();
                    };
                    runDeletes();
                }
            } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                if (orderedDetections.length === 0) return;
                e.preventDefault();
                let idx = orderedDetections.findIndex(d => d.detectionId === sel?.detectionId);
                idx = (idx + 1 + orderedDetections.length) % orderedDetections.length;
                const next = orderedDetections[idx];
                setCanvasState(prev => ({ ...prev, selectedDetection: next, selectedIds: new Set([next.detectionId]) }));
                onDetectionSelect && onDetectionSelect(next);
                // center selection
                const rect = pdfToCanvas(next.pdfCoords);
                const vp = viewportRef.current; if (vp) {
                    vp.scrollLeft = Math.max(0, rect.x + rect.width / 2 - vp.clientWidth / 2);
                    vp.scrollTop = Math.max(0, rect.y + rect.height / 2 - vp.clientHeight / 2);
                }
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                if (orderedDetections.length === 0) return;
                e.preventDefault();
                let idx = orderedDetections.findIndex(d => d.detectionId === sel?.detectionId);
                idx = (idx - 1 + orderedDetections.length) % orderedDetections.length;
                const prevDet = orderedDetections[idx];
                setCanvasState(prev => ({ ...prev, selectedDetection: prevDet, selectedIds: new Set([prevDet.detectionId]) }));
                onDetectionSelect && onDetectionSelect(prevDet);
                const rect = pdfToCanvas(prevDet.pdfCoords);
                const vp = viewportRef.current; if (vp) {
                    vp.scrollLeft = Math.max(0, rect.x + rect.width / 2 - vp.clientWidth / 2);
                    vp.scrollTop = Math.max(0, rect.y + rect.height / 2 - vp.clientHeight / 2);
                }
            } else if (e.key === 'f' || e.key === 'F') {
                handleFit();
            }
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [canvasState.selectedDetection, canvasState.selectedIds, orderedDetections, onDetectionStatusUpdate, onDetectionDelete, onDetectionSelect, handleFit]);

    return (
        <div className="interactive-detection-canvas" style={{ position: 'relative' }}>
            <div
                ref={viewportRef}
                className="canvas-viewport"
                style={{
                    width: '100%',
                    height: '72vh',
                    overflow: 'auto',
                    border: '1px solid #e9ecef',
                    background: '#fafafa'
                }}
            >
                <div style={{ position: 'relative', width: canvasState.canvasSize.width, height: canvasState.canvasSize.height, margin: '0 auto' }}>
                <canvas
                    ref={canvasRef}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    className="detection-canvas"
                    style={{
                        cursor: canvasState.isAddingDetection ? 'crosshair' : 'default',
                            position: 'absolute',
                            top: 0,
                            left: 0
                        }}
                    />

                    {/* Lasso rectangle overlay */}
                    {canvasState.lasso?.active && (
                        (() => {
                            const lx = canvasState.lasso.x;
                            const ly = canvasState.lasso.y;
                            const w = canvasState.lasso.w;
                            const h = canvasState.lasso.h;
                            const left = Math.min(lx, lx + w);
                            const top = Math.min(ly, ly + h);
                            const width = Math.abs(w);
                            const height = Math.abs(h);
                            return (
                                <div style={{ position: 'absolute', left, top, width, height, border: '1px dashed #0d6efd', background: 'rgba(13,110,253,0.1)', pointerEvents: 'none' }} />
                            );
                        })()
                    )}

                    {/* Contextual action popup near selected detection */}
                    {canvasState.selectedDetection && (
                        (() => {
                            const rect = getSelectedCanvasRect();
                            if (!rect) return null;
                            const popupWidth = 180;
                            const popupLeft = Math.min(Math.max(0, rect.left + rect.width + 8), Math.max(0, canvasState.canvasSize.width - popupWidth - 8));
                            const popupTop = Math.min(Math.max(0, rect.top), Math.max(0, canvasState.canvasSize.height - 120));
                            return (
                                <div
                                    className="detection-popup"
                                    style={{
                                        position: 'absolute',
                                        left: popupLeft,
                                        top: popupTop,
                                        width: popupWidth,
                                        background: 'rgba(255,255,255,0.95)',
                                        border: '1px solid #e9ecef',
                                        borderRadius: 8,
                                        padding: 8,
                                        boxShadow: '0 2px 10px rgba(0,0,0,0.08)'
                                    }}
                                >
                                    <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                                        IoU: {(canvasState.selectedDetection.iouScore * 100).toFixed(1)}% · Conf: {(canvasState.selectedDetection.matchConfidence * 100).toFixed(1)}%
                                    </div>
                                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                        <button className="btn btn-success" onClick={async () => {
                                            const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : [canvasState.selectedDetection.detectionId];
                                            if (onDetectionStatusUpdate) { await onDetectionStatusUpdate(ids, 'accepted'); }
                                            clearSelection();
                                        }}>✓ Accept</button>
                                        <button className="btn btn-warning" onClick={async () => {
                                            const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : [canvasState.selectedDetection.detectionId];
                                            if (onDetectionStatusUpdate) { await onDetectionStatusUpdate(ids, 'rejected'); }
                                            clearSelection();
                                        }}>✗ Reject</button>
                                        <button className="btn btn-secondary" onClick={() => onRequestDetails && onRequestDetails(canvasState.selectedDetection)}>View Details</button>
                                    </div>
                                    <div style={{ marginTop: 6, textAlign: 'right' }}>
                                        <button className="btn btn-danger" onClick={async () => {
                                            const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : [canvasState.selectedDetection.detectionId];
                                            if (onDetectionDelete) {
                                                await onDetectionDelete(ids);
                                            }
                                            clearSelection();
                                        }}>🗑️ Delete</button>
                                    </div>
                                </div>
                            );
                        })()
                    )}
                </div>
                {!canvasState.imageLoaded && (
                    <div className="canvas-loading" style={{ padding: 16, textAlign: 'center' }}>
                        <div className="loading-spinner" />
                        <p>Loading page image...</p>
                    </div>
                )}
            </div>

            {/* Floating bottom toolbar */}
            <div
                className="canvas-controls"
                style={{
                    position: 'absolute',
                    left: '50%',
                    bottom: 12,
                    transform: 'translateX(-50%)',
                    background: 'rgba(255,255,255,0.9)',
                    border: '1px solid #e9ecef',
                    borderRadius: 8,
                    padding: '6px 10px',
                    display: 'flex',
                    gap: 6,
                    alignItems: 'center',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.05)'
                }}
            >
                <button className="btn" onClick={handleZoomOut}>−</button>
                <button className="btn" onClick={handleZoomIn}>+</button>
                <button className="btn btn-secondary" onClick={handleFit}>Fit</button>
                <div className="canvas-info" style={{ marginLeft: 8, fontSize: 12, color: '#555' }}>
                    <span>{(canvasState.scale * 100).toFixed(0)}%</span>
                </div>
                <div style={{ marginLeft: 12, fontSize: 12, color: '#888' }}>Space+Drag to pan</div>
                <div style={{ marginLeft: 6, fontSize: 12, color: '#888' }}>Cmd/Ctrl+Wheel to zoom</div>
                <div style={{ marginLeft: 6, fontSize: 12, color: canvasState.quickReview ? '#0d6efd' : '#888' }}>Quick Review</div>
                <button className={`btn ${canvasState.quickReview ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setCanvasState(prev => ({ ...prev, quickReview: !prev.quickReview }))}>
                    {canvasState.quickReview ? 'On' : 'Off'}
                </button>
                <div style={{ flex: 1 }} />
                <button
                    className={`btn ${canvasState.isAddingDetection ? 'btn-danger' : 'btn-primary'}`}
                    onClick={canvasState.isAddingDetection ? cancelAddMode : startAddMode}
                    disabled={!templateDimensions}
                >
                    {canvasState.isAddingDetection ? '✕ Cancel Add' : '+ Add Detection'}
                </button>
                {canvasState.selectedDetection && (
                    <button
                        className="btn btn-danger"
                        onClick={async () => {
                            const ids = canvasState.selectedIds.size > 0 ? Array.from(canvasState.selectedIds) : [canvasState.selectedDetection.detectionId];
                            if (onDetectionDelete) {
                                await onDetectionDelete(ids);
                            }
                            clearSelection();
                        }}
                    >
                        🗑️ Delete
                    </button>
                )}
            </div>

            {/* Batch selection bar */}
            {canvasState.selectedIds.size > 1 && (
                <div style={{ position: 'absolute', left: 12, bottom: 12, background: 'rgba(255,255,255,0.95)', border: '1px solid #e9ecef', borderRadius: 8, padding: '6px 10px', display: 'flex', gap: 8, alignItems: 'center', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
                    <span style={{ fontSize: 12 }}>{canvasState.selectedIds.size} selected</span>
                     <button className="btn btn-success" onClick={async () => { if (onDetectionStatusUpdate) { await onDetectionStatusUpdate(Array.from(canvasState.selectedIds), 'accepted'); } clearSelection(); }}>✓ Accept</button>
                    <button className="btn btn-warning" onClick={async () => { if (onDetectionStatusUpdate) { await onDetectionStatusUpdate(Array.from(canvasState.selectedIds), 'rejected'); } clearSelection(); }}>✗ Reject</button>
                    <button className="btn btn-secondary" onClick={clearSelection}>Clear</button>
                </div>
            )}
        </div>
    );
};

export default InteractiveDetectionCanvas;