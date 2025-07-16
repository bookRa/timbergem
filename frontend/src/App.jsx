import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import DefineKeyAreasTab from './components/DefineKeyAreasTab';
import KnowledgeGraphTab from './components/KnowledgeGraphTab';
import ScopeGroupsTab from './components/ScopeGroupsTab';
import ScopeAnnotationsTab from './components/ScopeAnnotationsTab';
import PDFToHTMLTab from './components/PDFToHTMLTab';

const API_BASE_URL = '';

function App() {
    const [file, setFile] = useState(null);
    const [docInfo, setDocInfo] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('pdf-to-html');
    const [allAnnotations, setAllAnnotations] = useState({});
    const [pageSummaries, setPageSummaries] = useState({});
    const [isTestingMode, setIsTestingMode] = useState(true);
    const [projectData, setProjectData] = useState({
        keyAreas: {},
        summaries: {},
        knowledgeGraph: null,
        scopeGroups: [],
        scopeAnnotations: {}
    });

    // Auto-load TEST document when in testing mode
    useEffect(() => {
        if (isTestingMode) {
            simulateTestUpload();
        }
    }, [isTestingMode]);

    const simulateTestUpload = async () => {
        console.log('Simulating TEST document upload...');
        try {
            // Simulate the document info for the TEST document
            const testDocInfo = {
                docId: 'TEST',
                totalPages: 7,
                message: 'TEST document loaded for simulation',
                // Simulate file metadata
                filename: 'Test Construction Document.pdf'
            };
            
            setDocInfo(testDocInfo);
            setError('');
            
            // Load existing data if available
            await loadExistingData('TEST');
            
            console.log('TEST document simulation loaded successfully');
        } catch (err) {
            console.error('Error simulating TEST upload:', err);
            setError('Failed to load TEST document for simulation');
        }
    };

    const tabs = [
        { id: 'pdf-to-html', label: 'PDF-to-HTML Pipeline', component: PDFToHTMLTab },
        { id: 'define-key-areas', label: 'Define Key Areas', component: DefineKeyAreasTab },
        { id: 'knowledge-graph', label: 'Knowledge Graph', component: KnowledgeGraphTab },
        { id: 'scope-groups', label: 'Scope Groups', component: ScopeGroupsTab },
        { id: 'scope-annotations', label: 'Scope Annotations', component: ScopeAnnotationsTab }
    ];

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile && selectedFile.type === "application/pdf") {
            setFile(selectedFile);
            setError('');
            setDocInfo(null);
            setAllAnnotations({});
            setPageSummaries({});
            setProjectData({
                keyAreas: {},
                summaries: {},
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

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setDocInfo(response.data);
            
            // Load existing data if available
            await loadExistingData(response.data.docId);

        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'An unknown error occurred during upload.';
            setError(errorMessage);
        } finally {
            setIsProcessing(false);
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

    const renderActiveTab = () => {
        const activeTabConfig = tabs.find(tab => tab.id === activeTab);
        if (!activeTabConfig || !docInfo) return null;

        const TabComponent = activeTabConfig.component;
        
        const commonProps = {
            docInfo,
            allAnnotations,
            pageSummaries,
            projectData,
            onAnnotationsChange: handleAnnotationsChange,
            onSummaryChange: handleSummaryChange,
            onProjectDataChange: setProjectData,
            onSaveData: saveProjectData
        };

        // PDF-to-HTML tab only needs docInfo
        if (activeTabConfig.id === 'pdf-to-html') {
            return <TabComponent docInfo={docInfo} />;
        }

        return <TabComponent {...commonProps} />;
    };

    return (
        <div className="app-container">
            <header className="app-header">
                <h1>TimberGem 💎 - Context Modeler</h1>
                <div className="header-controls">
                    <div className="testing-mode-section">
                        <button
                            onClick={() => setIsTestingMode(!isTestingMode)}
                            className={`testing-mode-button ${isTestingMode ? 'active' : ''}`}
                        >
                            {isTestingMode ? '🧪 Testing Mode ON' : '🧪 Testing Mode OFF'}
                        </button>
                        {isTestingMode && (
                            <span className="testing-mode-info">
                                Auto-loaded TEST document for simulation
                            </span>
                        )}
                    </div>
                    
                    {!isTestingMode && (
                        <div className="upload-section">
                            <input type="file" onChange={handleFileChange} accept=".pdf" />
                            <button onClick={handleUpload} disabled={!file || isProcessing}>
                                {isProcessing ? 'Processing...' : 'Upload & Process'}
                            </button>
                        </div>
                    )}
                </div>
                {error && <p className="error-message">{error}</p>}
            </header>

            {docInfo && !isProcessing && (
                <div className="main-content">
                    <nav className="tab-navigation">
                        {tabs.map(tab => (
                            <button
                                key={tab.id}
                                className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
                                onClick={() => setActiveTab(tab.id)}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </nav>

                    <div className="tab-content">
                        {renderActiveTab()}
                    </div>
                </div>
            )}

            {isProcessing && <div className="spinner"></div>}
        </div>
    );
}

export default App;