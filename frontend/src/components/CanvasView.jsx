import React, { useEffect, useMemo, useRef, useState } from 'react';
import styles from './CanvasView.module.css';
import { useAppContext } from '../context/AppContext';

function CanvasView() {
    const { selectedPage, docId } = useAppContext();
    const containerRef = useRef(null);
    const [viewSize, setViewSize] = useState({ width: 0, height: 0 });

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
        };
        resize();
        const obs = new ResizeObserver(resize);
        obs.observe(el);
        return () => obs.disconnect();
    }, []);

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
                    <div className={styles.imageStage}>
                        {imageUrl ? (
                            <img className={styles.pageImage} src={imageUrl} alt="Page" />
                        ) : (
                            <div className={styles.placeholder}>No image available</div>
                        )}
                        <div className={styles.overlay}>
                            {/* Annotation overlay will be rendered here in next steps */}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default CanvasView;


