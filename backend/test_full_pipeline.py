#!/usr/bin/env python3
"""
Test script to run the full page-to-HTML pipeline with actual Gemini API calls.
This script demonstrates how to configure the pipeline for production use with
higher concurrency.
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.page_to_html_pipeline import PageToHTMLPipeline, PageToHTMLConfig


async def main():
    """Run the full pipeline test with Gemini API calls."""
    
    # Load environment variables
    load_dotenv()
    
    # Configuration for production run with higher concurrency
    config = PageToHTMLConfig(
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        testing_mode=False,  # 🚨 This will make actual API calls!
        dpi=200,
        high_res_dpi=300,
        max_concurrent_requests=7,  # 🚀 Increased from 3 to 7
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    # Document configuration
    doc_id = "TEST"
    processed_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    )
    doc_dir = os.path.join(processed_folder, doc_id)
    original_pdf_path = os.path.join(doc_dir, "original.pdf")
    
    # Verify setup
    print("🔍 Pre-flight checks:")
    print(f"   API Key configured: {'✅' if config.gemini_api_key else '❌'}")
    print(f"   Document directory: {doc_dir}")
    print(f"   Original PDF: {'✅' if os.path.exists(original_pdf_path) else '❌'}")
    print(f"   Concurrent requests: {config.max_concurrent_requests}")
    print(f"   Testing mode: {'✅' if config.testing_mode else '❌ PRODUCTION MODE'}")
    
    if not config.gemini_api_key:
        print("\n❌ ERROR: GEMINI_API_KEY not found in environment variables")
        print("   Please create a .env file with: GEMINI_API_KEY=your_key_here")
        return
    
    if not os.path.exists(original_pdf_path):
        print(f"\n❌ ERROR: Original PDF not found at {original_pdf_path}")
        print("   Please ensure the TEST document is properly set up")
        return
    
    print(f"\n🚀 Starting PRODUCTION pipeline run...")
    print(f"   This will make actual API calls to Gemini!")
    print(f"   Provider: {config.llm_provider}")
    print(f"   Model: {config.llm_model}")
    print(f"   Max concurrent requests: {config.max_concurrent_requests}")
    
    # Initialize and run pipeline
    pipeline = PageToHTMLPipeline(config)
    
    try:
        results = await pipeline.process_pdf_to_html(
            pdf_path=original_pdf_path,
            output_dir=doc_dir,
            doc_id=doc_id
        )
        
        # Print summary
        html_gen = results["html_generation"]
        print(f"\n✅ Pipeline completed successfully!")
        print(f"   Total pages: {html_gen['total_pages']}")
        print(f"   Successful: {html_gen['successful_pages']}")
        print(f"   Failed: {html_gen['failed_pages']}")
        print(f"   Total tokens: {html_gen['total_tokens_used']}")
        
        # Show per-page results
        print(f"\n📊 Per-page results:")
        for page_result in html_gen["results"]:
            status = "✅" if page_result["success"] else "❌"
            page_num = page_result["page_number"]
            time_taken = page_result["processing_time"]
            
            if page_result["success"]:
                html_length = page_result["html_content_length"]
                print(f"   {status} Page {page_num}: {html_length} chars HTML ({time_taken:.1f}s)")
            else:
                error = page_result["error_message"]
                print(f"   {status} Page {page_num}: {error} ({time_taken:.1f}s)")
        
        # Show file locations
        print(f"\n📁 Generated files:")
        print(f"   Results JSON: {os.path.join(doc_dir, 'page_to_html_results.json')}")
        
        for i in range(1, html_gen['total_pages'] + 1):
            page_dir = os.path.join(doc_dir, f"page_{i}")
            html_file = os.path.join(page_dir, f"page_{i}.html")
            raw_file = os.path.join(page_dir, f"page_{i}_raw_response.json")
            
            html_exists = "✅" if os.path.exists(html_file) else "❌"
            raw_exists = "✅" if os.path.exists(raw_file) else "❌"
            
            print(f"   Page {i}: HTML {html_exists} | Raw response {raw_exists}")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 