import os
import asyncio
import json
import time
import random
from flask import Blueprint, request, jsonify, Response
from utils.page_to_html_pipeline import PageToHTMLPipeline, PageToHTMLConfig


# Create blueprint for page-to-HTML endpoints
page_to_html_bp = Blueprint('page_to_html', __name__)


@page_to_html_bp.route("/api/simulate_pdf_to_html/<doc_id>", methods=["GET", "OPTIONS"])
def simulate_pdf_to_html(doc_id):
    """
    Simulate the PDF-to-HTML pipeline using pre-existing results.
    This endpoint streams results in real-time to simulate async processing.
    """
    print(f"\n--- Simulating PDF-to-HTML pipeline for doc: {doc_id} ---")
    
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for simulation")
        return "", 200
    
    def generate_simulation():
        try:
            # Check if document exists
            processed_folder = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
            )
            doc_dir = os.path.join(processed_folder, doc_id)
            
            if not os.path.exists(doc_dir):
                yield f"data: {json.dumps({'error': f'Document {doc_id} not found'})}\n\n"
                return
            
            # Load existing results to determine page count
            results_file = os.path.join(doc_dir, "page_to_html_results.json")
            if not os.path.exists(results_file):
                yield f"data: {json.dumps({'error': f'No results found for document {doc_id}'})}\n\n"
                return
                
            with open(results_file, 'r') as f:
                existing_results = json.load(f)
            
            total_pages = existing_results.get('pdf_processing', {}).get('totalPages', 0)
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': f'Starting simulation for {total_pages} pages'})}\n\n"
            time.sleep(0.5)
            
            # Simulate async processing - start all pages with random completion times
            page_completion_times = {}
            start_time = time.time()
            
            # Generate random completion times for each page (3s to 8s)
            for page_num in range(1, total_pages + 1):
                completion_time = random.uniform(3, 8)
                page_completion_times[page_num] = start_time + completion_time
                
                yield f"data: {json.dumps({'type': 'page_start', 'page': page_num, 'estimated_time': completion_time})}\n\n"
            
            # Sort pages by completion time to process them in the order they "finish"
            sorted_pages = sorted(page_completion_times.items(), key=lambda x: x[1])
            
            print(f"   📋 Page completion order: {[page for page, _ in sorted_pages]}")
            
            # Process pages as they "complete" in async order
            for page_num, completion_time in sorted_pages:
                # Wait until this page should be "complete"
                current_time = time.time()
                wait_time = completion_time - current_time
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # Check if HTML file exists
                html_file = os.path.join(doc_dir, f"page_{page_num}", f"page_{page_num}.html")
                if os.path.exists(html_file):
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    actual_processing_time = time.time() - start_time
                    yield f"data: {json.dumps({
                        'type': 'page_complete', 
                        'page': page_num, 
                        'html_content': html_content,
                        'processing_time': actual_processing_time
                    })}\n\n"
                else:
                    yield f"data: {json.dumps({
                        'type': 'page_error', 
                        'page': page_num, 
                        'error': f'HTML file not found for page {page_num}'
                    })}\n\n"
            
            # Send completion status
            yield f"data: {json.dumps({'type': 'complete', 'total_pages': total_pages})}\n\n"
            
        except Exception as e:
            print(f"Error in simulation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(
        generate_simulation(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
        }
    )


