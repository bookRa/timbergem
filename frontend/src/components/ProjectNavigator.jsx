import React from 'react';
import styles from './ProjectNavigator.module.css';

function ProjectNavigator() {
    return (
        <div className={styles.container}>
            <div className={styles.header}>Project Navigator</div>
            <div className={styles.content}>
                <p className={styles.placeholder}>Navigation tree will appear here.</p>
            </div>
        </div>
    );
}

export default ProjectNavigator;


