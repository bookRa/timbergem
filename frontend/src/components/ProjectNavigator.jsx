import React from 'react';
import styles from './ProjectNavigator.module.css';
import { useAppContext } from '../context/AppContext';

function ProjectNavigator() {
    const { documentPages, selectedPage, isLoading, selectPage } = useAppContext();

    return (
        <div className={styles.container}>
            <div className={styles.header}>Project Navigator</div>
            <div className={styles.content}>
                {isLoading && (
                    <div className={styles.loading}>Loading pages...</div>
                )}
                {!isLoading && documentPages && documentPages.length === 0 && (
                    <p className={styles.placeholder}>No pages found.</p>
                )}
                {!isLoading && documentPages && documentPages.length > 0 && (
                    <ul className={styles.pageList}>
                        {documentPages.map((page) => {
                            const key = page.page_number ?? page.pageNumber ?? page.id ?? String(Math.random());
                            const isSelected = !!selectedPage && (selectedPage.page_number ?? selectedPage.pageNumber) === (page.page_number ?? page.pageNumber);
                            return (
                                <li
                                    key={key}
                                    className={`${styles.pageItem} ${isSelected ? styles.selected : ''}`}
                                    onClick={() => selectPage(page)}
                                >
                                    <div className={styles.pagePrimary}>
                                        <span className={styles.pageNum}>Page {(page.page_number ?? page.pageNumber)}</span>
                                        {page.sheet_number && (
                                            <span className={styles.sheetNum}>{page.sheet_number}</span>
                                        )}
                                    </div>
                                    {page.title && (
                                        <div className={styles.pageTitle}>
                                            {page.title}
                                        </div>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                )}
            </div>
        </div>
    );
}

export default ProjectNavigator;


