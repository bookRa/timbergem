import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import styles from './AppLayout.module.css';
import ProjectNavigator from './components/ProjectNavigator';
import CanvasView from './components/CanvasView';
import KnowledgePanel from './components/KnowledgePanel';

const API_BASE_URL = '';

function App() {
    const [file, setFile] = useState(null);
    const [docInfo, setDocInfo] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');
    const [allAnnotations, setAllAnnotations] = useState({});
    const [pageSummaries, setPageSummaries] = useState({});
    
    // LLM Provider selection
    const [selectedLlmProvider, setSelectedLlmProvider] = useState('mock');
    
    // Pixmap tracking state
    const [pixmapStatus, setPixmapStatus] = useState({}); // {pageNum: 'loading'|'ready'|'error'}
    const [pixmapNotifications, setPixmapNotifications] = useState([]);
    const [htmlPipelineTriggered, setHtmlPipelineTriggered] = useState(false); // Track if HTML pipeline was already triggered
    const pixmapCheckIntervalRef = useRef(null); // Store the interval reference
    const [processingStatus, setProcessingStatus] = useState(''); // Processing status text
    
    const [projectData, setProjectData] = useState({
        keyAreas: {},
        summaries: {},
        symbols: {}, // page_number -> { symbol_id -> { name, description, coordinates } }
        knowledgeGraph: null,
        scopeGroups: [],
        scopeAnnotations: {}
    });

    // --- Dev-only preload harness (temporary while revamping UI) ---
    // Toggle off by visiting with ?dev=off or setting localStorage 'tg-dev-preload-off' = '1'
    useEffect(() => {
        const PRELOAD_DOC_ID = '871dfc70-f8eb-4368-902c-e8c6679b82cb';

        // Skip if a doc is already loaded
        if (docInfo) return;

        try {
            const params = new URLSearchParams(window.location.search);
            const devOff = params.get('dev') === 'off' || localStorage.getItem('tg-dev-preload-off') === '1';
            if (devOff) return;

            const preload = async () => {
                try {
                    // Load authoritative page metadata for coordinate mapping
                    const res = await fetch(`/data/processed/${PRELOAD_DOC_ID}/page_metadata.json`);
                    if (!res.ok) {
                        console.warn('[DEV PRELOAD] page_metadata.json not found; skipping preload');
                        return;
                    }
                    const meta = await res.json();

                    const pages = meta.pages || {};
                    const pageNums = Object.keys(pages).map(n => parseInt(n, 10)).sort((a, b) => a - b);
                    const totalPages = meta.totalPages || pageNums.length || 1;

                    // Establish doc info (used by all tabs) and prevent auto HTML pipeline
                    setDocInfo({
                        docId: PRELOAD_DOC_ID,
                        totalPages: totalPages,
                        pageMetadata: pages
                    });

                    // Mark all pixmaps as ready so canvases load immediately
                    const readyMap = {};
                    pageNums.forEach(p => { readyMap[p] = 'ready'; });
                    setPixmapStatus(readyMap);
                    // Prevent the auto HTML pipeline from kicking off due to all-ready state
                    setHtmlPipelineTriggered(true);

                    // Load any existing annotations/summaries for this doc
                    await loadExistingData(PRELOAD_DOC_ID);

                    console.log(`[DEV PRELOAD] Loaded doc ${PRELOAD_DOC_ID} with ${totalPages} pages`);
                } catch (e) {
                    console.error('[DEV PRELOAD] Failed to preload document', e);
                }
            };

            preload();
        } catch (e) {
            // no-op
        }
    }, [docInfo]);

    // Tabs removed in favor of a three-column layout

    // Pixmap availability checking
    const checkPixmapAvailability = async (docId, totalPages) => {
        console.log(`🔍 Starting pixmap availability check for document ${docId} with ${totalPages} pages...`);
        setProcessingStatus(`🖼️ Processing ${totalPages} page${totalPages > 1 ? 's' : ''}...`);
        
        for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
            setPixmapStatus(prev => ({ ...prev, [pageNum]: 'loading' }));
            checkPagePixmap(docId, pageNum);
        }
        
        // Set up periodic checking for pages that aren't ready yet
        const checkInterval = setInterval(() => {
            console.log(`🔄 Periodic pixmap check...`);
            Object.entries(pixmapStatus).forEach(([pageNum, status]) => {
                if (status === 'loading' || status === 'error') {
                    console.log(`Rechecking page ${pageNum} (status: ${status})`);
                    checkPagePixmap(docId, parseInt(pageNum));
                }
            });
        }, 5000);

        // Store the interval reference
        pixmapCheckIntervalRef.current = checkInterval;

        // Clear interval after 2 minutes
        setTimeout(() => {
            console.log(`⏰ Stopping pixmap check after 2 minutes`);
            clearInterval(checkInterval);
            pixmapCheckIntervalRef.current = null;
        }, 120000);
    };

    // Check if all pixmaps are ready and trigger HTML pipeline (only once)
    useEffect(() => {
        if (!docInfo || htmlPipelineTriggered) return;
        
        const allPageNums = Array.from({ length: docInfo.totalPages }, (_, i) => i + 1);
        const allReady = allPageNums.every(pageNum => pixmapStatus[pageNum] === 'ready');
        const hasAnyStatus = allPageNums.some(pageNum => pixmapStatus[pageNum]);
        
        if (allReady && hasAnyStatus) {
            console.log('All pixmaps ready! Automatically starting HTML pipeline...');
            setProcessingStatus('🚀 Starting HTML generation...');
            addPixmapNotification('🚀 All images ready! Starting HTML generation...');
            setHtmlPipelineTriggered(true); // Prevent triggering again
            
            // Stop periodic pixmap checking since all are ready
            if (pixmapCheckIntervalRef.current) {
                console.log('✅ Stopping pixmap periodic check - all ready');
                clearInterval(pixmapCheckIntervalRef.current);
                pixmapCheckIntervalRef.current = null;
            }
            
            startHtmlPipeline();
        }
    }, [pixmapStatus, docInfo, htmlPipelineTriggered]);

    const startHtmlPipeline = async () => {
        if (!docInfo) return;
        
        try {
            console.log(`Starting HTML pipeline for document ${docInfo.docId}`);
            
            // Prepare config based on selected provider
            const config = {
                llm_provider: selectedLlmProvider,
                dpi: 200,
                high_res_dpi: 300,
                max_concurrent_requests: 3
            };
            
            // Add provider-specific configuration
            if (selectedLlmProvider === 'gemini') {
                config.llm_model = 'gemini-2.5-pro';
                // Note: API key will be loaded from environment variables on backend
            }
            
            const response = await axios.post('/api/process_pdf_to_html', {
                docId: docInfo.docId,
                config: config
            });
            
            console.log('HTML pipeline started successfully:', response.data);
            setProcessingStatus('✅ HTML generation completed!');
            addPixmapNotification('✅ HTML generation completed!');
            
            // Clear processing status after a delay
            setTimeout(() => {
                setProcessingStatus('');
            }, 3000);
            
        } catch (error) {
            console.error('Failed to start HTML pipeline:', error);
            addPixmapNotification('❌ HTML generation failed');
        }
    };

    const checkPagePixmap = async (docId, pageNum) => {
        try {
            // Check the legacy format first (created by app.py upload endpoint)
            const legacyImageUrl = `/data/processed/${docId}/page_${pageNum}.png`;
            console.log(`Checking pixmap for page ${pageNum}: ${legacyImageUrl}`);
            const legacyResponse = await fetch(legacyImageUrl, { method: 'HEAD' });
            
            if (legacyResponse.ok) {
                console.log(`✅ Page ${pageNum} pixmap found (legacy format)`);
                setPixmapStatus(prev => {
                    if (prev[pageNum] !== 'ready') {
                        // Add notification for newly ready pixmap
                        addPixmapNotification(`🖼️ Page ${pageNum} image is ready!`);
                        // Update processing status with current progress
                        updateProcessingProgress(pageNum, docId);
                        return { ...prev, [pageNum]: 'ready' };
                    }
                    return prev;
                });
                return;
            }
            
            // If legacy doesn't exist, check the high-res pixmap format
            const pixmapImageUrl = `/data/processed/${docId}/page_${pageNum}/page_${pageNum}_pixmap.png`;
            console.log(`Legacy not found, checking pixmap format: ${pixmapImageUrl}`);
            const pixmapResponse = await fetch(pixmapImageUrl, { method: 'HEAD' });
            
            if (pixmapResponse.ok) {
                console.log(`✅ Page ${pageNum} pixmap found (high-res format)`);
                setPixmapStatus(prev => {
                    if (prev[pageNum] !== 'ready') {
                        // Add notification for newly ready pixmap
                        addPixmapNotification(`🖼️ Page ${pageNum} image is ready!`);
                        // Update processing status with current progress
                        updateProcessingProgress(pageNum, docId);
                        return { ...prev, [pageNum]: 'ready' };
                    }
                    return prev;
                });
            } else {
                console.log(`❌ Page ${pageNum} pixmap not found yet`);
                setPixmapStatus(prev => ({ ...prev, [pageNum]: 'loading' }));
            }
        } catch (error) {
            console.error(`Error checking page ${pageNum} pixmap:`, error);
            setPixmapStatus(prev => ({ ...prev, [pageNum]: 'error' }));
        }
    };

    const updateProcessingProgress = (completedPageNum, docId) => {
        if (!docInfo) return;
        
        // Count how many pages are ready
        const allPageNums = Array.from({ length: docInfo.totalPages }, (_, i) => i + 1);
        const readyCount = allPageNums.filter(pageNum => 
            pixmapStatus[pageNum] === 'ready' || pageNum === completedPageNum
        ).length;
        
        if (readyCount === docInfo.totalPages) {
            setProcessingStatus('✅ All page images ready! Setting up interface...');
        } else {
            setProcessingStatus(`🖼️ Page images ready: ${readyCount}/${docInfo.totalPages}`);
        }
    };

    // Pixmap notification functions
    const addPixmapNotification = (message) => {
        const id = Date.now() + Math.random();
        const newNotification = { id, message };
        
        setPixmapNotifications(prev => {
            // Check if we already have a notification with the same message
            if (prev.some(notif => notif.message === message)) {
                return prev;
            }
            return [...prev, newNotification];
        });
        
        // Auto-remove notification after 4 seconds
        setTimeout(() => {
            setPixmapNotifications(prev => prev.filter(notif => notif.id !== id));
        }, 4000);
    };

    const removePixmapNotification = (id) => {
        setPixmapNotifications(prev => prev.filter(notif => notif.id !== id));
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile && selectedFile.type === "application/pdf") {
            setFile(selectedFile);
            setError('');
            setDocInfo(null);
            setAllAnnotations({});
            setPageSummaries({});
            setPixmapStatus({});
            setPixmapNotifications([]);
            setHtmlPipelineTriggered(false); // Reset for new document
            setProcessingStatus(''); // Reset processing status
            setProjectData({
                keyAreas: {},
                summaries: {},
                symbols: {},
                knowledgeGraph: null,
                scopeGroups: [],
                scopeAnnotations: {}
            });
        } else {
            setFile(null);
            setError('Please select a valid PDF file.');
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file first.');
            return;
        }

        setIsProcessing(true);
        setError('');
        setProcessingStatus('📄 Uploading PDF and processing page images...');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setDocInfo(response.data);
            setProcessingStatus('🔍 Checking for page images...');
            
            // Load existing data if available
            await loadExistingData(response.data.docId);
            
            // Start checking for pixmaps
            await checkPixmapAvailability(response.data.docId, response.data.totalPages);

        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'An unknown error occurred during upload.';
            setError(errorMessage);
        } finally {
            setIsProcessing(false);
            setProcessingStatus('');
        }
    };

    const loadExistingData = async (docId) => {
        try {
            // Load annotations
            const annotationsResponse = await axios.get(`/api/load_annotations/${docId}`);
            const annotations = annotationsResponse.data.annotations || [];
            
            const annotationsByPage = {};
            annotations.forEach(annotation => {
                const page = annotation.pageNumber;
                if (!annotationsByPage[page]) {
                    annotationsByPage[page] = [];
                }
                annotationsByPage[page].push(annotation);
            });
            
            setAllAnnotations(annotationsByPage);

            // Load page summaries
            try {
                const summariesResponse = await axios.get(`/api/load_summaries/${docId}`);
                setPageSummaries(summariesResponse.data.summaries || {});
            } catch (err) {
                console.log('No existing summaries found');
            }

        } catch (err) {
            console.log('No existing data found');
        }
    };

    const handleAnnotationsChange = (pageNumber, annotations) => {
        setAllAnnotations(prev => ({
            ...prev,
            [pageNumber]: annotations
        }));
        
        setProjectData(prev => ({
            ...prev,
            keyAreas: {
                ...prev.keyAreas,
                [pageNumber]: annotations
            }
        }));
    };

    const handleSummaryChange = (pageNumber, summary) => {
        setPageSummaries(prev => ({
            ...prev,
            [pageNumber]: summary
        }));
        
        setProjectData(prev => ({
            ...prev,
            summaries: {
                ...prev.summaries,
                [pageNumber]: summary
            }
        }));
    };

    const saveProjectData = async () => {
        if (!docInfo) return;

        try {
            await axios.post('/api/save_project_data', {
                docId: docInfo.docId,
                projectData: projectData
            });
            alert('✅ Project data saved successfully!');
        } catch (err) {
            console.error('Failed to save project data:', err);
            setError('Failed to save project data');
        }
    };

    // Removed tab rendering logic

    // Removed tab placeholder

    return (
        <div className={styles.appRoot}>
            <header className={styles.header}>
                <div className={styles.titleRow}>
                    <h1 className={styles.title}>TimberGem 💎 - Context Modeler</h1>
                    <div className={styles.controls}>
                    {/* LLM Provider Selection */}
                    <div className="llm-provider-section">
                        <label htmlFor="llm-provider">LLM Provider:</label>
                        <select
                            id="llm-provider"
                            value={selectedLlmProvider}
                            onChange={(e) => setSelectedLlmProvider(e.target.value)}
                            className="llm-provider-select"
                        >
                            <option value="mock">Mock (Fast Testing)</option>
                            <option value="gemini">Gemini (Production)</option>
                        </select>
                        <span className="provider-info">
                            {selectedLlmProvider === 'mock' 
                                ? '🧪 Simulated HTML generation (2-3s per page)' 
                                : '🚀 Real AI-powered generation (requires GEMINI_API_KEY)'
                            }
                        </span>
                    </div>
                    
                    {!isProcessing && (
                        <div className="upload-section">
                            <input type="file" onChange={handleFileChange} accept=".pdf" />
                            <button onClick={handleUpload} disabled={!file || isProcessing}>
                                {isProcessing ? 'Processing...' : 'Upload & Process'}
                            </button>
                        </div>
                    )}
                    </div>
                </div>
                {error && <p className="error-message">{error}</p>}
            </header>

            {/* Processing Status */}
            {isProcessing && processingStatus && (
                <div className="processing-status">
                    <div className="processing-indicator">
                        <div className="spinner-small"></div>
                        <span>{processingStatus}</span>
                    </div>
                </div>
            )}

            <div className={styles.mainRow}>
                <div className={styles.leftCol}>
                    <ProjectNavigator />
                </div>
                <div className={styles.centerCol}>
                    <CanvasView />
                </div>
                <div className={styles.rightCol}>
                    <KnowledgePanel />
                </div>
            </div>

            {/* Pixmap Notifications */}
            {pixmapNotifications.length > 0 && (
                <div className="pixmap-notifications">
                    {pixmapNotifications.map(notification => (
                        <div key={notification.id} className="pixmap-notification">
                            {notification.message}
                            <button onClick={() => removePixmapNotification(notification.id)}>✕</button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default App;