@page_to_html_bp.route("/api/process_pdf_to_html", methods=["POST", "OPTIONS"])
def process_pdf_to_html():
    """
    Process a PDF document through the page-to-HTML pipeline.
    Supports both testing mode and production mode with configurable LLM providers.
    """
    print("\n--- Received request on /api/process_pdf_to_html ---")
    
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        print("Handling preflight OPTIONS request for page-to-HTML")
        return "", 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        # Get required parameters
        doc_id = data.get("docId")
        if not doc_id:
            return jsonify({"error": "Document ID is required"}), 400
        
        # Get configuration parameters
        config_data = data.get("config", {})
        
        # Auto-load API keys from environment variables
        gemini_api_key = config_data.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        openai_api_key = config_data.get("openai_api_key") or os.getenv("OPENAI_API_KEY")  
        anthropic_api_key = config_data.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
        
        config = PageToHTMLConfig(
            llm_provider=config_data.get("llm_provider", "mock"),
            llm_model=config_data.get("llm_model"),
            dpi=config_data.get("dpi", 200),
            high_res_dpi=config_data.get("high_res_dpi", 300),
            max_concurrent_requests=config_data.get("max_concurrent_requests", 7),
            gemini_api_key=gemini_api_key,
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key
        )
        
        print(f"🚀 Processing PDF to HTML for document: {doc_id}")
        print(f"   Config: {config.llm_provider} provider")
        
        # Determine paths
        processed_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
        )
        
        doc_dir = os.path.join(processed_folder, doc_id)
        
        # Check if document exists
        if not os.path.exists(doc_dir):
            return jsonify({"error": f"Document {doc_id} not found"}), 404
        
        # Check for original PDF
        original_pdf_path = os.path.join(doc_dir, "original.pdf")
        if not os.path.exists(original_pdf_path):
            return jsonify({"error": f"Original PDF not found for document {doc_id}"}), 404
        
        # Run the pipeline
        pipeline = PageToHTMLPipeline(config)
        
        # Since Flask doesn't natively support async, we need to run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                pipeline.process_pdf_to_html(original_pdf_path, doc_dir, doc_id)
            )
        finally:
            loop.close()
        
        print(f"✅ Pipeline processing complete for {doc_id}")
        
        return jsonify({
            "message": "PDF processed to HTML successfully",
            "docId": doc_id,
            "results": results
        }), 200
        
    except Exception as e:
        print(f"❌ ERROR: Failed to process PDF to HTML: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@page_to_html_bp.route("/api/load_html_results/<doc_id>", methods=["GET"])
def load_html_results(doc_id):
    """
    Load the results from a previous page-to-HTML processing run.
    """
    print(f"\n--- Loading HTML results for document: {doc_id} ---")
    
    try:
        processed_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
        )
        
        doc_dir = os.path.join(processed_folder, doc_id)
        results_file = os.path.join(doc_dir, "page_to_html_results.json")
        
        if not os.path.exists(results_file):
            print(f"   ⚠️  No HTML results found for document {doc_id}")
            return jsonify({
                "docId": doc_id,
                "results": None,
                "message": "No HTML processing results found"
            }), 200
        
        import json
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        print(f"   ✅ Loaded HTML results for {doc_id}")
        
        return jsonify({
            "docId": doc_id,
            "results": results
        }), 200
        
    except Exception as e:
        print(f"❌ ERROR: Failed to load HTML results: {e}")
        return jsonify({"error": str(e)}), 500


@page_to_html_bp.route("/api/get_page_html/<doc_id>/<int:page_number>", methods=["GET"])
def get_page_html(doc_id, page_number):
    """
    Get the HTML content for a specific page.
    """
    print(f"\n--- Getting HTML for document {doc_id}, page {page_number} ---")
    
    try:
        processed_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
        )
        
        doc_dir = os.path.join(processed_folder, doc_id)
        page_dir = os.path.join(doc_dir, f"page_{page_number}")
        html_file = os.path.join(page_dir, f"page_{page_number}.html")
        
        if not os.path.exists(html_file):
            return jsonify({
                "error": f"HTML file not found for document {doc_id}, page {page_number}"
            }), 404
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"   ✅ Loaded HTML content for page {page_number}")
        
        return jsonify({
            "docId": doc_id,
            "pageNumber": page_number,
            "htmlContent": html_content,
            "htmlFilePath": html_file
        }), 200
        
    except Exception as e:
        print(f"❌ ERROR: Failed to get page HTML: {e}")
        return jsonify({"error": str(e)}), 500 