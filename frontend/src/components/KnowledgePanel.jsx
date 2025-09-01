import React from 'react';
import styles from './KnowledgePanel.module.css';

function KnowledgePanel() {
    return (
        <div className={styles.container}>
            <div className={styles.header}>Knowledge Panel</div>
            <div className={styles.content}>
                <p className={styles.placeholder}>Contextual insights will appear here.</p>
            </div>
        </div>
    );
}

export default KnowledgePanel;


