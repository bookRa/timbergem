# PDF-to-HTML Pipeline Demo

This demo showcases the PDF-to-HTML pipeline integration with the TimberGem frontend, using a "testing mode" that simulates the async processing without making actual LLM calls.

## 🚀 Quick Start

Run the demo with a single command:

```bash
./run_demo.sh
```

This will:
- Start the Flask backend server on port 5001
- Start the Vite frontend server on port 5173
- Open your browser to the demo (or visit http://localhost:5173)

## 🎯 Demo Features

### Testing Mode
- **Auto-loaded TEST document**: The app automatically loads a pre-processed TEST document
- **No LLM calls**: Uses existing HTML artifacts from `data/processed/TEST/`
- **Realistic timing**: Simulates 3-8 seconds per page processing time
- **Real-time streaming**: Uses Server-Sent Events (SSE) to stream progress updates

### User Interface
- **PDF-to-HTML Pipeline Tab**: New tab dedicated to visualizing the pipeline
- **Auto Mode**: Toggle to automatically start simulation when document loads
- **Real-time Progress**: See processing progress with estimated completion times
- **Live HTML Preview**: View generated HTML pages as they complete
- **Page Navigation**: Click through completed pages to see their output

## 📖 How to Use

1. **Start the demo** using `./run_demo.sh`
2. **Navigate to the frontend** at http://localhost:5173
3. **Observe the testing mode**: The app loads with "🧪 Testing Mode ON"
4. **Go to PDF-to-HTML tab**: Should be the active tab by default
5. **Enable Auto Mode**: Click "🤖 Auto Mode ON" to start simulation automatically
6. **Watch the pipeline**: Observe real-time processing of each page
7. **View results**: Click on completed pages to see their HTML output

## 🏗️ Architecture

### Backend (`/api/simulate_pdf_to_html/<doc_id>`)
- **Server-Sent Events**: Streams processing updates in real-time
- **Pre-existing artifacts**: Uses HTML files from `data/processed/TEST/`
- **Random timing**: Simulates realistic async processing delays
- **Progress tracking**: Sends start/complete/error events for each page

### Frontend Components
- **PDFToHTMLTab**: Main component managing the pipeline UI
- **EventSource**: Handles SSE connection for real-time updates
- **State management**: Tracks processing status, completed pages, and HTML content
- **Auto-upload simulation**: Simulates document upload for testing

### Testing Mode Features
- **No file upload required**: Auto-loads TEST document
- **Instant setup**: No manual configuration needed
- **Repeatable**: Can restart simulation multiple times
- **Safe**: No API costs or external dependencies

## 🎮 Interactive Elements

### Controls
- **Testing Mode Toggle**: Switch between testing and production modes
- **Auto Mode**: Automatically start simulation when document loads
- **Start/Stop**: Manual control over simulation
- **Page Selection**: Click to view specific page HTML

### Visual Feedback
- **Progress bars**: Show processing progress for current page
- **Status messages**: Real-time updates on pipeline status
- **Completion indicators**: Visual confirmation when pages finish
- **HTML iframe**: Live preview of generated HTML content

## 🔧 Technical Details

### File Structure
```
data/processed/TEST/
├── original.pdf                    # Source PDF
├── page_to_html_results.json      # Processing metadata
├── page_1/
│   ├── page_1.html                # Generated HTML ← Used by demo
│   ├── page_1_pixmap.png          # Page image
│   └── page_1_text.txt            # Extracted text
├── page_2/
│   └── ...
└── ...
```

### Event Types
The simulation streams these event types:
- `status`: General pipeline status updates
- `page_start`: When page processing begins
- `page_complete`: When page HTML is ready
- `page_error`: If page processing fails
- `complete`: When entire pipeline finishes
- `error`: If pipeline fails

### Timing Configuration
- **Processing time**: 3-8 seconds per page (randomized)
- **Total demo time**: ~30-60 seconds for 7 pages
- **Update frequency**: Real-time via SSE

## 🎯 Next Steps

After experiencing the demo, you can:

1. **Switch to production mode**: Toggle off Testing Mode to upload real PDFs
2. **Integrate with other tabs**: Use processed HTML in annotation workflows
3. **Customize timing**: Adjust simulation speeds in `backend/api/page_to_html.py`
4. **Add real LLM calls**: Configure API keys for actual processing
5. **Extend UI**: Add more visualization features or processing options

## 🛠️ Development

### Modifying the Demo
- **Backend simulation**: Edit `backend/api/page_to_html.py`
- **Frontend UI**: Modify `frontend/src/components/PDFToHTMLTab.jsx`
- **Styling**: Update CSS in `frontend/src/App.css`
- **Timing**: Adjust processing delays in the simulation loop

### Adding Features
- **WebSocket support**: Replace SSE with bi-directional communication
- **Progress persistence**: Save progress across browser refreshes
- **Error simulation**: Add failure scenarios for testing
- **Multiple documents**: Support switching between different test documents

## 📚 Related Documentation

- [Backend PDF-to-HTML Guide](backend/PAGE_TO_HTML_GUIDE.md)
- [Pull Request #3](https://github.com/bookRa/timbergem/pull/3) - Original implementation
- [Frontend Component Documentation](frontend/src/components/)

---

**Enjoy exploring the PDF-to-HTML pipeline!** 🎉 