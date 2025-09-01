import React from 'react';
import styles from './CanvasView.module.css';

function CanvasView() {
    return (
        <div className={styles.container}>
            <div className={styles.header}>Canvas View</div>
            <div className={styles.canvasArea}>
                <div className={styles.placeholder}>Interactive canvas area</div>
            </div>
        </div>
    );
}

export default CanvasView;


