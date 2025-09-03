import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export const AppContext = createContext({
    documentPages: [],
    selectedPage: null,
    isLoading: false,
    selectPage: () => {},
    docId: null,
});

export function AppProvider({ docId, children }) {
    const [documentPages, setDocumentPages] = useState([]);
    const [selectedPage, setSelectedPage] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        if (!docId) {
            setDocumentPages([]);
            setSelectedPage(null);
            return;
        }

        let isCancelled = false;
        const controller = new AbortController();

        const fetchPagesOnce = async () => {
            const res = await fetch(`/api/v2/documents/${docId}/pages`, { signal: controller.signal, cache: 'no-store' });
            if (!res.ok) return [];
            const data = await res.json();
            const pages = Array.isArray(data)
                ? data
                : (Array.isArray(data?.pages) ? data.pages : (data?.pages ? Object.values(data.pages) : []));
            return pages;
        };

        const loadWithRetry = async () => {
            try {
                setIsLoading(true);
                const maxAttempts = 30; // ~15s total with 500ms
                for (let i = 0; i < maxAttempts && !isCancelled; i++) {
                    const pages = await fetchPagesOnce();
                    if (pages.length > 0) {
                        setDocumentPages(pages);
                        if (!selectedPage) setSelectedPage(pages[0]);
                        break;
                    }
                    await new Promise(r => setTimeout(r, 500));
                }
            } catch (e) {
                if (!isCancelled && e.name !== 'AbortError') {
                    console.error('Error fetching document pages', e);
                    setDocumentPages([]);
                }
            } finally {
                if (!isCancelled) setIsLoading(false);
            }
        };

        loadWithRetry();
        return () => {
            isCancelled = true;
            controller.abort();
        };
    }, [docId]);

    const selectPage = useCallback((page) => {
        setSelectedPage(page || null);
    }, []);

    const value = useMemo(() => ({
        documentPages,
        selectedPage,
        isLoading,
        selectPage,
        docId,
    }), [documentPages, selectedPage, isLoading, selectPage, docId]);

    return (
        <AppContext.Provider value={value}>
            {children}
        </AppContext.Provider>
    );
}

export function useAppContext() {
    return useContext(AppContext);
}


