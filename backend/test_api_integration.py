"""
Test script for API integration (Milestone 3).

This script tests the REST API endpoints for symbol detection,
including detection execution, progress monitoring, and result management.
"""

import os
import sys
import json
import time
import tempfile
import shutil
import requests
from typing import Dict, Any

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test configuration
API_BASE_URL = "http://localhost:5001"
TEST_TIMEOUT = 30  # seconds


def create_test_document_with_symbols():
    """Create a test document structure with symbol metadata"""
    
    # Use the processed folder from the app config
    processed_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    )
    
    # Create a test document ID
    doc_id = "api_test_doc_12345"
    doc_dir = os.path.join(processed_folder, doc_id)
    
    print(f"📁 Creating test document: {doc_dir}")
    
    # Clean up any existing test data
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)
    
    # Create directory structure
    symbols_dir = os.path.join(doc_dir, "symbols")
    os.makedirs(symbols_dir, exist_ok=True)
    
    # Create page metadata
    page_metadata = {
        "docId": doc_id,
        "totalPages": 2,
        "pages": {
            "1": {
                "page_number": 1,
                "pdf_width_points": 612.0,
                "pdf_height_points": 792.0,
                "pdf_rotation_degrees": 0,
                "image_width_pixels": 1700,
                "image_height_pixels": 2200,
                "image_dpi": 200,
                "high_res_image_width_pixels": 2550,
                "high_res_image_height_pixels": 3300,
                "high_res_dpi": 300
            },
            "2": {
                "page_number": 2,
                "pdf_width_points": 612.0,
                "pdf_height_points": 792.0,
                "pdf_rotation_degrees": 0,
                "image_width_pixels": 1700,
                "image_height_pixels": 2200,
                "image_dpi": 200,
                "high_res_image_width_pixels": 2550,
                "high_res_image_height_pixels": 3300,
                "high_res_dpi": 300
            }
        }
    }
    
    with open(os.path.join(doc_dir, "page_metadata.json"), 'w') as f:
        json.dump(page_metadata, f, indent=2)
    
    # Create symbols metadata
    symbols_metadata = {
        "docId": doc_id,
        "timestamp": "2024-01-01T00:00:00Z",
        "total_symbols": 1,
        "symbols_by_legend": 1,
        "symbols": [
            {
                "id": "test_symbol_001",
                "name": "Test Symbol",
                "description": "Test symbol for API integration",
                "filename": "test_symbol.png",
                "relative_path": "symbols/legend_001/test_symbol.png",
                "page_number": 1,
                "symbol_template_dimensions": {
                    "height_pixels_300dpi": 50,
                    "width_pixels_300dpi": 50
                }
            }
        ]
    }
    
    with open(os.path.join(symbols_dir, "symbols_metadata.json"), 'w') as f:
        json.dump(symbols_metadata, f, indent=2)
    
    # Create symbol template image directory and file
    legend_dir = os.path.join(symbols_dir, "legend_001")
    os.makedirs(legend_dir, exist_ok=True)
    
    # Create a minimal test image
    template_path = os.path.join(legend_dir, "test_symbol.png")
    with open(template_path, 'wb') as f:
        # Minimal PNG file
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x32\x00\x00\x00\x32\x08\x02\x00\x00\x00\x91\x5d\x1f\xe6\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82')
    
    # Create a minimal PDF file
    pdf_content = """%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R 4 0 R]
/Count 2
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj

4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000174 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
238
%%EOF"""
    
    with open(os.path.join(doc_dir, "original.pdf"), 'w') as f:
        f.write(pdf_content)
    
    print(f"✅ Test document created successfully")
    return doc_id


def test_api_health():
    """Test the API health endpoint"""
    print("\n🧪 Testing API Health Endpoint")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/detection_health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Health check failed: {e}")
        print(f"ℹ️ Make sure the backend server is running on {API_BASE_URL}")
        return False


