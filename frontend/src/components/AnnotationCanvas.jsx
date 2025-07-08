import React, { useEffect, useRef, useState } from 'react';
import { fabric } from 'fabric';

const AnnotationCanvas = ({ imageUrl, pageNumber, onAnnotationsChange, existingAnnotations }) => {
    const canvasRef = useRef(null);
    const fabricCanvasRef = useRef(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [selectedTag, setSelectedTag] = useState('TitleBlock');
    const [annotations, setAnnotations] = useState(existingAnnotations || []);
    const [canvasObjects, setCanvasObjects] = useState({});

    // Predefined annotation tags based on construction document elements
    const annotationTags = [
        { value: 'TitleBlock', label: 'Title Block', color: '#FF6B6B' },
        { value: 'DrawingArea', label: 'Drawing Area', color: '#4ECDC4' },
        { value: 'NotesArea', label: 'Notes Area', color: '#45B7D1' },
        { value: 'Legend', label: 'Legend', color: '#96CEB4' },
        { value: 'Dimensions', label: 'Dimensions', color: '#FFEAA7' },
        { value: 'RevisionBlock', label: 'Revision Block', color: '#DDA0DD' },
        { value: 'ScaleInfo', label: 'Scale Info', color: '#F39C12' },
        { value: 'Other', label: 'Other', color: '#95A5A6' }
    ];

    useEffect(() => {
        const canvas = new fabric.Canvas(canvasRef.current, {
            selection: true,
            preserveObjectStacking: true,
        });

        fabricCanvasRef.current = canvas;

        // Clear existing objects and render existing annotations if any
        canvas.clear();

        // Define updateAnnotations function first
        const updateAnnotations = () => {
            const objects = canvas.getObjects();
            const newAnnotations = objects
                .filter(obj => obj.annotationTag) // Only annotation rectangles
                .map(obj => ({
                    id: obj.annotationId,
                    tag: obj.annotationTag,
                    label: obj.annotationLabel,
                    left: obj.left,
                    top: obj.top,
                    width: obj.width * obj.scaleX,
                    height: obj.height * obj.scaleY,
                    pageNumber: pageNumber
                }));
            
            setAnnotations(newAnnotations);
            onAnnotationsChange(newAnnotations);
        };

        // Render existing annotations if provided
        if (existingAnnotations && existingAnnotations.length > 0) {
            existingAnnotations.forEach(annotation => {
                const tagConfig = annotationTags.find(tag => tag.value === annotation.tag);
                if (tagConfig) {
                    // Create rectangle
                    const rect = new fabric.Rect({
                        left: annotation.left,
                        top: annotation.top,
                        originX: 'left',
                        originY: 'top',
                        width: annotation.width,
                        height: annotation.height,
                        angle: 0,
                        fill: 'transparent',
                        stroke: tagConfig.color,
                        strokeWidth: 2,
                        strokeDashArray: [5, 5],
                        selectable: true,
                        hasControls: true,
                        hasBorders: true,
                        // Custom properties for annotation
                        annotationTag: annotation.tag,
                        annotationLabel: annotation.label,
                        annotationId: annotation.id
                    });

                    // Add text label
                    const text = new fabric.Text(annotation.label, {
                        left: annotation.left + 5,
                        top: annotation.top + 5,
                        fontSize: 12,
                        fontWeight: 'bold',
                        fill: tagConfig.color,
                        backgroundColor: 'white',
                        padding: 3,
                        border: '1px solid ' + tagConfig.color,
                        borderRadius: 3,
                        selectable: false,
                        hasControls: false
                    });

                    // Add both to canvas
                    canvas.add(rect);
                    canvas.add(text);
                    
                    // Store reference to canvas objects for deletion
                    setCanvasObjects(prev => ({
                        ...prev,
                        [annotation.id]: { rect, text }
                    }));
                }
            });
        }

        // Load the background image
        if (imageUrl) {
            fabric.Image.fromURL(imageUrl, (img) => {
                // Scale image to fit canvas while maintaining aspect ratio
                const canvasWidth = 800;
                const canvasHeight = 600;
                
                const scaleX = canvasWidth / img.width;
                const scaleY = canvasHeight / img.height;
                const scale = Math.min(scaleX, scaleY);

                img.scale(scale);
                
                // Set canvas dimensions to match scaled image
                canvas.setWidth(img.width * scale);
                canvas.setHeight(img.height * scale);
                
                // Set image as background
                canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
                    scaleX: scale,
                    scaleY: scale,
                });
            });
        }

        // Enable drawing mode for rectangles
        let isDown, origX, origY;
        let rect;

        canvas.on('mouse:down', (o) => {
            if (!isDrawing) return;
            
            isDown = true;
            const pointer = canvas.getPointer(o.e);
            origX = pointer.x;
            origY = pointer.y;
            
            const tagConfig = annotationTags.find(tag => tag.value === selectedTag);
            
            rect = new fabric.Rect({
                left: origX,
                top: origY,
                originX: 'left',
                originY: 'top',
                width: 1,
                height: 1,
                angle: 0,
                fill: 'transparent',
                stroke: tagConfig.color,
                strokeWidth: 2,
                strokeDashArray: [5, 5],
                selectable: true,
                hasControls: true,
                hasBorders: true,
                // Custom properties for annotation
                annotationTag: selectedTag,
                annotationLabel: tagConfig.label,
                annotationId: Date.now().toString(),
                pageNumber: pageNumber  // Add page number to the object
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
            if (!isDrawing) return;
            
            isDown = false;
            
            // Add text label to the newly created rectangle
            if (rect) {
                const tagConfig = annotationTags.find(tag => tag.value === selectedTag);
                if (tagConfig) {
                    const text = new fabric.Text(tagConfig.label, {
                        left: rect.left + 5,
                        top: rect.top + 5,
                        fontSize: 12,
                        fontWeight: 'bold',
                        fill: tagConfig.color,
                        backgroundColor: 'white',
                        padding: 3,
                        border: '1px solid ' + tagConfig.color,
                        borderRadius: 3,
                        selectable: false,
                        hasControls: false
                    });
                    
                    canvas.add(text);
                    
                    // Store reference to canvas objects for deletion
                    setCanvasObjects(prev => ({
                        ...prev,
                        [rect.annotationId]: { rect, text }
                    }));
                }
            }
            
            // Update annotations state
            updateAnnotations();
        });

        // Handle object selection and modification
        canvas.on('object:modified', updateAnnotations);
        canvas.on('object:removed', updateAnnotations);

        return () => {
            canvas.dispose();
        };
    }, [imageUrl, pageNumber, selectedTag, isDrawing, onAnnotationsChange, existingAnnotations]);

    const toggleDrawingMode = () => {
        setIsDrawing(!isDrawing);
        if (fabricCanvasRef.current) {
            fabricCanvasRef.current.selection = isDrawing;
        }
    };

    const clearAnnotations = () => {
        if (fabricCanvasRef.current) {
            const objects = fabricCanvasRef.current.getObjects();
            const annotationObjects = objects.filter(obj => obj.annotationTag);
            annotationObjects.forEach(obj => {
                fabricCanvasRef.current.remove(obj);
            });
            fabricCanvasRef.current.renderAll();
            setAnnotations([]);
            onAnnotationsChange([]);
        }
    };

    const deleteSelected = () => {
        if (fabricCanvasRef.current) {
            const activeObjects = fabricCanvasRef.current.getActiveObjects();
            activeObjects.forEach(obj => {
                if (obj.annotationTag) {
                    // Find the annotation ID
                    const annotationId = obj.annotationId;
                    // Remove the object from canvas
                    fabricCanvasRef.current.remove(obj);
                    // Remove from canvasObjects state
                    setCanvasObjects(prev => {
                        const newObjects = { ...prev };
                        delete newObjects[annotationId];
                        return newObjects;
                    });
                }
            });
            fabricCanvasRef.current.discardActiveObject();
            fabricCanvasRef.current.renderAll();
            
            // Update annotations
            const objects = fabricCanvasRef.current.getObjects();
            const newAnnotations = objects
                .filter(obj => obj.annotationTag)
                .map(obj => ({
                    id: obj.annotationId,
                    tag: obj.annotationTag,
                    label: obj.annotationLabel,
                    left: obj.left,
                    top: obj.top,
                    width: obj.width * obj.scaleX,
                    height: obj.height * obj.scaleY,
                    pageNumber: pageNumber
                }));
            
            setAnnotations(newAnnotations);
            onAnnotationsChange(newAnnotations);
        }
    };

    const deleteAnnotation = (annotationId) => {
        if (fabricCanvasRef.current && canvasObjects[annotationId]) {
            const { rect, text } = canvasObjects[annotationId];
            fabricCanvasRef.current.remove(rect);
            fabricCanvasRef.current.remove(text);
            fabricCanvasRef.current.renderAll();
            
            // Remove from canvasObjects state
            setCanvasObjects(prev => {
                const newObjects = { ...prev };
                delete newObjects[annotationId];
                return newObjects;
            });
            
            // Update annotations state
            const newAnnotations = annotations.filter(ann => ann.id !== annotationId);
            setAnnotations(newAnnotations);
            onAnnotationsChange(newAnnotations);
        }
    };

    return (
        <div className="annotation-canvas-container">
            <div className="annotation-controls">
                <div className="control-group">
                    <label htmlFor="tag-select">Annotation Type:</label>
                    <select 
                        id="tag-select"
                        value={selectedTag} 
                        onChange={(e) => setSelectedTag(e.target.value)}
                        className="tag-select"
                    >
                        {annotationTags.map(tag => (
                            <option key={tag.value} value={tag.value}>
                                {tag.label}
                            </option>
                        ))}
                    </select>
                </div>
                
                <div className="control-group">
                    <button 
                        onClick={toggleDrawingMode}
                        className={`draw-button ${isDrawing ? 'active' : ''}`}
                    >
                        {isDrawing ? '✏️ Drawing ON' : '🖱️ Selection Mode'}
                    </button>
                    
                    <button onClick={clearAnnotations} className="clear-button">
                        🗑️ Clear All
                    </button>
                    
                    <button onClick={deleteSelected} className="delete-button">
                        ❌ Delete Selected
                    </button>
                </div>
            </div>

            <div className="canvas-wrapper">
                <canvas ref={canvasRef} className="annotation-canvas" />
            </div>

            <div className="annotations-summary">
                <h4>Annotations on Page {pageNumber} ({annotations.length})</h4>
                {annotations.map(annotation => (
                    <div key={annotation.id} className="annotation-item">
                        <span 
                            className="annotation-color" 
                            style={{ 
                                backgroundColor: annotationTags.find(t => t.value === annotation.tag)?.color 
                            }}
                        ></span>
                        <span className="annotation-label">{annotation.label}</span>
                        <span className="annotation-coords">
                            ({Math.round(annotation.left)}, {Math.round(annotation.top)}) 
                            {Math.round(annotation.width)} × {Math.round(annotation.height)}
                        </span>
                        <button 
                            onClick={() => deleteAnnotation(annotation.id)}
                            className="delete-annotation-button"
                            title="Delete this annotation"
                        >
                            🗑️
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default AnnotationCanvas; 