#!/usr/bin/env python3
"""
Test script for the page-to-HTML API endpoints.
"""

import requests
import json
import sys


def test_process_pdf_to_html():
    """Test the /api/process_pdf_to_html endpoint."""
    
    print("🧪 Testing /api/process_pdf_to_html endpoint...")
    
    # Test data
    test_data = {
        "docId": "TEST",
        "config": {
            "llm_provider": "mock",
            "testing_mode": True,
            "dpi": 200,
            "high_res_dpi": 300,
            "max_concurrent_requests": 3
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:5001/api/process_pdf_to_html",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"   Message: {result['message']}")
            print(f"   Doc ID: {result['docId']}")
            
            # Print summary from results
            html_gen = result['results']['html_generation']
            print(f"   Total pages: {html_gen['total_pages']}")
            print(f"   Successful pages: {html_gen['successful_pages']}")
            print(f"   Failed pages: {html_gen['failed_pages']}")
            print(f"   Testing mode: {html_gen['testing_mode']}")
            
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Flask is running on port 5001.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_load_html_results():
    """Test the /api/load_html_results endpoint."""
    
    print("\n🧪 Testing /api/load_html_results endpoint...")
    
    try:
        response = requests.get("http://localhost:5001/api/load_html_results/TEST")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"   Doc ID: {result['docId']}")
            
            if result['results']:
                html_gen = result['results']['html_generation']
                print(f"   Total pages: {html_gen['total_pages']}")
                print(f"   Successful pages: {html_gen['successful_pages']}")
            else:
                print(f"   Message: {result['message']}")
            
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Flask is running on port 5001.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_get_page_html():
    """Test the /api/get_page_html endpoint."""
    
    print("\n🧪 Testing /api/get_page_html endpoint...")
    
    try:
        response = requests.get("http://localhost:5001/api/get_page_html/TEST/1")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"   Doc ID: {result['docId']}")
            print(f"   Page Number: {result['pageNumber']}")
            print(f"   HTML Content Length: {len(result['htmlContent'])} characters")
            print(f"   HTML File Path: {result['htmlFilePath']}")
            
            # Show a snippet of the HTML
            html_snippet = result['htmlContent'][:200] + "..." if len(result['htmlContent']) > 200 else result['htmlContent']
            print(f"   HTML Snippet: {html_snippet}")
            
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Flask is running on port 5001.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    
    print("🚀 Starting API tests for page-to-HTML endpoints")
    print("📋 Make sure the Flask server is running (python app.py)")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Process PDF to HTML
    if test_process_pdf_to_html():
        success_count += 1
    
    # Test 2: Load HTML results
    if test_load_html_results():
        success_count += 1
    
    # Test 3: Get page HTML
    if test_get_page_html():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 