#!/usr/bin/env python3
"""
Test script to demonstrate calling the page-to-HTML API with higher concurrency.
This shows how to configure the pipeline through the API endpoint.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_with_concurrent_requests():
    """Test the API endpoint with 7 concurrent requests configured."""
    
    # API endpoint
    api_url = "http://localhost:5000/api/process_pdf_to_html"
    
    # Configuration with 7 concurrent requests
    config = {
        "docId": "TEST",
        "config": {
            "llm_provider": "gemini",
            "llm_model": "gemini-2.5-pro",
            "testing_mode": False,  # 🚨 This will make actual API calls!
            "dpi": 200,
            "high_res_dpi": 300,
            "max_concurrent_requests": 7,  # 🚀 Increased from 3 to 7
            "gemini_api_key": os.getenv("GEMINI_API_KEY")
        }
    }
    
    print("🔍 API Test Configuration:")
    print(f"   Endpoint: {api_url}")
    print(f"   Document ID: {config['docId']}")
    print(f"   Provider: {config['config']['llm_provider']}")
    print(f"   Model: {config['config']['llm_model']}")
    print(f"   Max concurrent requests: {config['config']['max_concurrent_requests']}")
    print(f"   Testing mode: {'✅' if config['config']['testing_mode'] else '❌ PRODUCTION MODE'}")
    print(f"   API Key configured: {'✅' if config['config']['gemini_api_key'] else '❌'}")
    
    if not config['config']['gemini_api_key']:
        print("\n❌ ERROR: GEMINI_API_KEY not found in environment variables")
        print("   Please create a .env file with: GEMINI_API_KEY=your_key_here")
        return
    
    print(f"\n🚀 Making API request...")
    print(f"   This will make actual API calls to Gemini with 7 concurrent requests!")
    
    try:
        # Make the API request
        response = requests.post(
            api_url,
            json=config,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout for processing
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Print summary
            html_gen = result["results"]["html_generation"]
            print(f"\n✅ API request completed successfully!")
            print(f"   Total pages: {html_gen['total_pages']}")
            print(f"   Successful: {html_gen['successful_pages']}")
            print(f"   Failed: {html_gen['failed_pages']}")
            print(f"   Total tokens: {html_gen['total_tokens_used']}")
            print(f"   Provider: {html_gen['provider']}")
            
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
            
            # Show configuration that was used
            pipeline_config = result["results"]["pipeline_metadata"]["config"]
            print(f"\n⚙️  Pipeline configuration used:")
            print(f"   Provider: {pipeline_config['llm_provider']}")
            print(f"   Model: {pipeline_config['llm_model']}")
            print(f"   Testing mode: {pipeline_config['testing_mode']}")
            print(f"   High-res DPI: {pipeline_config['high_res_dpi']}")
            
        else:
            print(f"\n❌ API request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"\n⏰ API request timed out after 5 minutes")
        print(f"   This might be normal for large documents with many pages")
        
    except Exception as e:
        print(f"\n❌ API request failed with error: {e}")


def test_load_results():
    """Test loading the results from a previous run."""
    
    api_url = "http://localhost:5000/api/load_html_results/TEST"
    
    print(f"\n🔍 Testing results loading...")
    print(f"   Endpoint: {api_url}")
    
    try:
        response = requests.get(api_url)
        
        if response.status_code == 200:
            result = response.json()
            
            if result["results"]:
                html_gen = result["results"]["html_generation"]
                print(f"   ✅ Previous results found!")
                print(f"   Total pages: {html_gen['total_pages']}")
                print(f"   Successful: {html_gen['successful_pages']}")
                print(f"   Provider: {html_gen['provider']}")
            else:
                print(f"   ⚠️  No previous results found")
                
        else:
            print(f"   ❌ Failed to load results: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error loading results: {e}")


def test_get_page_html():
    """Test getting HTML for a specific page."""
    
    page_num = 1
    api_url = f"http://localhost:5000/api/get_page_html/TEST/{page_num}"
    
    print(f"\n🔍 Testing page HTML retrieval...")
    print(f"   Endpoint: {api_url}")
    
    try:
        response = requests.get(api_url)
        
        if response.status_code == 200:
            result = response.json()
            html_content = result["htmlContent"]
            
            print(f"   ✅ Page {page_num} HTML retrieved!")
            print(f"   HTML length: {len(html_content)} characters")
            print(f"   File path: {result['htmlFilePath']}")
            
            # Show a preview of the HTML
            preview = html_content[:200] + "..." if len(html_content) > 200 else html_content
            print(f"   Preview: {preview}")
            
        else:
            print(f"   ❌ Failed to get page HTML: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error getting page HTML: {e}")


if __name__ == "__main__":
    print("🧪 Testing page-to-HTML API with concurrent requests")
    print("=" * 60)
    
    # Test the main processing endpoint
    test_api_with_concurrent_requests()
    
    # Test loading results
    test_load_results()
    
    # Test getting specific page HTML
    test_get_page_html()
    
    print("\n✅ API testing complete!") 