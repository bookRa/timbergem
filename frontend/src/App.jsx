import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // We'll create this file for basic styling
import AnnotationCanvas from './components/AnnotationCanvas';

const API_BASE_URL = ''; // Use relative URLs with Vite proxy

function App() {
    const [file, setFile] = useState(null);
    const [docInfo, setDocInfo] = useState(null); // { docId, pageCount }
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [allAnnotations, setAllAnnotations] = useState({});
    const [showAnnotationMode, setShowAnnotationMode] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile && selectedFile.type === "application/pdf") {
            setFile(selectedFile);
            setError('');
            setDocInfo(null); // Reset previous document info
            console.log('File selected:', selectedFile.name);
        } else {
            setFile(null);
            setError('Please select a valid PDF file.');
            console.error('Invalid file type selected.');
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file first.');
            return;
        }

        setIsProcessing(true);
        setError('');
        console.log('Starting upload...');

        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log('Making request to:', `${API_BASE_URL}/api/upload`);
            const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            console.log('Backend Response:', response.data);
            setDocInfo(response.data); // Save the docId and pageCount
            setCurrentPage(1); // Reset to first page
            setAllAnnotations({}); // Clear previous annotations
            setShowAnnotationMode(false); // Start in viewing mode
            
            // Try to load existing annotations
            loadExistingAnnotations(response.data.docId);

        } catch (err) {
            console.error('Upload failed:', err);
            console.error('Error details:', {
                status: err.response?.status,
                statusText: err.response?.statusText,
                data: err.response?.data,
                headers: err.response?.headers,
                message: err.message
            });
            const errorMessage = err.response?.data?.error || err.message || 'An unknown error occurred during upload.';
            setError(errorMessage);
        } finally {
            setIsProcessing(false);
            console.log('Upload process finished.');
        }
    };

    const loadExistingAnnotations = async (docId) => {
        try {
            const response = await axios.get(`/api/load_annotations/${docId}`);
            const annotations = response.data.annotations || [];
            
            // Group annotations by page
            const annotationsByPage = {};
            annotations.forEach(annotation => {
                const page = annotation.pageNumber;
                if (!annotationsByPage[page]) {
                    annotationsByPage[page] = [];
                }
                annotationsByPage[page].push(annotation);
            });
            
            setAllAnnotations(annotationsByPage);
            console.log('Loaded existing annotations:', annotationsByPage);
        } catch (err) {
            console.log('No existing annotations found or error loading:', err.message);
        }
    };

    const handleAnnotationsChange = (pageNumber, annotations) => {
        setAllAnnotations(prev => ({
            ...prev,
            [pageNumber]: annotations
        }));
    };

    const saveAllAnnotations = async () => {
        if (!docInfo) {
            setError('No document loaded');
            return;
        }

        setIsSaving(true);
        setError('');

        try {
            // Flatten all annotations from all pages
            const allAnnotationsArray = [];
            Object.entries(allAnnotations).forEach(([pageNumber, pageAnnotations]) => {
                allAnnotationsArray.push(...pageAnnotations.map(annotation => ({
                    ...annotation,
                    pageNumber: parseInt(pageNumber)
                })));
            });

            console.log('Saving annotations:', allAnnotationsArray);

            const response = await axios.post('/api/save_annotations', {
                docId: docInfo.docId,
                annotations: allAnnotationsArray
            });

            console.log('Annotations saved:', response.data);
            alert(`✅ Successfully saved ${allAnnotationsArray.length} annotations!`);

        } catch (err) {
            console.error('Failed to save annotations:', err);
            const errorMessage = err.response?.data?.error || err.message || 'Failed to save annotations';
            setError(errorMessage);
        } finally {
            setIsSaving(false);
        }
    };

    const getTotalAnnotationCount = () => {
        return Object.values(allAnnotations).reduce((total, pageAnnotations) => {
            return total + pageAnnotations.length;
        }, 0);
    };

    const renderCurrentPage = () => {
        if (!docInfo) return null;

        const imageUrl = `${API_BASE_URL}/data/processed/${docInfo.docId}/page_${currentPage}.png`;
        
        if (showAnnotationMode) {
            return (
                <AnnotationCanvas
                    imageUrl={imageUrl}
                    pageNumber={currentPage}
                    onAnnotationsChange={(annotations) => handleAnnotationsChange(currentPage, annotations)}
                    existingAnnotations={allAnnotations[currentPage] || []}
                />
            );
        } else {
            return (
                <div className="page-container">
                    <p className="page-label">Page {currentPage} of {docInfo.pageCount}</p>
                    <img
                        src={imageUrl}
                        alt={`Page ${currentPage} of document ${docInfo.docId}`}
                        className="page-image"
                    />
                </div>
            );
        }
    };

    const renderPageNavigation = () => {
        if (!docInfo || docInfo.pageCount <= 1) return null;

        return (
            <div className="page-navigation">
                <button 
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage <= 1}
                    className="nav-button"
                >
                    ← Previous
                </button>
                
                <span className="page-info">
                    Page {currentPage} of {docInfo.pageCount}
                </span>
                
                <button 
                    onClick={() => setCurrentPage(Math.min(docInfo.pageCount, currentPage + 1))}
                    disabled={currentPage >= docInfo.pageCount}
                    className="nav-button"
                >
                    Next →
                </button>
            </div>
        );
    };

    return (
        <div className="app-container">
            <header className="app-header">
                <h1>TimberGem 💎 - Context Modeler</h1>
                <p>Upload a construction document to begin the annotation process.</p>
            </header>

            <div className="upload-section">
                <input type="file" onChange={handleFileChange} accept=".pdf" />
                <button onClick={handleUpload} disabled={!file || isProcessing}>
                    {isProcessing ? 'Processing...' : 'Upload & Process'}
                </button>
            </div>

            {error && <p className="error-message">{error}</p>}

            {docInfo && !isProcessing && (
                <div className="document-controls">
                    <div className="mode-controls">
                        <button 
                            onClick={() => setShowAnnotationMode(!showAnnotationMode)}
                            className={`mode-button ${showAnnotationMode ? 'active' : ''}`}
                        >
                            {showAnnotationMode ? '📝 Annotation Mode' : '👁️ View Mode'}
                        </button>
                        
                        {showAnnotationMode && (
                            <button 
                                onClick={saveAllAnnotations}
                                disabled={isSaving || getTotalAnnotationCount() === 0}
                                className="save-button"
                            >
                                {isSaving ? 'Saving...' : `💾 Save Annotations (${getTotalAnnotationCount()})`}
                            </button>
                        )}
                    </div>
                    
                    <div className="document-info">
                        <span>Document: {docInfo.docId}</span>
                        <span>Total Annotations: {getTotalAnnotationCount()}</span>
                    </div>
                </div>
            )}

            <main className="viewer-section">
                {isProcessing && <div className="spinner"></div>}
                {docInfo && !isProcessing && (
                    <div className="document-viewer">
                        {renderPageNavigation()}
                        {renderCurrentPage()}
                        {renderPageNavigation()}
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;