import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const PDFToHTMLTab = ({ docInfo }) => {
    const [isProcessing, setIsProcessing] = useState(false);
    const [processingStatus, setProcessingStatus] = useState('');
    const [processedPages, setProcessedPages] = useState({});
    const [currentPage, setCurrentPage] = useState(null);
    const [completedPages, setCompletedPages] = useState([]);
    const [selectedPageNumber, setSelectedPageNumber] = useState(null);
    const [toastNotifications, setToastNotifications] = useState([]);
    const [htmlResults, setHtmlResults] = useState(null);
    const eventSourceRef = useRef(null);

    // Check for existing HTML results when component loads
    useEffect(() => {
        if (docInfo) {
            checkForExistingHtmlResults();
            // Set up periodic checking for new HTML pages
            const interval = setInterval(() => {
                // Only check if we don't have all pages completed yet
                if (completedPages.length < docInfo.totalPages) {
                    checkForNewHtmlPages();
                } else {
                    console.log('All HTML pages completed, stopping periodic check');
                    clearInterval(interval);
                }
            }, 10000); // Check every 10 seconds
            return () => clearInterval(interval);
        }
    }, [docInfo, completedPages.length]);

    useEffect(() => {
        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
        };
    }, []);

    const checkForExistingHtmlResults = async () => {
        try {
            const response = await axios.get(`/api/load_html_results/${docInfo.docId}`);
            if (response.data.results) {
                setHtmlResults(response.data.results);
                const htmlGen = response.data.results.html_generation;
                
                // Set up completed pages from existing results
                const existingPages = {};
                const completedPageNumbers = [];
                
                htmlGen.results.forEach(pageResult => {
                    if (pageResult.success) {
                        const pageNum = pageResult.page_number;
                        existingPages[pageNum] = {
                            number: pageNum,
                            htmlContent: '', // Will be loaded on demand
                            processingTime: pageResult.processing_time,
                            completedAt: Date.now()
                        };
                        completedPageNumbers.push(pageNum);
                    }
                });
                
                setProcessedPages(existingPages);
                setCompletedPages(completedPageNumbers);
                
                if (completedPageNumbers.length > 0 && !selectedPageNumber) {
                    setSelectedPageNumber(completedPageNumbers[0]);
                    loadPageHtml(completedPageNumbers[0]);
                }
                
                setProcessingStatus(`Found ${htmlGen.successful_pages} completed HTML pages`);
                console.log(`Loaded existing HTML results: ${htmlGen.successful_pages} pages completed`);
            } else {
                setProcessingStatus('No HTML pages generated yet');
            }
        } catch (error) {
            console.log('No existing HTML results found:', error);
            setProcessingStatus('No HTML pages generated yet');
        }
    };

    const checkForNewHtmlPages = async () => {
        try {
            const response = await axios.get(`/api/load_html_results/${docInfo.docId}`);
            if (response.data.results) {
                const htmlGen = response.data.results.html_generation;
                const newCompletedPages = [];
                
                htmlGen.results.forEach(pageResult => {
                    if (pageResult.success) {
                        const pageNum = pageResult.page_number;
                        if (!completedPages.includes(pageNum)) {
                            newCompletedPages.push(pageNum);
                            
                            // Add to processed pages
                            setProcessedPages(prev => ({
                                ...prev,
                                [pageNum]: {
                                    number: pageNum,
                                    htmlContent: '',
                                    processingTime: pageResult.processing_time,
                                    completedAt: Date.now()
                                }
                            }));
                            
                            // Add toast notification
                            const completionOrder = completedPages.length + newCompletedPages.length;
                            const ordinalSuffix = completionOrder === 1 ? 'st' : completionOrder === 2 ? 'nd' : completionOrder === 3 ? 'rd' : 'th';
                            addToast(`📄 Page ${pageNum} HTML ready! (${completionOrder}${ordinalSuffix} to complete)`);
                        }
                    }
                });
                
                if (newCompletedPages.length > 0) {
                    setCompletedPages(prev => [...prev, ...newCompletedPages].sort((a, b) => a - b));
                    setHtmlResults(response.data.results);
                    
                    // Auto-select first new page if none selected
                    if (!selectedPageNumber && newCompletedPages.length > 0) {
                        setSelectedPageNumber(newCompletedPages[0]);
                        loadPageHtml(newCompletedPages[0]);
                    }
                }
            }
        } catch (error) {
            // Silently handle errors for periodic checks
        }
    };

    const loadPageHtml = async (pageNumber) => {
        try {
            const response = await axios.get(`/api/get_page_html/${docInfo.docId}/${pageNumber}`);
            const htmlContent = response.data.htmlContent;
            
            setProcessedPages(prev => ({
                ...prev,
                [pageNumber]: {
                    ...prev[pageNumber],
                    htmlContent: htmlContent
                }
            }));
        } catch (error) {
            console.error(`Failed to load HTML for page ${pageNumber}:`, error);
        }
    };

    const startSimulation = () => {
        if (!docInfo) return;

        setIsProcessing(true);
        setProcessingStatus('Initializing HTML page generation...');
        setProcessedPages({});
        setCurrentPage(null);
        setCompletedPages([]);
        setToastNotifications([]); // Clear any existing toasts

        // Connect to the SSE stream to start simulation
        const eventSource = new EventSource(`/api/simulate_pdf_to_html/${docInfo.docId}`);
        eventSourceRef.current = eventSource;

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleSimulationUpdate(data);
            } catch (error) {
                console.error('Error parsing SSE data:', error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            setProcessingStatus('Connection error occurred');
            setIsProcessing(false);
            eventSource.close();
        };
    };

    // Toast notification functions
    const addToast = (message) => {
        const id = Date.now() + Math.random(); // More unique ID
        const newToast = { id, message };
        
        setToastNotifications(prev => {
            // Check if we already have a toast with the same message
            if (prev.some(toast => toast.message === message)) {
                return prev;
            }
            return [...prev, newToast];
        });
        
        // Auto-remove toast after 4 seconds
        setTimeout(() => {
            setToastNotifications(prev => prev.filter(toast => toast.id !== id));
        }, 4000);
    };

    const removeToast = (id) => {
        setToastNotifications(prev => prev.filter(toast => toast.id !== id));
    };

    const handleSimulationUpdate = (data) => {
        switch (data.type) {
            case 'status':
                setProcessingStatus(data.message);
                break;
            
            case 'page_start':
                setCurrentPage({
                    number: data.page,
                    status: 'processing',
                    estimatedTime: data.estimated_time,
                    startTime: Date.now()
                });
                setProcessingStatus(`Processing page ${data.page}... (estimated ${Math.round(data.estimated_time)}s)`);
                break;
            
            case 'page_complete':
                setProcessedPages(prev => ({
                    ...prev,
                    [data.page]: {
                        number: data.page,
                        htmlContent: data.html_content,
                        processingTime: data.processing_time,
                        completedAt: Date.now()
                    }
                }));
                setCompletedPages(prev => {
                    // Check if page is already completed to avoid duplicates
                    if (prev.includes(data.page)) {
                        return prev;
                    }
                    
                    const newCompleted = [...prev, data.page];
                    // Add toast notification for completed page
                    const completionOrder = newCompleted.length;
                    const ordinalSuffix = completionOrder === 1 ? 'st' : completionOrder === 2 ? 'nd' : completionOrder === 3 ? 'rd' : 'th';
                    addToast(`Page ${data.page} completed! (${completionOrder}${ordinalSuffix} to finish)`);
                    return newCompleted;
                });
                setProcessingStatus(`Page ${data.page} completed in ${Math.round(data.processing_time)}s`);
                setCurrentPage(null);
                
                // Auto-select the first completed page for display
                if (!selectedPageNumber) {
                    setSelectedPageNumber(data.page);
                    loadPageHtml(data.page);
                }
                break;
            
            case 'page_error':
                setProcessingStatus(`Error processing page ${data.page}: ${data.error}`);
                setCurrentPage(null);
                break;
            
            case 'complete':
                setProcessingStatus(`✅ Pipeline completed! Processed ${data.total_pages} pages`);
                setIsProcessing(false);
                setCurrentPage(null);
                if (eventSourceRef.current) {
                    eventSourceRef.current.close();
                }
                break;
            
            case 'error':
                setProcessingStatus(`❌ Error: ${data.message}`);
                setIsProcessing(false);
                setCurrentPage(null);
                if (eventSourceRef.current) {
                    eventSourceRef.current.close();
                }
                break;
        }
    };

    const stopSimulation = () => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }
        setIsProcessing(false);
        setProcessingStatus('Simulation stopped');
        setCurrentPage(null);
    };

    const renderPageProgress = () => {
        if (!currentPage) return null;

        const elapsed = (Date.now() - currentPage.startTime) / 1000;
        const progress = Math.min((elapsed / currentPage.estimatedTime) * 100, 95);

        return (
            <div className="page-progress">
                <div className="progress-header">
                    <h4>Processing Page {currentPage.number}</h4>
                    <span>{Math.round(elapsed)}s / {Math.round(currentPage.estimatedTime)}s</span>
                </div>
                <div className="progress-bar">
                    <div 
                        className="progress-fill" 
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
            </div>
        );
    };

    const renderPageList = () => (
        <div className="page-list">
            <h3>Pages ({completedPages.length} completed)</h3>
            {completedPages.length === 0 ? (
                <p className="empty-state">No pages processed yet</p>
            ) : (
                <>
                    <div className="completion-order">
                        <h4>Completion Order:</h4>
                        <div className="completion-sequence">
                            {completedPages.map((pageNum, index) => (
                                <span key={pageNum} className="completion-item">
                                    {index > 0 && ' → '}
                                    <button
                                        className={`completion-badge ${selectedPageNumber === pageNum ? 'selected' : ''}`}
                                        onClick={() => setSelectedPageNumber(pageNum)}
                                        title={`Page ${pageNum} - Completed ${index + 1}${index === 0 ? 'st' : index === 1 ? 'nd' : index === 2 ? 'rd' : 'th'}`}
                                    >
                                        {pageNum}
                                    </button>
                                </span>
                            ))}
                        </div>
                    </div>
                    <div className="page-buttons">
                        <h4>All Pages (numerical order):</h4>
                        {completedPages
                            .sort((a, b) => a - b) // Sort pages numerically for display
                            .map(pageNum => (
                            <button
                                key={pageNum}
                                className={`page-button ${selectedPageNumber === pageNum ? 'selected' : ''}`}
                                onClick={() => {
                                    setSelectedPageNumber(pageNum);
                                    if (!processedPages[pageNum]?.htmlContent) {
                                        loadPageHtml(pageNum);
                                    }
                                }}
                                title={`Completed in ${Math.round(processedPages[pageNum]?.processingTime || 0)}s`}
                            >
                                <span className="page-number">Page {pageNum}</span>
                                                            {processedPages[pageNum]?.processingTime && (
                                <span className="processing-time">
                                    {Math.round(processedPages[pageNum].processingTime)}s
                                </span>
                            )}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );

    const renderHTMLPreview = () => {
        if (!selectedPageNumber || !processedPages[selectedPageNumber]) {
            return (
                <div className="html-preview-placeholder">
                    <p>Select a completed page to view its HTML content</p>
                </div>
            );
        }

        const page = processedPages[selectedPageNumber];
        
        return (
            <div className="html-preview">
                <div className="preview-header">
                    <h3>Page {page.number} HTML</h3>
                    <span className="processing-time">
                        Processed in {Math.round(page.processingTime)}s
                    </span>
                </div>
                <div className="html-content">
                    <iframe
                        srcDoc={page.htmlContent}
                        title={`Page ${page.number} HTML`}
                        className="html-iframe"
                        sandbox="allow-same-origin allow-scripts"
                    />
                </div>
            </div>
        );
    };

    return (
        <div className="pdf-to-html-tab">
            <div className="tab-header">
                <h2>HTML Page Representations</h2>
            </div>

            <div className="status-section">
                <div className="status-message">{processingStatus}</div>
                {renderPageProgress()}
            </div>

            <div className="content-layout">
                <div className="sidebar">
                    {renderPageList()}
                </div>
                <div className="main-content">
                    {renderHTMLPreview()}
                </div>
            </div>
            
            {/* Toast Notifications */}
            <div className="toast-container">
                {toastNotifications.map(toast => (
                    <div key={toast.id} className="toast-notification">
                        <span className="toast-message">{toast.message}</span>
                        <button 
                            className="toast-close"
                            onClick={() => removeToast(toast.id)}
                        >
                            ×
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PDFToHTMLTab; 