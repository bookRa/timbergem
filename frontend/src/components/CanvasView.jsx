import React, { useEffect, useMemo, useRef, useState } from 'react';
import styles from './CanvasView.module.css';
import { useAppContext } from '../context/AppContext';

function CanvasView() {
    const { selectedPage, docId } = useAppContext();
    const containerRef = useRef(null);
    const stageRef = useRef(null);
    const contentRef = useRef(null);
    const [viewSize, setViewSize] = useState({ width: 0, height: 0 });
    // zoom is expressed relative to natural image pixel size (1 = 100% of 10800x7200 etc.)
    const [zoom, setZoom] = useState(0.1);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const isPanningRef = useRef(false);
    const lastMouseRef = useRef({ x: 0, y: 0 });
    const [fitZoom, setFitZoom] = useState(0.1);

    const imageUrl = useMemo(() => {
        if (!docId || !selectedPage) return null;
        const n = selectedPage.page_number ?? selectedPage.pageNumber;
        if (!n) return null;
        return `/data/processed/${docId}/page_${n}.png`;
    }, [docId, selectedPage]);

    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;
        const resize = () => {
            const rect = el.getBoundingClientRect();
            setViewSize({ width: rect.width, height: rect.height });
            // Refit on container resize to avoid scrollbars and keep image centered
            fitToScreen();
        };
        resize();
        const obs = new ResizeObserver(resize);
        obs.observe(el);
        return () => obs.disconnect();
    }, []);

    useEffect(() => {
        // Reset on page change; once image loads, we will compute fit
        setZoom(0.1);
        setPan({ x: 0, y: 0 });
        setFitZoom(0.1);
    }, [selectedPage?.page_number, selectedPage?.pageNumber, docId]);

    const clampPan = (nextPan, z, stageRect, natural) => {
        const buffer = 80;
        const contentW = natural.w * z;
        const contentH = natural.h * z;
        const minX = Math.min(buffer, stageRect.width - contentW - buffer);
        const maxX = Math.max(stageRect.width - contentW + buffer, buffer);
        const minY = Math.min(buffer, stageRect.height - contentH - buffer);
        const maxY = Math.max(stageRect.height - contentH + buffer, buffer);
        return {
            x: Math.max(minX, Math.min(maxX, nextPan.x)),
            y: Math.max(minY, Math.min(maxY, nextPan.y)),
        };
    };

    const getStageRect = () => stageRef.current?.getBoundingClientRect();
    const getNatural = () => {
        const img = contentRef.current?.querySelector('img');
        const w = img?.naturalWidth || img?.width || 1;
        const h = img?.naturalHeight || img?.height || 1;
        return { w, h };
    };

    const onWheel = (e) => {
        const stage = stageRef.current;
        if (!stage) return;
        // Cmd/Ctrl + wheel to zoom
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 1.1 : 1 / 1.1;
            const prev = zoom;
            const next = Math.max(0.05, Math.min(10, prev * delta));

            // Zoom around mouse position
            const rect = stage.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;

            const nat = getNatural();
            const cx = (mx - pan.x) / prev;
            const cy = (my - pan.y) / prev;
            const newPanX = mx - cx * next;
            const newPanY = my - cy * next;
            setPan(clampPan({ x: newPanX, y: newPanY }, next, getStageRect(), nat));
            setZoom(next);
            return;
        }

        // Panning (when zoomed in):
        // - Shift+wheel forces horizontal pan using deltaY (common OS behavior)
        // - Otherwise, detect dominant axis and use that (trackpad horizontal scroll => deltaX)
        if (zoom > fitZoom) {
            e.preventDefault();
            let dx = 0, dy = 0;
            if (e.shiftKey) {
                // Some mice report horizontal delta via deltaX when Shift is held,
                // others convert vertical wheel into deltaY with Shift. Use the non-zero axis.
                const h = Math.abs(e.deltaX) > 0 ? e.deltaX : e.deltaY;
                dx = -h;
            } else {
                const ax = Math.abs(e.deltaX);
                const ay = Math.abs(e.deltaY);
                if (ax > ay) {
                    dx = -e.deltaX;
                } else {
                    dy = -e.deltaY;
                }
            }
            const nat = getNatural();
            const rect = getStageRect();
            setPan((p) => clampPan({ x: p.x + dx, y: p.y + dy }, zoom, rect, nat));
        }
    };

    const onKeyDown = (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            stageRef.current?.classList.add(styles.grab);
        }
    };

    const onKeyUp = (e) => {
        if (e.code === 'Space') {
            stageRef.current?.classList.remove(styles.grab);
        }
    };

    const onMouseDown = (e) => {
        const stage = stageRef.current;
        if (!stage) return;
        // Start panning when space is held, or when already grabbing
        if (e.button === 0 && (e.getModifierState('Space') || stage.classList.contains(styles.grab))) {
            e.preventDefault();
            isPanningRef.current = true;
            lastMouseRef.current = { x: e.clientX, y: e.clientY };
            stage.classList.add(styles.grabbing);
        }
    };

    const onMouseMove = (e) => {
        if (!isPanningRef.current) return;
        const dx = e.clientX - lastMouseRef.current.x;
        const dy = e.clientY - lastMouseRef.current.y;
        lastMouseRef.current = { x: e.clientX, y: e.clientY };
        const nat = getNatural();
        const rect = getStageRect();
        setPan((p) => clampPan({ x: p.x + dx, y: p.y + dy }, zoom, rect, nat));
    };

    const onMouseUp = () => {
        if (!isPanningRef.current) return;
        isPanningRef.current = false;
        stageRef.current?.classList.remove(styles.grabbing);
    };

    useEffect(() => {
        const stage = stageRef.current;
        if (!stage) return;
        stage.addEventListener('wheel', onWheel, { passive: false });
        stage.addEventListener('mousedown', onMouseDown);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
        return () => {
            stage.removeEventListener('wheel', onWheel);
            stage.removeEventListener('mousedown', onMouseDown);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
            window.removeEventListener('keydown', onKeyDown);
            window.removeEventListener('keyup', onKeyUp);
        };
    }, [zoom]);

    const fitToScreen = () => {
        const stage = stageRef.current;
        const img = contentRef.current?.querySelector('img');
        if (!stage || !img) return;
        const rect = stage.getBoundingClientRect();
        const padding = 16;
        const availW = Math.max(100, rect.width - padding * 2);
        const availH = Math.max(100, rect.height - padding * 2);
        const naturalW = img.naturalWidth || img.width;
        const naturalH = img.naturalHeight || img.height;
        const scaleX = availW / naturalW; // this will be ~0.09 for 10800->1000
        const scaleY = availH / naturalH;
        const computedFit = Math.max(0.01, Math.min(scaleX, scaleY));
        setFitZoom(computedFit);
        const nextZoom = Math.min(5, computedFit);
        setZoom(nextZoom);
        // Center the image
        const mx = rect.width / 2;
        const my = rect.height / 2;
        const cx = naturalW / 2;
        const cy = naturalH / 2;
        const centered = { x: mx - cx * nextZoom, y: my - cy * nextZoom };
        setPan(clampPan(centered, nextZoom, rect, { w: naturalW, h: naturalH }));
    };

    const zoomBy = (factor, pivotX, pivotY) => {
        const rect = getStageRect();
        if (!rect) return;
        const prev = zoom;
        const next = Math.max(0.05, Math.min(10, prev * factor));
        const mx = pivotX != null ? pivotX : rect.width / 2;
        const my = pivotY != null ? pivotY : rect.height / 2;
        const cx = (mx - pan.x) / prev;
        const cy = (my - pan.y) / prev;
        const newPanX = mx - cx * next;
        const newPanY = my - cy * next;
        const nat = getNatural();
        const clamped = clampPan({ x: newPanX, y: newPanY }, next, rect, nat);
        setPan(clamped);
        setZoom(next);
    };

    const zoomIn = () => zoomBy(1.2);
    const zoomOut = () => zoomBy(1 / 1.2);

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                {selectedPage ? (
                    <>
                        <span>Page {(selectedPage.page_number ?? selectedPage.pageNumber)}</span>
                        {selectedPage.sheet_number && (
                            <span style={{ marginLeft: 8, color: '#6c757d' }}>· {selectedPage.sheet_number}</span>
                        )}
                    </>
                ) : (
                    <span>No page selected</span>
                )}
            </div>
            <div ref={containerRef} className={styles.canvasArea}>
                {!selectedPage && (
                    <div className={styles.placeholder}>Select a page to view</div>
                )}
                {selectedPage && (
                    <>
                        <div ref={stageRef} className={styles.imageStage}>
                            <div
                                ref={contentRef}
                                className={styles.contentLayer}
                                style={{
                                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                                    transformOrigin: '0 0',
                                }}
                            >
                                {imageUrl ? (
                                    <img
                                        className={styles.pageImage}
                                        src={imageUrl}
                                        alt="Page"
                                        onLoad={() => {
                                            // Recompute fit when image loads and after resizes
                                            fitToScreen();
                                        }}
                                    />
                                ) : (
                                    <div className={styles.placeholder}>No image available</div>
                                )}
                            </div>
                            <div className={styles.overlay} />
                        </div>
                        <div className={styles.controls}>
                            <button className={styles.controlButton} onClick={zoomOut}>−</button>
                            <button className={styles.controlButton} onClick={zoomIn}>+</button>
                            <button className={styles.controlButton} onClick={fitToScreen}>Fit</button>
                            <span className={styles.zoomInfo}>{Math.round(zoom * 100)}%</span>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

export default CanvasView;


