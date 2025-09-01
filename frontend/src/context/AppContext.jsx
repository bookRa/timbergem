import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export const AppContext = createContext({
    documentPages: [],
    selectedPage: null,
    isLoading: false,
    selectPage: () => {},
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

        const fetchPages = async () => {
            try {
                setIsLoading(true);
                const res = await fetch(`/api/documents/${docId}/pages`, { signal: controller.signal });
                if (!res.ok) {
                    throw new Error(`Failed to fetch pages: ${res.status}`);
                }
                const data = await res.json();
                const pages = Array.isArray(data) ? data : (Array.isArray(data?.pages) ? data.pages : []);
                if (!isCancelled) {
                    setDocumentPages(pages);
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

        fetchPages();
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
    }), [documentPages, selectedPage, isLoading, selectPage]);

    return (
        <AppContext.Provider value={value}>
            {children}
        </AppContext.Provider>
    );
}

export function useAppContext() {
    return useContext(AppContext);
}