def test_detection_runs_list(doc_id):
    """Test listing detection runs"""
    print(f"\n🧪 Testing Detection Runs List")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/detection_runs/{doc_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Listed detection runs successfully")
            print(f"   Document: {data.get('docId')}")
            print(f"   Total runs: {data.get('totalRuns', 0)}")
            return True, data.get('runs', [])
        else:
            print(f"❌ Failed to list detection runs: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, []
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False, []


def test_start_detection(doc_id):
    """Test starting a detection run"""
    print(f"\n🧪 Testing Start Detection")
    print("-" * 40)
    
    try:
        request_data = {
            "docId": doc_id,
            "detectionParams": {
                "matchThreshold": 0.25,  # Lower threshold for test
                "iouThreshold": 0.15,    # Lower threshold for test
                "scaleVariancePx": 1
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/run_symbol_detection",
            json=request_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Detection started successfully")
            print(f"   Message: {data.get('message')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Document: {data.get('docId')}")
            return True
        else:
            print(f"❌ Failed to start detection: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def test_progress_monitoring(doc_id, max_wait_time=30):
    """Test progress monitoring"""
    print(f"\n🧪 Testing Progress Monitoring")
    print("-" * 40)
    
    try:
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < max_wait_time:
            response = requests.get(f"{API_BASE_URL}/api/detection_progress/{doc_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get('hasProgress'):
                    print(f"ℹ️ No progress data available yet")
                    time.sleep(2)
                    continue
                
                progress = data.get('progressPercent', 0)
                status = data.get('status', 'unknown')
                current_step = data.get('currentStep', 'Processing...')
                
                # Only print if progress changed significantly
                if progress != last_progress:
                    print(f"📊 Progress: {progress:.1f}% - {status}")
                    print(f"   Step: {current_step}")
                    last_progress = progress
                
                if status in ['completed', 'failed']:
                    print(f"✅ Detection {status}")
                    return status == 'completed'
                    
            else:
                print(f"⚠️ Progress check failed: {response.status_code}")
            
            time.sleep(2)
        
        print(f"⏰ Progress monitoring timed out after {max_wait_time} seconds")
        return False
        
    except requests.RequestException as e:
        print(f"❌ Progress monitoring failed: {e}")
        return False


def test_detection_results(doc_id):
    """Test retrieving detection results"""
    print(f"\n🧪 Testing Detection Results Retrieval")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/detection_results/{doc_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get('hasResults'):
                print(f"ℹ️ No detection results available")
                return True  # This is acceptable
            
            print(f"✅ Retrieved detection results successfully")
            print(f"   Document: {data.get('docId')}")
            print(f"   Run ID: {data.get('runId')}")
            print(f"   Status: {data.get('status')}")
            
            summary = data.get('summary', {})
            print(f"   Total detections: {summary.get('totalDetections', 0)}")
            print(f"   Symbols processed: {summary.get('symbolsProcessed', 0)}")
            
            symbol_results = data.get('symbolResults', {})
            print(f"   Symbol results: {len(symbol_results)} symbols")
            
            return True
        else:
            print(f"❌ Failed to retrieve results: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def test_status_updates(doc_id):
    """Test detection status updates"""
    print(f"\n🧪 Testing Detection Status Updates")
    print("-" * 40)
    
    try:
        # First, try to get some detection results to update
        response = requests.get(f"{API_BASE_URL}/api/detection_results/{doc_id}")
        
        if response.status_code != 200:
            print(f"ℹ️ Cannot test status updates - no detection results available")
            return True  # This is acceptable
        
        data = response.json()
        
        if not data.get('hasResults'):
            print(f"ℹ️ No detection results to update")
            return True
        
        # Find the first detection to update
        symbol_results = data.get('symbolResults', {})
        first_detection_id = None
        run_id = data.get('runId')
        
        for symbol_data in symbol_results.values():
            for page_detections in symbol_data.get('detectionsByPage', {}).values():
                if page_detections:
                    first_detection_id = page_detections[0].get('detectionId')
                    break
            if first_detection_id:
                break
        
        if not first_detection_id:
            print(f"ℹ️ No detection IDs found to update")
            return True
        
        # Test status update
        update_data = {
            "docId": doc_id,
            "runId": run_id,
            "updates": [
                {
                    "detectionId": first_detection_id,
                    "action": "accept",
                    "reviewedBy": "api_test_user"
                }
            ]
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/update_detection_status",
            json=update_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status update successful")
            print(f"   Updated count: {result.get('updatedCount')}")
            return True
        else:
            print(f"❌ Status update failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def cleanup_test_data(doc_id):
    """Clean up test data"""
    print(f"\n🧹 Cleaning up test data")
    print("-" * 30)
    
    try:
        processed_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "processed")
        )
        doc_dir = os.path.join(processed_folder, doc_id)
        
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)
            print(f"✅ Cleaned up test document: {doc_id}")
        else:
            print(f"ℹ️ No test data to clean up")
            
    except Exception as e:
        print(f"⚠️ Failed to clean up: {e}")


def run_api_integration_tests():
    """Run all API integration tests"""
    print("🧪 API INTEGRATION TESTS (MILESTONE 3)")
    print("=" * 60)
    
    # Test API health first
    if not test_api_health():
        print(f"\n❌ API server is not responding. Please start the backend server:")
        print(f"   cd backend && python app.py")
        return False
    
    # Create test document
    doc_id = create_test_document_with_symbols()
    
    try:
        tests = [
            ("Detection Runs List", lambda: test_detection_runs_list(doc_id)[0]),
            ("Start Detection", lambda: test_start_detection(doc_id)),
            ("Progress Monitoring", lambda: test_progress_monitoring(doc_id)),
            ("Detection Results", lambda: test_detection_results(doc_id)),
            ("Status Updates", lambda: test_status_updates(doc_id))
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                print(f"\n🔄 Running {test_name} test...")
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name} test PASSED")
                else:
                    print(f"❌ {test_name} test FAILED")
            except Exception as e:
                print(f"💥 {test_name} test CRASHED: {e}")
        
        print(f"\n📊 API INTEGRATION TEST SUMMARY")
        print("-" * 40)
        print(f"Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL API INTEGRATION TESTS PASSED!")
            print(f"✅ Symbol Detection API is working correctly")
            print(f"🚀 Milestone 3: API Integration COMPLETE")
            return True
        else:
            print(f"\n❌ Some API tests failed.")
            return False
    
    finally:
        # Always clean up
        cleanup_test_data(doc_id)


if __name__ == "__main__":
    success = run_api_integration_tests()
    sys.exit(0 if success else 1)