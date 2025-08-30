import React, { useState, useRef, useEffect } from 'react';
import { fabric } from 'fabric';
import {
    CoordinateTransformer,
    CanvasCoordinates,
    PDFCoordinates,
    createPageMetadata,
    getOptimalCanvasDimensions
} from '../utils/coordinateMapping';

const DefineKeyAreasTab = ({
    docInfo,
    allAnnotations,
    pageSummaries,
    onAnnotationsChange,
    onSummaryChange,
    onSaveData,
    pixmapStatus = {},
    onPixmapCheck = () => { }
}) => {
    const [selectedTool, setSelectedTool] = useState(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [drawingPage, setDrawingPage] = useState(null); // Track which page is in drawing mode
    const [canvasRefs, setCanvasRefs] = useState({});
    const [fabricCanvases, setFabricCanvases] = useState({});
    const [editingSummary, setEditingSummary] = useState({});
    const [selectedAnnotation, setSelectedAnnotation] = useState(null); // Track selected annotation
    const [canvasDimensions, setCanvasDimensions] = useState({}); // Track canvas dimensions for coordinate mapping
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false); // Collapse/expand sidebar
    const viewportRefs = useRef({}); // Per-page scrollable viewport wrappers
    const [pageZoom, setPageZoom] = useState({}); // Per-page zoom display

    const MIN_ZOOM = 0.05;
    const MAX_ZOOM = 3.0;

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

                        console.log(`🖼️  [DefineKeyAreas] Image loaded for page ${pageNumber}: ${img.width}x${img.height}`);

                        // Use new coordinate system for canvas sizing
                        let scale;
                        if (docInfo?.pageMetadata?.[pageNumber]) {
                            const pageMetadata = createPageMetadata(docInfo.pageMetadata[pageNumber]);
                            const transformer = new CoordinateTransformer(pageMetadata);
                            const canvasDims = transformer.getCanvasDimensionsForAspectRatio(1200, 900);

                            console.log(`📐 [DefineKeyAreas] NEW coordinate system for page ${pageNumber}:`);
                            console.log(`    PDF: ${pageMetadata.pdfWidthPoints}x${pageMetadata.pdfHeightPoints} points`);
                            console.log(`    Image: ${pageMetadata.imageWidthPixels}x${pageMetadata.imageHeightPixels} pixels @ ${pageMetadata.imageDpi} DPI`);
                            console.log(`    Canvas: ${canvasDims.width.toFixed(1)}x${canvasDims.height.toFixed(1)} pixels`);

                            scale = Math.min(canvasDims.width / img.width, canvasDims.height / img.height);

                            img.scale(scale);
                            canvas.setWidth(canvasDims.width);
                            canvas.setHeight(canvasDims.height);

                            setCanvasDimensions(prev => ({
                                ...prev,
                                [pageNumber]: {
                                    width: canvasDims.width,
                                    height: canvasDims.height,
                                    scale: scale,
                                    pageMetadata: pageMetadata,
                                    transformer: transformer
                                }
                            }));

                            console.log(`✅ [DefineKeyAreas] Canvas ${pageNumber} sized using NEW system: ${canvasDims.width.toFixed(1)}x${canvasDims.height.toFixed(1)} (scale: ${scale.toFixed(4)})`);
                        } else {
                            // Fallback to old system if metadata not available
                            console.warn(`⚠️  [DefineKeyAreas] No page metadata for page ${pageNumber}, using fallback sizing`);
                            const imageAspectRatio = img.width / img.height;
                            const maxCanvasWidth = 1200;
                            const maxCanvasHeight = 900;

                            let actualCanvasWidth, actualCanvasHeight;

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
                                    height: actualCanvasHeight,
                                    scale: scale
                                }
                            }));

                            console.log(`📊 [DefineKeyAreas] Canvas ${pageNumber} sized using FALLBACK: ${actualCanvasWidth.toFixed(1)}x${actualCanvasHeight.toFixed(1)} (scale: ${scale.toFixed(4)})`);
                        }

                        canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                            scaleX: scale,
                            scaleY: scale
                        });

                        // Fit canvas content to viewport after background is ready
                        requestAnimationFrame(() => fitToViewport(pageNumber));

                        console.log(`✅ [DefineKeyAreas] Background loaded for page ${pageNumber}`);
                    }, { crossOrigin: 'anonymous' });
                }
            }
        });
    }, [pixmapStatus, fabricCanvases, docInfo.docId, docInfo?.pageMetadata]);

    const annotationTools = [
        { id: 'TitleBlock', label: 'Title Block', color: '#FF6B6B', icon: '📋' },
        { id: 'DrawingArea', label: 'Drawing Area', color: '#4ECDC4', icon: '📐' },
        { id: 'NotesArea', label: 'Notes Area', color: '#45B7D1', icon: '📝' },
        { id: 'SymbolLegend', label: 'Symbol Legend', color: '#96CEB4', icon: '🔣' }
    ];

    useEffect(() => {
        let attempts = 0;
        const maxAttempts = 10; // Increased from 5

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
                setTimeout(initializeAllCanvases, 200); // Reduced delay for faster retry
            }
        };

        // Start initialization after a shorter delay
        const timer = setTimeout(initializeAllCanvases, 100); // Reduced from 300ms

        return () => {
            clearTimeout(timer);
            // Cleanup canvases
            Object.values(fabricCanvases).forEach(canvas => {
                if (canvas) {
                    if (canvas.__zoomPanCleanup) {
                        try { canvas.__zoomPanCleanup(); } catch (_) {}
                    }
                    canvas.dispose();
                }
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

        // Use much larger canvas dimensions for better visibility
        const canvas = new fabric.Canvas(canvasElement, {
            selection: true,
            preserveObjectStacking: true,
            width: 1200,  // Increased from 800
            height: 900   // Increased from 600
        });

        // Store canvas in state immediately
        setFabricCanvases(prev => {
            const newCanvases = { ...prev, [pageNumber]: canvas };
            console.log('Updated canvases:', Object.keys(newCanvases));
            return newCanvases;
        });

        // Setup basic canvas interactions IMMEDIATELY after creation
        setupCanvasInteractions(canvas, pageNumber);

        // Setup zoom/pan interactions using Fabric transforms
        const viewportEl = viewportRefs.current[pageNumber];
        if (viewportEl) {
            setupZoomPan(canvas, pageNumber, viewportEl);
        }

        // Check if pixmap is ready before loading background image
        const pageStatus = pixmapStatus[pageNumber];
        if (pageStatus !== 'ready') {
            console.log(`Page ${pageNumber} pixmap not ready yet (status: ${pageStatus}), canvas ready for annotations`);
            return;
        }

        // Load background image - try legacy format first, then high-res pixmap
        const legacyImageUrl = `/data/processed/${docInfo.docId}/page_${pageNumber}.png`;

        fabric.Image.fromURL(legacyImageUrl, (img) => {
            if (!canvas || canvas._disposed) return;

            console.log(`🖼️  [DefineKeyAreas] Initializing canvas ${pageNumber} - Image: ${img.width}x${img.height}`);

            // Use new coordinate system for canvas sizing
            let scale;
            if (docInfo?.pageMetadata?.[pageNumber]) {
                const pageMetadata = createPageMetadata(docInfo.pageMetadata[pageNumber]);
                const transformer = new CoordinateTransformer(pageMetadata);
                const canvasDims = transformer.getCanvasDimensionsForAspectRatio(1200, 900);

                console.log(`📐 [DefineKeyAreas] NEW coordinate system for canvas ${pageNumber}:`);
                console.log(`    PDF: ${pageMetadata.pdfWidthPoints}x${pageMetadata.pdfHeightPoints} points`);
                console.log(`    Image: ${pageMetadata.imageWidthPixels}x${pageMetadata.imageHeightPixels} pixels @ ${pageMetadata.imageDpi} DPI`);
                console.log(`    Canvas: ${canvasDims.width.toFixed(1)}x${canvasDims.height.toFixed(1)} pixels`);

                scale = Math.min(canvasDims.width / img.width, canvasDims.height / img.height);

                // Scale the image to match canvas
                img.scale(scale);

                // Set canvas to exact calculated dimensions
                canvas.setWidth(canvasDims.width);
                canvas.setHeight(canvasDims.height);

                // Store enhanced canvas dimensions with coordinate transformer
                setCanvasDimensions(prev => ({
                    ...prev,
                    [pageNumber]: {
                        width: canvasDims.width,
                        height: canvasDims.height,
                        scale: scale,
                        pageMetadata: pageMetadata,
                        transformer: transformer
                    }
                }));

                console.log(`✅ [DefineKeyAreas] Canvas ${pageNumber} initialized with NEW system: ${canvasDims.width.toFixed(1)}x${canvasDims.height.toFixed(1)} (scale: ${scale.toFixed(4)})`);
            } else {
                // Fallback to old system if metadata not available
                console.warn(`⚠️  [DefineKeyAreas] No page metadata for canvas ${pageNumber}, using fallback sizing`);
                const imageAspectRatio = img.width / img.height;
                const maxCanvasWidth = 1200;
                const maxCanvasHeight = 900;

                let actualCanvasWidth, actualCanvasHeight;

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
                        height: actualCanvasHeight,
                        scale: scale
                    }
                }));

                console.log(`📊 [DefineKeyAreas] Canvas ${pageNumber} initialized with FALLBACK: ${actualCanvasWidth.toFixed(1)}x${actualCanvasHeight.toFixed(1)} (scale: ${scale.toFixed(4)})`);
            }

            canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                scaleX: scale,
                scaleY: scale
            });

            // Fit canvas content to viewport after background is ready
            requestAnimationFrame(() => fitToViewport(pageNumber));
        }, (error) => {
            console.log(`Failed to load legacy image for page ${pageNumber}, trying high-res pixmap`);

            // Try high-res pixmap format
            const pixmapImageUrl = `/data/processed/${docInfo.docId}/page_${pageNumber}/page_${pageNumber}_pixmap.png`;

            fabric.Image.fromURL(pixmapImageUrl, (img) => {
                if (!canvas || canvas._disposed) return;

                console.log(`🖼️  [DefineKeyAreas] High-res pixmap loaded for canvas ${pageNumber}: ${img.width}x${img.height}`);

                // Use new coordinate system for high-res pixmap sizing
                let scale;
                if (docInfo?.pageMetadata?.[pageNumber]) {
                    const pageMetadata = createPageMetadata(docInfo.pageMetadata[pageNumber]);
                    const transformer = new CoordinateTransformer(pageMetadata);
                    const canvasDims = transformer.getCanvasDimensionsForAspectRatio(1200, 900);

                    console.log(`📐 [DefineKeyAreas] High-res coordinate system for canvas ${pageNumber}:`);
                    console.log(`    PDF: ${pageMetadata.pdfWidthPoints}x${pageMetadata.pdfHeightPoints} points`);
                    console.log(`    Image: ${pageMetadata.imageWidthPixels}x${pageMetadata.imageHeightPixels} pixels @ ${pageMetadata.imageDpi} DPI`);
                    console.log(`    Canvas: ${canvasDims.width.toFixed(1)}x${canvasDims.height.toFixed(1)} pixels`);

                    scale = Math.min(canvasDims.width / img.width, canvasDims.height / img.height);

                    img.scale(scale);
                    canvas.setWidth(canvasDims.width);
                    canvas.setHeight(canvasDims.height);

                    setCanvasDimensions(prev => ({
                        ...prev,
                        [pageNumber]: {
                            width: canvasDims.width,
                            height: canvasDims.height,
                            scale: scale,
                            pageMetadata: pageMetadata,
                            transformer: transformer
                        }
                    }));

                    console.log(`✅ [DefineKeyAreas] High-res canvas ${pageNumber} sized with NEW system: ${canvasDims.width.toFixed(1)}x${canvasDims.height.toFixed(1)} (scale: ${scale.toFixed(4)})`);
                } else {
                    // Fallback to old system
                    console.warn(`⚠️  [DefineKeyAreas] No metadata for high-res canvas ${pageNumber}, using fallback`);
                    const imageAspectRatio = img.width / img.height;
                    const maxCanvasWidth = 1200;
                    const maxCanvasHeight = 900;

                    let actualCanvasWidth, actualCanvasHeight;

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
                            height: actualCanvasHeight,
                            scale: scale
                        }
                    }));

                    console.log(`📊 [DefineKeyAreas] High-res canvas ${pageNumber} sized with FALLBACK: ${actualCanvasWidth.toFixed(1)}x${actualCanvasHeight.toFixed(1)} (scale: ${scale.toFixed(4)})`);
                }

                canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                    scaleX: scale,
                    scaleY: scale
                });

                // Fit canvas content to viewport after background is ready
                requestAnimationFrame(() => fitToViewport(pageNumber));
            }, (pixmapError) => {
                console.error(`Failed to load both legacy and high-res images for page ${pageNumber}:`, error, pixmapError);

                // Even without background image, store canvas dimensions for annotations to work
                setCanvasDimensions(prev => ({
                    ...prev,
                    [pageNumber]: {
                        width: 1200,
                        height: 900,
                        scale: 1
                    }
                }));
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

        console.log(`Canvas ${pageNumber} initialized and interactions set up`);
    };

    const setupZoomPan = (canvas, pageNumber, viewportEl) => {
        if (!canvas || !viewportEl) return;

        let isPanning = false;
        let lastX = 0, lastY = 0;

        const onKeyDown = (e) => { if (e.code === 'Space') viewportEl.classList.add('panning'); };
        const onKeyUp = (e) => { if (e.code === 'Space') viewportEl.classList.remove('panning'); };

        const onMouseDown = (e) => {
            if (e.button === 1 || viewportEl.classList.contains('panning')) {
                isPanning = true; lastX = e.clientX; lastY = e.clientY; e.preventDefault();
            }
        };

        const onMouseMove = (e) => {
            if (!isPanning) return;
            const dx = e.clientX - lastX; const dy = e.clientY - lastY;
            lastX = e.clientX; lastY = e.clientY;
            canvas.relativePan(new fabric.Point(dx, dy));
        };

        const onMouseUp = () => { isPanning = false; };

        const onWheel = (e) => {
            if (!(e.ctrlKey || e.metaKey)) return; // only intercept pinch/Cmd zoom
            e.preventDefault();
            const rect = viewportEl.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            const delta = e.deltaY < 0 ? 1.1 : 1 / 1.1;
            const prevZoom = canvas.getZoom();
            const nextZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, prevZoom * delta));
            const point = new fabric.Point(mouseX, mouseY);
            canvas.zoomToPoint(point, nextZoom);
            setPageZoom((prev) => ({ ...prev, [pageNumber]: nextZoom }));
        };

        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
        viewportEl.addEventListener('mousedown', onMouseDown);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        viewportEl.addEventListener('wheel', onWheel, { passive: false });

        // Cleanup when canvas is disposed
        const cleanup = () => {
            window.removeEventListener('keydown', onKeyDown);
            window.removeEventListener('keyup', onKeyUp);
            viewportEl.removeEventListener('mousedown', onMouseDown);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
            viewportEl.removeEventListener('wheel', onWheel);
        };
        // Attach to canvas for disposal and keep a direct handle
        canvas.on('removed', cleanup);
        canvas.__zoomPanCleanup = cleanup;
    };

    const fitToViewport = (pageNumber) => {
        const canvas = fabricCanvases[pageNumber];
        const viewportEl = viewportRefs.current[pageNumber];
        if (!canvas || !viewportEl) return;

        const baseW = canvas.getWidth();
        const baseH = canvas.getHeight();
        const rect = viewportEl.getBoundingClientRect();
        const availableW = Math.max(rect.width - 16, 100);
        const availableH = Math.max(rect.height - 16, 140);
        const scaleX = availableW / baseW;
        const scaleY = availableH / baseH;
        const fitZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.min(scaleX, scaleY)));

        canvas.setZoom(fitZoom);
        // Reset pan to top-left
        const vt = canvas.viewportTransform;
        if (vt) { vt[4] = 0; vt[5] = 0; }
        canvas.requestRenderAll();
        setPageZoom((prev) => ({ ...prev, [pageNumber]: fitZoom }));
    };

    const zoomIn = (pageNumber) => {
        const canvas = fabricCanvases[pageNumber];
        const viewportEl = viewportRefs.current[pageNumber];
        if (!canvas || !viewportEl) return;
        const rect = viewportEl.getBoundingClientRect();
        const center = new fabric.Point(rect.width / 2, rect.height / 2);
        const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, (canvas.getZoom() || 1) * 1.2));
        canvas.zoomToPoint(center, next);
        setPageZoom((prev) => ({ ...prev, [pageNumber]: next }));
    };

    const zoomOut = (pageNumber) => {
        const canvas = fabricCanvases[pageNumber];
        const viewportEl = viewportRefs.current[pageNumber];
        if (!canvas || !viewportEl) return;
        const rect = viewportEl.getBoundingClientRect();
        const center = new fabric.Point(rect.width / 2, rect.height / 2);
        const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, (canvas.getZoom() || 1) / 1.2));
        canvas.zoomToPoint(center, next);
        setPageZoom((prev) => ({ ...prev, [pageNumber]: next }));
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

        // Ensure canvas exists before starting drawing
        const canvas = fabricCanvases[pageNumber];
        if (!canvas) {
            console.log(`Canvas not ready for page ${pageNumber}, attempting to initialize`);

            // Try to initialize the canvas if it doesn't exist
            const canvasElement = document.getElementById(`canvas-${pageNumber}`);
            if (canvasElement) {
                initializeCanvas(pageNumber);

                // Wait a bit for initialization then try again
                setTimeout(() => {
                    const retryCanvas = fabricCanvases[pageNumber];
                    if (retryCanvas) {
                        console.log(`Canvas initialized successfully for page ${pageNumber}, starting drawing`);
                        setSelectedTool(toolId);
                        setIsDrawing(true);
                        setDrawingPage(pageNumber);

                        retryCanvas.discardActiveObject();
                        retryCanvas.renderAll();
                    } else {
                        console.error(`Failed to initialize canvas for page ${pageNumber}`);
                        alert(`Canvas not ready for page ${pageNumber}. Please try again in a moment.`);
                    }
                }, 300);

                return;
            } else {
                console.error(`Canvas element not found for page ${pageNumber}`);
                alert(`Canvas element not found for page ${pageNumber}. Please refresh the page.`);
                return;
            }
        }

        // Canvas exists, proceed with drawing
        setSelectedTool(toolId);
        setIsDrawing(true);
        setDrawingPage(pageNumber);

        // Focus on the specific page canvas
        canvas.discardActiveObject();
        canvas.renderAll();
        console.log(`Canvas found and focused for page ${pageNumber}, drawing mode enabled`);
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

            console.log('🚀 [DefineKeyAreas] ENHANCED - Generating clippings with NEW coordinate system');
            console.log('📊 [DefineKeyAreas] Annotations to process:', allAnnotationsFlat);
            console.log('📐 [DefineKeyAreas] Canvas dimensions:', canvasDimensions);

            // Enhanced debugging with coordinate transformation analysis
            allAnnotationsFlat.forEach((annotation, index) => {
                const pageDims = canvasDimensions[annotation.pageNumber];
                console.log(`\n🔍 [DefineKeyAreas] ANNOTATION ${index + 1} ANALYSIS (${annotation.tag} on page ${annotation.pageNumber}):`);
                console.log(`  📍 Canvas Coords: (${annotation.left}, ${annotation.top}) ${annotation.width}x${annotation.height}`);
                console.log(`  📐 Canvas Dims: ${pageDims?.width}x${pageDims?.height} (scale: ${pageDims?.scale})`);

                // Calculate PDF coordinates using new system if available
                if (pageDims?.transformer) {
                    try {
                        const canvasCoords = new CanvasCoordinates(
                            annotation.left, annotation.top, annotation.width, annotation.height,
                            pageDims.width, pageDims.height
                        );

                        const pdfCoords = pageDims.transformer.canvasToPdf(canvasCoords);

                        console.log(`  📄 PDF Coords (NEW SYSTEM): (${pdfCoords.left.toFixed(2)}, ${pdfCoords.top.toFixed(2)}) ${pdfCoords.width.toFixed(2)}x${pdfCoords.height.toFixed(2)} points`);
                        console.log(`  🎯 Page Metadata: ${pageDims.pageMetadata.pdfWidthPoints}x${pageDims.pageMetadata.pdfHeightPoints} points @ ${pageDims.pageMetadata.imageDpi} DPI`);

                        // Store PDF coordinates for backend
                        annotation.pdfCoordinates = pdfCoords.toDict();

                    } catch (error) {
                        console.error(`  ❌ PDF coordinate calculation failed:`, error);
                    }
                } else {
                    console.warn(`  ⚠️  No coordinate transformer available for page ${annotation.pageNumber}`);
                }

                // Original canvas verification
                const canvasElement = document.getElementById(`canvas-${annotation.pageNumber}`);
                if (canvasElement) {
                    console.log(`  🖼️  Canvas Element: ${canvasElement.width}x${canvasElement.height} (DOM)`);
                    console.log(`  📏 Canvas Style: ${canvasElement.style.width} x ${canvasElement.style.height}`);

                    const fabricCanvas = fabricCanvases[annotation.pageNumber];
                    if (fabricCanvas) {
                        console.log(`  🎨 Fabric Canvas: ${fabricCanvas.width}x${fabricCanvas.height}`);
                        console.log(`  🖼️  Background:`, fabricCanvas.backgroundImage ?
                            `${fabricCanvas.backgroundImage.width}x${fabricCanvas.backgroundImage.height} (scale: ${fabricCanvas.backgroundImage.scaleX}x${fabricCanvas.backgroundImage.scaleY})` :
                            'None');

                        const objects = fabricCanvas.getObjects();
                        console.log(`  📦 Canvas Objects (${objects.length}):`);
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
        <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-header">
                <button onClick={generateHighResClippings} className="generate-button">
                    Move onto Symbol Identification
                </button>
                <button
                    className="sidebar-toggle"
                    title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                    onClick={() => setSidebarCollapsed(v => !v)}
                >
                    {sidebarCollapsed ? '➡️' : '⬅️'}
                </button>
            </div>

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

            {/* Footer kept for spacing when list is short */}
            <div className="generate-section" />
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
                <div className="page-header-left">
                    <h3>Page {pageNumber}</h3>
                    {renderPageStatus(pageNumber)}
                </div>
                <div className="page-header-actions">
                    <span className="label">Add key area:</span>
                    <button
                        className={`add-button ${selectedTool === 'TitleBlock' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                        onClick={() => startDrawing('TitleBlock', pageNumber)}
                        title="Title Block"
                    >
                        {selectedTool === 'TitleBlock' && isDrawing && drawingPage === pageNumber ? '📋 Click & Drag' : '📋 Title Block'}
                    </button>
                    <button
                        className={`add-button ${selectedTool === 'DrawingArea' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                        onClick={() => startDrawing('DrawingArea', pageNumber)}
                        title="Drawing Area"
                    >
                        {selectedTool === 'DrawingArea' && isDrawing && drawingPage === pageNumber ? '📐 Click & Drag' : '📐 Drawing Area'}
                    </button>
                    <button
                        className={`add-button ${selectedTool === 'NotesArea' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                        onClick={() => startDrawing('NotesArea', pageNumber)}
                        title="Notes Area"
                    >
                        {selectedTool === 'NotesArea' && isDrawing && drawingPage === pageNumber ? '📝 Click & Drag' : '📝 Notes Area'}
                    </button>
                    <button
                        className={`add-button ${selectedTool === 'SymbolLegend' && isDrawing && drawingPage === pageNumber ? 'active' : ''}`}
                        onClick={() => startDrawing('SymbolLegend', pageNumber)}
                        title="Symbol Legend"
                    >
                        {selectedTool === 'SymbolLegend' && isDrawing && drawingPage === pageNumber ? '🔣 Click & Drag' : '🔣 Symbol Legend'}
                    </button>
                </div>
            </div>

            <div className="page-layout">
                <div className="page-canvas-container" style={{ position: 'relative' }}>
                    <div
                        ref={(el) => { viewportRefs.current[pageNumber] = el; }}
                        className="canvas-viewport"
                        style={{
                            width: '100%',
                            height: '72vh',
                            overflow: 'hidden',
                            border: '1px solid #e9ecef',
                            background: '#fafafa',
                            position: 'relative'
                        }}
                    >
                        <canvas
                            id={`canvas-${pageNumber}`}
                            className="page-canvas"
                            data-page={pageNumber}
                            style={{ display: 'block', margin: '0 auto' }}
                        />
                    </div>

                    {/* Floating bottom toolbar for zoom/pan controls */}
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
                        <button className="btn" onClick={() => zoomOut(pageNumber)}>−</button>
                        <button className="btn" onClick={() => zoomIn(pageNumber)}>+</button>
                        <button className="btn btn-secondary" onClick={() => fitToViewport(pageNumber)}>Fit</button>
                        <div className="canvas-info" style={{ marginLeft: 8, fontSize: 12, color: '#555' }}>
                            <span>{Math.round(((pageZoom[pageNumber] || 1) * 100))}%</span>
                        </div>
                        <div style={{ marginLeft: 12, fontSize: 12, color: '#888' }}>Space+Drag to pan</div>
                        <div style={{ marginLeft: 6, fontSize: 12, color: '#888' }}>Cmd/Ctrl+Wheel to zoom</div>
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