import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // We'll create this file for basic styling

const API_BASE_URL = 'http://localhost:5000';

function App() {
    const [file, setFile] = useState(null);
    const [docInfo, setDocInfo] = useState(null); // { docId, pageCount }
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');

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
            const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            console.log('Backend Response:', response.data);
            setDocInfo(response.data); // Save the docId and pageCount

        } catch (err) {
            console.error('Upload failed:', err);
            const errorMessage = err.response?.data?.error || 'An unknown error occurred during upload.';
            setError(errorMessage);
        } finally {
            setIsProcessing(false);
            console.log('Upload process finished.');
        }
    };

    const renderPageImages = () => {
        if (!docInfo) return null;

        const pageImages = [];
        for (let i = 1; i <= docInfo.pageCount; i++) {
            const imageUrl = `${API_BASE_URL}/data/processed/${docInfo.docId}/page_${i}.png`;
            pageImages.push(
                <div key={i} className="page-container">
                    <p className="page-label">Page {i}</p>
                    <img
                        src={imageUrl}
                        alt={`Page ${i} of document ${docInfo.docId}`}
                        className="page-image"
                    />
                </div>
            );
        }
        return pageImages;
    };

    return (
        <div className="app-container">
            <header className="app-header">
                <h1>TimberGem 💎 - Context Modeler</h1>
                <p>Upload a construction document to begin the process.</p>
            </header>

            <div className="upload-section">
                <input type="file" onChange={handleFileChange} accept=".pdf" />
                <button onClick={handleUpload} disabled={!file || isProcessing}>
                    {isProcessing ? 'Processing...' : 'Upload & Process'}
                </button>
            </div>

            {error && <p className="error-message">{error}</p>}

            <main className="viewer-section">
                {isProcessing && <div className="spinner"></div>}
                {docInfo && !isProcessing && (
                    <div>
                        <h2>Document Processed: {docInfo.docId}</h2>
                        {renderPageImages()}
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;