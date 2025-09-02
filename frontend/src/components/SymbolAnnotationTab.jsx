import React, { useState, useRef, useEffect } from 'react';
import { fabric } from 'fabric';
import {
    ClippingCoordinateTransformer,
    CanvasCoordinates,
    PDFCoordinates,
    createPageMetadata,
    HIGH_RES_DPI
} from '../utils/coordinateMapping';

const SymbolAnnotationTab = ({
    docInfo,
    allAnnotations,
    projectData,
    onProjectDataChange,
    onSaveData,
    pixmapStatus = {}
}) => {
    const [symbolData, setSymbolData] = useState(projectData.symbols || {});

    // Debug logging for symbol data changes (reduced)
    useEffect(() => {
        const totalSymbols = Object.values(symbolData).reduce((total, legendSymbols) =>
            total + Object.keys(legendSymbols).length, 0
        );
        if (totalSymbols > 0) {
            console.log(`🔍 TOTAL SYMBOLS: ${totalSymbols}`, Object.keys(symbolData).map(legendId =>
                `${legendId}: ${Object.keys(symbolData[legendId]).length}`
            ));
        }
    }, [symbolData]);
    const [loadingClippings, setLoadingClippings] = useState(false);
    const [clippingImages, setClippingImages] = useState({});
    const [fabricCanvases, setFabricCanvases] = useState({});
    const [selectedSymbol, setSelectedSymbol] = useState(null);
    const [editingSymbol, setEditingSymbol] = useState(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [drawingLegend, setDrawingLegend] = useState(null);
    const [expandedLegends, setExpandedLegends] = useState({}); // control per-legend expansion

    // Use refs to store current drawing state for event handlers (similar to DefineKeyAreasTab)
    const drawingStateRef = useRef({ isDrawing: false, drawingLegend: null });

    // Load Symbol Legend clippings when component mounts or annotations change
    useEffect(() => {
        console.log(`🔄 SymbolAnnotationTab effect triggered - docInfo: ${!!docInfo}, allAnnotations: ${!!allAnnotations}`);
        if (docInfo && allAnnotations) {
            loadSymbolLegendClippings();
        }
    }, [docInfo?.docId, Object.keys(allAnnotations || {}).length]); // Fixed dependencies to prevent infinite loop

    // Update project data when symbol data changes
    useEffect(() => {
        onProjectDataChange(prev => ({
            ...prev,
            symbols: symbolData
        }));
    }, [symbolData, onProjectDataChange]);

    // Update ref whenever drawing state changes
    useEffect(() => {
        drawingStateRef.current = { isDrawing, drawingLegend };
        console.log(`🎯 Drawing state updated: isDrawing=${isDrawing}, drawingLegend=${drawingLegend}`);
    }, [isDrawing, drawingLegend]);

    // Cleanup effect for canvas disposal
    useEffect(() => {
        return () => {
            // Cleanup all fabric canvases and observers when component unmounts
            Object.values(fabricCanvases).forEach(canvas => {
                if (canvas.resizeObserver) {
                    canvas.resizeObserver.disconnect();
                }
                // Remove any raw DOM listeners we attached for debugging
                if (canvas._symbolDomDownListener && canvas.upperCanvasEl) {
                    try {
                        canvas.upperCanvasEl.removeEventListener('mousedown', canvas._symbolDomDownListener);
                    } catch (e) {
                        // noop
                    }
                }
                canvas.dispose();
            });
        };
    }, []);

    const loadSymbolLegendClippings = async () => {
        if (!docInfo || !allAnnotations) return;

        setLoadingClippings(true);

        try {
            // Find all Symbol Legend annotations across all pages
            const symbolLegendAnnotations = [];
            Object.entries(allAnnotations).forEach(([pageNumber, pageAnnotations]) => {
                pageAnnotations.forEach(annotation => {
                    if (annotation.tag === 'SymbolLegend') {
                        symbolLegendAnnotations.push({
                            ...annotation,
                            pageNumber: parseInt(pageNumber)
                        });
                    }
                });
            });

            console.log('Found Symbol Legend annotations:', symbolLegendAnnotations);

            // Load clipping images for each Symbol Legend
            const newClippingImages = {};
            for (const annotation of symbolLegendAnnotations) {
                const clippingUrl = `/data/processed/${docInfo.docId}/clippings/page${annotation.pageNumber}/SymbolLegend_${getSequentialIndex(annotation, symbolLegendAnnotations)}_clipping.png`;

                try {
                    // Check if clipping exists
                    const response = await fetch(clippingUrl, { method: 'HEAD' });
                    if (response.ok) {
                        newClippingImages[annotation.id] = {
                            url: clippingUrl,
                            annotation: annotation,
                            loaded: false
                        };
                    }
                } catch (error) {
                    console.log(`Clipping not found for annotation ${annotation.id}:`, error);
                }
            }

            setClippingImages(newClippingImages);
            // Expand only the first legend by default to keep content above the fold
            const legendIds = Object.keys(newClippingImages);
            if (legendIds.length > 0) {
                setExpandedLegends({ [legendIds[0]]: true });
            }
            console.log('Loaded clipping images:', Object.keys(newClippingImages).length);

        } catch (error) {
            console.error('Error loading Symbol Legend clippings:', error);
        } finally {
            setLoadingClippings(false);
        }
    };

    const getSequentialIndex = (targetAnnotation, allAnnotations) => {
        // Find the sequential index of this annotation among all Symbol Legend annotations on the same page
        const pageAnnotations = allAnnotations.filter(ann =>
            ann.pageNumber === targetAnnotation.pageNumber && ann.tag === 'SymbolLegend'
        );
        pageAnnotations.sort((a, b) => a.id.localeCompare(b.id)); // Sort for consistent ordering
        return pageAnnotations.findIndex(ann => ann.id === targetAnnotation.id) + 1;
    };

    const initializeCanvas = (legendId, imageElement) => {
        const canvasId = `symbol-canvas-${legendId}`;
        const canvasElement = document.getElementById(canvasId);

        if (!canvasElement || fabricCanvases[legendId]) {
            return;
        }

        console.log(`Initializing symbol canvas for legend ${legendId}`);

        // Get the displayed image dimensions (not natural dimensions)
        const displayedWidth = imageElement.clientWidth;
        const displayedHeight = imageElement.clientHeight;

        console.log(`Image natural size: ${imageElement.naturalWidth}x${imageElement.naturalHeight}`);
        console.log(`Image displayed size: ${displayedWidth}x${displayedHeight}`);

        // Create canvas with dimensions matching the displayed image size
        const canvas = new fabric.Canvas(canvasElement, {
            selection: true,
            preserveObjectStacking: true
        });

        // Explicitly set internal canvas dimensions
        canvas.setWidth(displayedWidth);
        canvas.setHeight(displayedHeight);

        // Ensure the Fabric wrapper and upper canvas are positioned above the image
        if (canvas.wrapperEl) {
            const wrapper = canvas.wrapperEl;
            wrapper.style.position = 'absolute';
            wrapper.style.top = '0px';
            wrapper.style.left = '0px';
            wrapper.style.width = displayedWidth + 'px';
            wrapper.style.height = displayedHeight + 'px';
            wrapper.style.zIndex = '11';
        }

        // Lower canvas (the element we provided) should not intercept events
        canvasElement.style.position = 'absolute';
        canvasElement.style.top = '0px';
        canvasElement.style.left = '0px';
        canvasElement.style.width = displayedWidth + 'px';
        canvasElement.style.height = displayedHeight + 'px';
        canvasElement.style.pointerEvents = 'none';
        canvasElement.style.zIndex = '10';

        // Upper canvas receives pointer events
        if (canvas.upperCanvasEl) {
            const upper = canvas.upperCanvasEl;
            upper.style.position = 'absolute';
            upper.style.top = '0px';
            upper.style.left = '0px';
            upper.style.width = displayedWidth + 'px';
            upper.style.height = displayedHeight + 'px';
            upper.style.pointerEvents = 'auto';
            upper.style.zIndex = '12';
        }

        // Debug current layering
        console.log('[SymbolAnnotation] Canvas layering check', {
            legendId,
            wrapper: !!canvas.wrapperEl,
            lowerCanvas: {
                width: canvasElement.style.width,
                height: canvasElement.style.height,
                zIndex: canvasElement.style.zIndex,
                pointerEvents: canvasElement.style.pointerEvents
            },
            upperCanvas: canvas.upperCanvasEl ? {
                width: canvas.upperCanvasEl.style.width,
                height: canvas.upperCanvasEl.style.height,
                zIndex: canvas.upperCanvasEl.style.zIndex,
                pointerEvents: canvas.upperCanvasEl.style.pointerEvents
            } : null
        });

        // Calculate scale factor between natural and displayed size
        const scaleX = displayedWidth / imageElement.naturalWidth;
        const scaleY = displayedHeight / imageElement.naturalHeight;

        console.log(`Scale factors: ${scaleX}x${scaleY}`);

        // Do NOT set a canvas background image; we keep the <img> visible under a transparent canvas to avoid duplicate visuals
        console.log(`Canvas initialized: ${displayedWidth}x${displayedHeight} (transparent overlay, no background)`);

        setupCanvasInteractions(canvas, legendId);

        setFabricCanvases(prev => ({
            ...prev,
            [legendId]: canvas
        }));

        // Load existing symbols for this legend
        loadSymbolsOnCanvas(canvas, legendId);

        // Add resize observer to keep canvas aligned with image
        const resizeObserver = new ResizeObserver(() => {
            const newW = imageElement.clientWidth;
            const newH = imageElement.clientHeight;
            if (newW && newH && (newW !== canvas.width || newH !== canvas.height)) {
                const prevW = canvas.width || 1;
                const prevH = canvas.height || 1;
                const scaleX = newW / prevW;
                const scaleY = newH / prevH;

                // Resize the fabric canvases
                canvas.setWidth(newW);
                canvas.setHeight(newH);
                canvasElement.style.width = newW + 'px';
                canvasElement.style.height = newH + 'px';
                if (canvas.upperCanvasEl) {
                    canvas.upperCanvasEl.style.width = newW + 'px';
                    canvas.upperCanvasEl.style.height = newH + 'px';
                }
                if (canvas.wrapperEl) {
                    canvas.wrapperEl.style.width = newW + 'px';
                    canvas.wrapperEl.style.height = newH + 'px';
                }

                // Proportionally rescale and reposition existing objects to prevent visual shifts
                canvas.getObjects().forEach(obj => {
                    if (!obj) return;
                    // Compute absolute size before scaling
                    const absW = (typeof obj.getScaledWidth === 'function') ? obj.getScaledWidth() : (obj.width * (obj.scaleX || 1));
                    const absH = (typeof obj.getScaledHeight === 'function') ? obj.getScaledHeight() : (obj.height * (obj.scaleY || 1));

                    obj.set({
                        left: (obj.left || 0) * scaleX,
                        top: (obj.top || 0) * scaleY,
                        scaleX: 1,
                        scaleY: 1,
                        width: absW * scaleX,
                        height: absH * scaleY
                    });
                    obj.setCoords();
                });

                // Sync React state with rescaled objects so saved coordinates match what the user sees
                updateSymbolsFromCanvas(canvas, legendId);

                canvas.requestRenderAll();

                console.log('[SymbolAnnotation] Canvas resized with object rescale', {
                    legendId,
                    prev: { w: prevW, h: prevH },
                    next: { w: newW, h: newH },
                    scaleX,
                    scaleY
                });
            }
        });

        resizeObserver.observe(imageElement);

        // Store cleanup function
        canvas.resizeObserver = resizeObserver;
    };

    const setupCanvasInteractions = (canvas, legendId) => {
        let isDown = false;
        let origX, origY;
        let rect;

        canvas.on('mouse:down', (o) => {
            // Get current state from ref (like DefineKeyAreasTab pattern)
            const { isDrawing: currentIsDrawing, drawingLegend: currentDrawingLegend } = drawingStateRef.current;

            console.log(`🖱️ Canvas ${legendId} mouse:down - currentIsDrawing: ${currentIsDrawing}, currentDrawingLegend: ${currentDrawingLegend}, expectedLegend: ${legendId}`);

            if (!currentIsDrawing || currentDrawingLegend !== legendId) {
                console.log(`❌ Canvas click blocked - isDrawing: ${currentIsDrawing}, drawingLegend: ${currentDrawingLegend}, expectedLegend: ${legendId}`);
                return;
            }

            console.log(`✅ Starting symbol annotation on legend ${legendId}`);
            isDown = true;
            const pointer = canvas.getPointer(o.e);
            origX = pointer.x;
            origY = pointer.y;

            console.log(`📍 Mouse down at canvas coordinates: (${origX}, ${origY})`);

            rect = new fabric.Rect({
                left: origX,
                top: origY,
                originX: 'left',
                originY: 'top',
                width: 1,
                height: 1,
                fill: 'transparent',
                stroke: '#FF6B6B',
                strokeWidth: 2,
                strokeDashArray: [5, 5],
                strokeUniform: true,
                selectable: true,
                hasControls: true,
                hasBorders: true,
                symbolId: `symbol-${Date.now()}-${legendId}`
            });

            canvas.add(rect);
            canvas.setActiveObject(rect);
            canvas.requestRenderAll();
        });

        canvas.on('mouse:move', (o) => {
            if (!isDown || !rect) return;

            const pointer = canvas.getPointer(o.e);

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

            if (rect && (rect.width > 10 && rect.height > 10)) {
                // Create new symbol entry
                const symbolId = rect.symbolId;

                // Store canvas coordinates - these will be converted to natural image coordinates when saving
                const newSymbol = {
                    id: symbolId,
                    name: '',
                    description: '',
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height,
                    legendId: legendId,
                    canvasScale: {
                        displayedWidth: canvas.width,
                        displayedHeight: canvas.height
                    }
                };

                console.log(`✅ SYMBOL WITH SCALE CREATED:`, newSymbol);

                updateSymbolData(legendId, symbolId, newSymbol);
                setEditingSymbol({ legendId, symbolId });

                console.log(`🎯 NEW SYMBOL CREATED:`, newSymbol);
                console.log(`🎯 Current symbolData after update:`, symbolData);
            } else if (rect) {
                canvas.remove(rect);
            }

            rect = null;
            // Don't automatically reset drawing state - let user click button again to stop
            // setIsDrawing(false);
            // setDrawingLegend(null);
            canvas.requestRenderAll();

            console.log(`✅ Symbol annotation completed, keeping drawing mode active`);
        });

        canvas.on('object:modified', () => {
            updateSymbolsFromCanvas(canvas, legendId);
        });

        canvas.on('selection:created', (e) => {
            const selectedObject = e.selected[0];
            if (selectedObject && selectedObject.symbolId) {
                setSelectedSymbol({ legendId, symbolId: selectedObject.symbolId });
            }
        });

        canvas.on('selection:updated', (e) => {
            const selectedObject = e.selected[0];
            if (selectedObject && selectedObject.symbolId) {
                setSelectedSymbol({ legendId, symbolId: selectedObject.symbolId });
            }
        });

        canvas.on('selection:cleared', () => {
            setSelectedSymbol(null);
        });

        // Attach DOM listener on Fabric's upper canvas to verify we receive raw mouse events
        if (canvas.upperCanvasEl && !canvas._symbolDomDownListener) {
            const logDomDown = (evt) => {
                const rectEl = canvas.upperCanvasEl.getBoundingClientRect();
                console.log(`🧪 upperCanvasEl mousedown @ (${(evt.clientX - rectEl.left).toFixed(1)}, ${(evt.clientY - rectEl.top).toFixed(1)}) for legend ${legendId}`);
            };
            canvas.upperCanvasEl.addEventListener('mousedown', logDomDown);
            canvas._symbolDomDownListener = logDomDown;
        }
    };

    const loadSymbolsOnCanvas = (canvas, legendId) => {
        const legendSymbols = symbolData[legendId] || {};

        Object.values(legendSymbols).forEach(symbol => {
            const rect = new fabric.Rect({
                left: symbol.left,
                top: symbol.top,
                width: symbol.width,
                height: symbol.height,
                fill: 'transparent',
                stroke: '#FF6B6B',
                strokeWidth: 2,
                strokeDashArray: [5, 5],
                strokeUniform: true,
                selectable: true,
                hasControls: true,
                hasBorders: true,
                symbolId: symbol.id
            });

            canvas.add(rect);
        });

        canvas.requestRenderAll();
    };

    const updateSymbolsFromCanvas = (canvas, legendId) => {
        const objects = canvas.getObjects();

        // Only update coordinates, preserve all other data (name, description, canvasScale, etc.)
        setSymbolData(prev => {
            const legendSymbols = prev[legendId] || {};
            const updatedSymbols = { ...legendSymbols };

            objects
                .filter(obj => obj.symbolId)
                .forEach(obj => {
                    const existingSymbol = updatedSymbols[obj.symbolId] || {};
                    updatedSymbols[obj.symbolId] = {
                        ...existingSymbol, // Preserve ALL existing data
                        // Only update coordinates from canvas
                        left: obj.left,
                        top: obj.top,
                        width: obj.width * obj.scaleX,
                        height: obj.height * obj.scaleY,
                        // Ensure required fields are present
                        id: obj.symbolId,
                        legendId: legendId,
                        // Keep canvasScale in sync with current canvas size so conversions use correct basis
                        canvasScale: {
                            displayedWidth: canvas.width,
                            displayedHeight: canvas.height
                        }
                    };
                });

            console.log(`🔄 CANVAS UPDATE: Preserving data for ${Object.keys(updatedSymbols).length} symbols`);

            return {
                ...prev,
                [legendId]: updatedSymbols
            };
        });
    };

    const updateSymbolData = (legendId, symbolId, symbolInfo) => {
        console.log(`📝 UPDATING SYMBOL DATA:`, { legendId, symbolId, symbolInfo });
        setSymbolData(prev => {
            const newData = {
                ...prev,
                [legendId]: {
                    ...prev[legendId],
                    [symbolId]: symbolInfo
                }
            };
            console.log(`📝 NEW SYMBOL DATA STATE:`, newData);
            return newData;
        });
    };

    const startDrawingSymbol = (legendId) => {
        console.log(`🎯 BUTTON CLICKED: Starting drawing mode for legend: ${legendId}`);
        console.log(`🎯 Available canvases:`, Object.keys(fabricCanvases));
        console.log(`🎯 Current state before update - isDrawing: ${isDrawing}, drawingLegend: ${drawingLegend}`);

        setIsDrawing(true);
        setDrawingLegend(legendId);

        console.log(`🎯 State setters called - should be isDrawing: true, drawingLegend: ${legendId}`);

        // Ensure canvas is ready and has focus
        const canvas = fabricCanvases[legendId];
        if (canvas) {
            canvas.discardActiveObject();
            canvas.requestRenderAll();
            console.log(`✅ Canvas for legend ${legendId} is ready for drawing`);
            console.log(`📊 Canvas details: width=${canvas.width}, height=${canvas.height}`);
        } else {
            console.log(`❌ WARNING: Canvas for legend ${legendId} not found`);
            console.log(`🔍 Available canvas keys:`, Object.keys(fabricCanvases));
        }
    };

    const cancelDrawing = () => {
        console.log(`❌ CANCELING drawing mode`);
        setIsDrawing(false);
        setDrawingLegend(null);

        // Clear any active selections on all canvases
        Object.values(fabricCanvases).forEach(canvas => {
            canvas.discardActiveObject();
            canvas.requestRenderAll();
        });
    };

    const deleteSymbol = (legendId, symbolId) => {
        // Remove from canvas
        const canvas = fabricCanvases[legendId];
        if (canvas) {
            const objectToRemove = canvas.getObjects().find(obj => obj.symbolId === symbolId);
            if (objectToRemove) {
                canvas.remove(objectToRemove);
                canvas.requestRenderAll();
            }
        }

        // Remove from data
        setSymbolData(prev => {
            const newData = { ...prev };
            if (newData[legendId]) {
                delete newData[legendId][symbolId];
                if (Object.keys(newData[legendId]).length === 0) {
                    delete newData[legendId];
                }
            }
            return newData;
        });

        // Clear selection if deleted symbol was selected
        if (selectedSymbol?.symbolId === symbolId) {
            setSelectedSymbol(null);
        }
    };

    const updateSymbolInfo = (legendId, symbolId, field, value) => {
        setSymbolData(prev => {
            const updatedSymbol = {
                ...prev[legendId][symbolId],
                [field]: value
            };

            // Ensure canvasScale is preserved
            if (!updatedSymbol.canvasScale && prev[legendId][symbolId].canvasScale) {
                updatedSymbol.canvasScale = prev[legendId][symbolId].canvasScale;
            }

            console.log(`📝 UPDATING SYMBOL INFO (${field}):`, updatedSymbol);

            return {
                ...prev,
                [legendId]: {
                    ...prev[legendId],
                    [symbolId]: updatedSymbol
                }
            };
        });
    };

    const saveSymbolClippings = async () => {
        try {
            console.log('🚀 [SymbolAnnotation] ENHANCED - Saving symbols with NEW coordinate system');
            console.log('📊 [SymbolAnnotation] Symbol data:', symbolData);

            // Prepare symbol data with enhanced coordinate transformation
            const symbolsToSave = [];

            Object.entries(symbolData).forEach(([legendId, legendSymbols]) => {
                const clippingData = clippingImages[legendId];
                const imageElement = document.querySelector(`img[src="${clippingData?.url}"]`);

                console.log(`\n📐 [SymbolAnnotation] LEGEND ${legendId} ANALYSIS:`);
                console.log(`  Has clipping data: ${!!clippingData}`);
                console.log(`  Has image element: ${!!imageElement}`);
                console.log(`  Natural size: ${imageElement ? `${imageElement.naturalWidth}x${imageElement.naturalHeight}` : 'N/A'}`);

                // Get legend annotation and page metadata for new coordinate system
                const legendAnnotation = clippingData?.annotation;
                const pageNumber = legendAnnotation?.pageNumber;
                const pageMetadata = docInfo?.pageMetadata?.[pageNumber];

                if (pageMetadata && legendAnnotation?.pdfCoordinates) {
                    console.log(`  ✅ NEW coordinate system available for legend ${legendId}`);
                    console.log(`  📄 Legend PDF coords:`, legendAnnotation.pdfCoordinates);

                    // Create PDF coordinates for the legend
                    const legendPdfCoords = new PDFCoordinates(
                        legendAnnotation.pdfCoordinates.left_points,
                        legendAnnotation.pdfCoordinates.top_points,
                        legendAnnotation.pdfCoordinates.width_points,
                        legendAnnotation.pdfCoordinates.height_points
                    );

                    // Create clipping coordinate transformer using ACTUAL clipping image DPI derived from natural size
                    const pageMetaObj = createPageMetadata(pageMetadata);
                    let effectiveClippingDpi = HIGH_RES_DPI;
                    if (imageElement && legendPdfCoords.width > 0) {
                        const derivedDpiFromWidth = (imageElement.naturalWidth * 72.0) / legendPdfCoords.width;
                        const derivedDpiFromHeight = (imageElement.naturalHeight * 72.0) / legendPdfCoords.height;
                        // Use average as a guard (should be identical if aspect is preserved)
                        effectiveClippingDpi = Math.round((derivedDpiFromWidth + derivedDpiFromHeight) / 2);
                    }

                    const clippingTransformer = new ClippingCoordinateTransformer(
                        legendPdfCoords,
                        effectiveClippingDpi,
                        pageMetaObj
                    );

                    console.log(`  🎯 Clipping transformer created: ${clippingTransformer.clippingWidthPixels}x${clippingTransformer.clippingHeightPixels} pixels @ ${effectiveClippingDpi} DPI (natural: ${imageElement?.naturalWidth}x${imageElement?.naturalHeight})`);

                    Object.values(legendSymbols).forEach(symbol => {
                        if (symbol.name && symbol.name.trim()) {
                            console.log(`\n  🔣 [SymbolAnnotation] SYMBOL ANALYSIS: ${symbol.name}`);
                            console.log(`    Canvas coords: (${symbol.left}, ${symbol.top}) ${symbol.width}x${symbol.height}`);

                            try {
                                // Get canvas dimensions from symbol or fallback
                                let canvasWidth, canvasHeight;
                                if (symbol.canvasScale) {
                                    canvasWidth = symbol.canvasScale.displayedWidth;
                                    canvasHeight = symbol.canvasScale.displayedHeight;
                                } else if (fabricCanvases[legendId]) {
                                    canvasWidth = fabricCanvases[legendId].width;
                                    canvasHeight = fabricCanvases[legendId].height;
                                } else if (imageElement) {
                                    canvasWidth = imageElement.offsetWidth;
                                    canvasHeight = imageElement.offsetHeight;
                                } else {
                                    throw new Error('No canvas dimensions available');
                                }

                                console.log(`    Canvas dims: ${canvasWidth}x${canvasHeight}`);

                                // Create symbol canvas coordinates
                                const symbolCanvasCoords = new CanvasCoordinates(
                                    symbol.left, symbol.top, symbol.width, symbol.height,
                                    canvasWidth, canvasHeight
                                );

                                // Transform to absolute PDF coordinates
                                const symbolPdfCoords = clippingTransformer.symbolCanvasToPdf(symbolCanvasCoords);

                                console.log(`    PDF coords (NEW SYSTEM): (${symbolPdfCoords.left.toFixed(3)}, ${symbolPdfCoords.top.toFixed(3)}) ${symbolPdfCoords.width.toFixed(3)}x${symbolPdfCoords.height.toFixed(3)} points`);

                                // Get clipping coordinates for image extraction
                                const clippingCoords = clippingTransformer.canvasToClipping(symbolCanvasCoords);

                                symbolsToSave.push({
                                    ...symbol,
                                    legendId: legendId,
                                    // Canvas coordinates (for UI)
                                    left: symbol.left,
                                    top: symbol.top,
                                    width: symbol.width,
                                    height: symbol.height,
                                    // Canvas dimensions
                                    canvasWidth: canvasWidth,
                                    canvasHeight: canvasHeight,
                                    // Coordinate system info
                                    coordinateSystem: 'NEW_SYSTEM',
                                    pdfCoordinates: symbolPdfCoords.toDict(),
                                    clippingCoordinates: clippingCoords.toDict(),
                                    canvasCoordinates: symbolCanvasCoords.toDict()
                                });

                                console.log(`    ✅ Symbol ${symbol.name} processed with NEW coordinate system`);

                            } catch (error) {
                                console.error(`    ❌ NEW coordinate system failed for ${symbol.name}:`, error);
                                // Fallback to old system
                                console.log(`    🔄 Using FALLBACK coordinate system for ${symbol.name}`);
                                symbolsToSave.push({
                                    ...symbol,
                                    legendId: legendId,
                                    coordinateSystem: 'FALLBACK'
                                });
                            }
                        }
                    });
                } else {
                    // Fallback to old coordinate system
                    console.warn(`  ⚠️  [SymbolAnnotation] No NEW coordinate system data for legend ${legendId}, using FALLBACK`);

                    Object.values(legendSymbols).forEach(symbol => {
                        if (symbol.name && symbol.name.trim()) {
                            if (clippingData && imageElement) {
                                // Old coordinate transformation logic
                                let canvasScale = symbol.canvasScale;

                                if (!canvasScale) {
                                    const canvas = fabricCanvases[legendId];
                                    if (canvas) {
                                        canvasScale = {
                                            displayedWidth: canvas.width,
                                            displayedHeight: canvas.height
                                        };
                                    }
                                }

                                if (canvasScale) {
                                    const scaleX = imageElement.naturalWidth / canvasScale.displayedWidth;
                                    const scaleY = imageElement.naturalHeight / canvasScale.displayedHeight;

                                    const naturalCoords = {
                                        left: symbol.left * scaleX,
                                        top: symbol.top * scaleY,
                                        width: symbol.width * scaleX,
                                        height: symbol.height * scaleY
                                    };

                                    console.log(`  🔄 FALLBACK scaling ${symbol.name}:`, {
                                        canvas: { left: symbol.left, top: symbol.top, width: symbol.width, height: symbol.height },
                                        scale: { scaleX, scaleY },
                                        natural: naturalCoords
                                    });

                                    symbolsToSave.push({
                                        ...symbol,
                                        ...naturalCoords,
                                        legendId: legendId,
                                        coordinateSystem: 'FALLBACK',
                                        originalCanvasCoords: {
                                            left: symbol.left,
                                            top: symbol.top,
                                            width: symbol.width,
                                            height: symbol.height
                                        }
                                    });
                                } else {
                                    symbolsToSave.push({
                                        ...symbol,
                                        legendId: legendId,
                                        coordinateSystem: 'FALLBACK_NO_SCALE'
                                    });
                                }
                            } else {
                                symbolsToSave.push({
                                    ...symbol,
                                    legendId: legendId,
                                    coordinateSystem: 'FALLBACK_NO_DATA'
                                });
                            }
                        }
                    });
                }
            });

            console.log(`\n🚀 [SymbolAnnotation] FINAL SYMBOLS TO SAVE (${symbolsToSave.length} total):`);
            symbolsToSave.forEach((symbol, index) => {
                console.log(`  ${index + 1}. ${symbol.name} (${symbol.coordinateSystem}):`);
                if (symbol.coordinateSystem === 'NEW_SYSTEM') {
                    console.log(`     Canvas: (${symbol.left}, ${symbol.top}) ${symbol.width}x${symbol.height}`);
                    console.log(`     PDF: (${symbol.pdfCoordinates.left_points.toFixed(2)}, ${symbol.pdfCoordinates.top_points.toFixed(2)}) ${symbol.pdfCoordinates.width_points.toFixed(2)}x${symbol.pdfCoordinates.height_points.toFixed(2)} points`);
                } else {
                    console.log(`     Fallback coordinates:`, { left: symbol.left, top: symbol.top, width: symbol.width, height: symbol.height });
                }
            });

            if (symbolsToSave.length === 0) {
                alert('No named symbols to save. Please add names to your symbols first.');
                return;
            }

            console.log(`📤 [SymbolAnnotation] Sending ${symbolsToSave.length} symbols to backend...`);

            const response = await fetch('/api/v1/save_symbol_clippings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    docId: docInfo.docId,
                    symbols: symbolsToSave,
                    clippingImages: clippingImages
                })
            });

            const data = await response.json();

            if (response.ok) {
                console.log(`✅ [SymbolAnnotation] Backend response:`, data);
                alert(`✅ Saved ${data.savedSymbols} symbol clippings!`);
                await onSaveData();
            } else {
                console.error(`❌ [SymbolAnnotation] Backend error:`, data);
                alert(`❌ Failed to save symbols: ${data.error}`);
            }
        } catch (error) {
            console.error('Error saving symbol clippings:', error);
            alert('❌ Error saving symbol clippings. Check console for details.');
        }
    };

    const renderSymbolLegend = (legendId, clippingData) => {
        const legendSymbols = symbolData[legendId] || {};
        const symbolCount = Object.keys(legendSymbols).length;
        const isExpanded = !!expandedLegends[legendId];

        // Reduced logging - only log when symbols change
        if (symbolCount > 0) {
            console.log(`🖼️ LEGEND ${legendId} has ${symbolCount} symbols`);
        }

        return (
            <div key={legendId} className={`symbol-legend-container ${isExpanded ? 'expanded' : 'collapsed'}`}>
                <div className="legend-header">
                    <h3>Symbol Legend - Page {clippingData.annotation.pageNumber}</h3>
                    <div className="legend-controls">
                        <span className="symbol-count">{symbolCount} symbols identified</span>
                        <button
                            className="draw-symbol-btn secondary"
                            onClick={() => setExpandedLegends(prev => ({ ...prev, [legendId]: !isExpanded }))}
                        >
                            {isExpanded ? '▾ Collapse' : '▸ Expand'}
                        </button>
                        {isDrawing && drawingLegend === legendId ? (
                            <button
                                className="draw-symbol-btn cancel"
                                onClick={cancelDrawing}
                            >
                                ✕ Cancel Drawing
                            </button>
                        ) : (
                            <button
                                className="draw-symbol-btn"
                                onClick={() => startDrawingSymbol(legendId)}
                            >
                                + Add Symbol
                            </button>
                        )}
                    </div>
                </div>

                {isExpanded && (
                    <div className="legend-workspace">
                        <div className="legend-image-section">
                            <div className="legend-image-container">
                                <img src={clippingData.url} alt="legend" className="legend-image" onLoad={(e) => {
                                    setClippingImages(prev => ({ ...prev, [legendId]: { ...prev[legendId], loaded: true } }));
                                    setTimeout(() => initializeCanvas(legendId, e.target), 50);
                                }} />
                                <canvas
                                    id={`symbol-canvas-${legendId}`}
                                    className="symbol-annotation-canvas"
                                />
                            </div>

                            {/* Instruction panel removed to avoid shrinking the canvas area */}
                        </div>

                        <div className="symbols-management-section">
                            <div className="symbols-list-header">
                                <h4>📝 Identified Symbols ({Object.keys(legendSymbols).length})</h4>
                                {Object.keys(legendSymbols).length > 0 && (
                                    <button
                                        onClick={() => {
                                            // Auto-name all unnamed symbols
                                            Object.values(legendSymbols).forEach((symbol, index) => {
                                                if (!symbol.name || symbol.name.trim() === '') {
                                                    updateSymbolInfo(legendId, symbol.id, 'name', `Symbol ${index + 1}`);
                                                }
                                            });
                                        }}
                                        className="auto-name-btn"
                                    >
                                        🏷️ Auto-name Unnamed
                                    </button>
                                )}
                            </div>

                            <div className="symbols-list">
                                {Object.keys(legendSymbols).length === 0 ? (
                                    <div className="empty-symbols">
                                        <p>No symbols identified yet.</p>
                                        <p>Click "Add Symbol" above and draw boxes around individual symbols in the legend.</p>
                                    </div>
                                ) : (
                                    <div className="symbols-grid">
                                        {Object.values(legendSymbols).map((symbol, index) => (
                                            <div
                                                key={symbol.id}
                                                className={`symbol-item ${selectedSymbol?.symbolId === symbol.id ? 'selected' : ''}`}
                                                onClick={() => {
                                                    setSelectedSymbol({ legendId, symbolId: symbol.id });
                                                    // Highlight symbol on canvas
                                                    const canvas = fabricCanvases[legendId];
                                                    if (canvas) {
                                                        const symbolObject = canvas.getObjects().find(obj => obj.symbolId === symbol.id);
                                                        if (symbolObject) {
                                                            canvas.setActiveObject(symbolObject);
                                                            canvas.requestRenderAll();
                                                        }
                                                    }
                                                }}
                                            >
                                                <div className="symbol-number">#{index + 1}</div>
                                                <div className="symbol-info">
                                                    {editingSymbol?.symbolId === symbol.id ? (
                                                        <div className="symbol-edit-form">
                                                            <input
                                                                type="text"
                                                                value={symbol.name || ''}
                                                                onChange={(e) => updateSymbolInfo(legendId, symbol.id, 'name', e.target.value)}
                                                                placeholder="Symbol name (required)"
                                                                className="symbol-name-input"
                                                                autoFocus
                                                            />
                                                            <textarea
                                                                value={symbol.description || ''}
                                                                onChange={(e) => updateSymbolInfo(legendId, symbol.id, 'description', e.target.value)}
                                                                placeholder="Symbol description (optional)"
                                                                className="symbol-description-input"
                                                                rows="2"
                                                            />
                                                            <div className="edit-actions">
                                                                <button
                                                                    onClick={() => setEditingSymbol(null)}
                                                                    className="save-symbol-btn"
                                                                >
                                                                    ✓ Save
                                                                </button>
                                                                <button
                                                                    onClick={() => deleteSymbol(legendId, symbol.id)}
                                                                    className="delete-symbol-btn"
                                                                >
                                                                    🗑️ Delete
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <div className="symbol-display">
                                                            <div className="symbol-name">
                                                                {symbol.name ? (
                                                                    <span className="has-name">{symbol.name}</span>
                                                                ) : (
                                                                    <span className="no-name">⚠️ Unnamed Symbol</span>
                                                                )}
                                                            </div>
                                                            <div className="symbol-description">
                                                                {symbol.description || 'No description provided'}
                                                            </div>
                                                            <div className="symbol-coordinates">
                                                                Position: ({Math.round(symbol.left)}, {Math.round(symbol.top)})
                                                                Size: {Math.round(symbol.width)} × {Math.round(symbol.height)}px
                                                            </div>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setEditingSymbol({ legendId, symbolId: symbol.id });
                                                                }}
                                                                className="edit-symbol-btn"
                                                            >
                                                                ✏️ Edit Details
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    if (loadingClippings) {
        return (
            <div className="symbol-annotation-tab">
                <div className="loading-state">
                    <h2>🔣 Symbol Annotation</h2>
                    <p>Loading Symbol Legend clippings...</p>
                    <div className="spinner"></div>
                </div>
            </div>
        );
    }

    const symbolLegendCount = Object.keys(clippingImages).length;
    const totalSymbols = Object.values(symbolData).reduce((total, legendSymbols) =>
        total + Object.keys(legendSymbols).length, 0
    );

    return (
        <div className="symbol-annotation-tab">
            <div className="tab-header">
                <h2>🔣 Symbol Annotation</h2>
                <p>Identify and annotate individual symbols within Symbol Legend clippings.</p>

                <div className="progress-summary">
                    <div className="stat">
                        <span className="stat-number">{symbolLegendCount}</span>
                        <span className="stat-label">Symbol Legends</span>
                    </div>
                    <div className="stat">
                        <span className="stat-number">{totalSymbols}</span>
                        <span className="stat-label">Symbols Identified</span>
                    </div>
                </div>

                {totalSymbols > 0 && (
                    <div className="save-section">
                        <button onClick={saveSymbolClippings} className="save-symbols-button">
                            💾 Save Symbol Clippings ({totalSymbols} symbols)
                        </button>
                    </div>
                )}
            </div>

            <div className="symbols-content">
                {symbolLegendCount === 0 ? (
                    <div className="empty-state">
                        <h3>No Symbol Legends Found</h3>
                        <p>To use this tab, first go to the "Define Key Areas" tab and create Symbol Legend annotations.
                            Then click "Move onto Symbol Identification" to generate clippings.</p>
                        <div className="instructions">
                            <ol>
                                <li>Go to "Define Key Areas" tab</li>
                                <li>Draw boxes around symbol legends using the "Symbol Legend" tool</li>
                                <li>Click "Move onto Symbol Identification"</li>
                                <li>Return here to annotate individual symbols</li>
                            </ol>
                        </div>
                    </div>
                ) : (
                    <div className="legends-container">
                        {Object.entries(clippingImages).map(([legendId, clippingData]) =>
                            renderSymbolLegend(legendId, clippingData)
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SymbolAnnotationTab; 