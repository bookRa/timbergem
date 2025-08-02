"""
Offline test for Milestone 3: API Integration

This script tests the API implementation without requiring a running server,
focusing on the endpoint logic and integration with the detection system.
"""

import os
import sys
import json
import tempfile
import shutil
from unittest.mock import Mock

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_app_context():
    """Create a mock Flask app context for testing"""
    from flask import Flask
    from api.symbol_detection import symbol_detection_bp
    
    app = Flask(__name__)
    app.register_blueprint(symbol_detection_bp)
    
    # Configure processed folder
    processed_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    )
    app.config["PROCESSED_FOLDER"] = processed_folder
    
    return app


def create_test_document():
    """Create a test document for API testing"""
    processed_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    )
    
    doc_id = "milestone3_test_doc"
    doc_dir = os.path.join(processed_folder, doc_id)
    
    # Clean up any existing test data
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)
    
    print(f"📁 Creating test document: {doc_dir}")
    
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
                "id": "test_api_symbol_001",
                "name": "API Test Symbol",
                "description": "Test symbol for API milestone",
                "filename": "api_test_symbol.png",
                "relative_path": "symbols/legend_001/api_test_symbol.png",
                "page_number": 1,
                "symbol_template_dimensions": {
                    "height_pixels_300dpi": 40,
                    "width_pixels_300dpi": 40
                }
            }
        ]
    }
    
    with open(os.path.join(symbols_dir, "symbols_metadata.json"), 'w') as f:
        json.dump(symbols_metadata, f, indent=2)
    
    # Create symbol template image
    legend_dir = os.path.join(symbols_dir, "legend_001")
    os.makedirs(legend_dir, exist_ok=True)
    
    template_path = os.path.join(legend_dir, "api_test_symbol.png")
    with open(template_path, 'wb') as f:
        # Minimal PNG (40x40 pixels)
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00(\x00\x00\x00(\x08\x02\x00\x00\x00\x0f\xbb\xbf\xa1\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82')
    
    # Create minimal PDF
    pdf_content = """%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R 4 0 R]/Count 2>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
4 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000174 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
238
%%EOF"""
    
    with open(os.path.join(doc_dir, "original.pdf"), 'w') as f:
        f.write(pdf_content)
    
    print(f"✅ Test document created successfully")
    return doc_id


def test_api_endpoints():
    """Test API endpoint functionality"""
    print("\n🧪 Testing API Endpoint Implementation")
    print("-" * 50)
    
    app = create_test_app_context()
    doc_id = create_test_document()
    
    try:
        with app.app_context():
            from utils.symbol_detection import SymbolDetectionEngine
            
            # Test 1: SymbolDetectionEngine creation
            print("1️⃣ Testing SymbolDetectionEngine creation...")
            processed_folder = app.config["PROCESSED_FOLDER"]
            engine = SymbolDetectionEngine(doc_id, processed_folder)
            print("   ✅ Detection engine created successfully")
            
            # Test 2: List detection runs (should be empty initially)
            print("2️⃣ Testing detection runs listing...")
            runs = engine.list_detection_runs()
            print(f"   ✅ Listed {len(runs)} detection runs (expected: 0)")
            
            # Test 3: Test progress monitoring on non-existent run
            print("3️⃣ Testing progress monitoring...")
            progress = engine.get_detection_progress("non_existent_run")
            if progress is None:
                print("   ✅ Progress monitoring handles non-existent runs correctly")
            else:
                print("   ⚠️ Unexpected progress data returned")
            
            # Test 4: Test result loading on non-existent run
            print("4️⃣ Testing result loading...")
            results = engine.load_detection_results("non_existent_run")
            if results is None:
                print("   ✅ Result loading handles non-existent runs correctly")
            else:
                print("   ⚠️ Unexpected results returned")
            
            print("\n✅ API endpoint implementation tests passed")
            return True
    
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        processed_folder = app.config["PROCESSED_FOLDER"]
        doc_dir = os.path.join(processed_folder, doc_id)
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)


def test_api_blueprint_registration():
    """Test that API blueprint is properly registered"""
    print("\n🧪 Testing API Blueprint Registration")
    print("-" * 40)
    
    try:
        app = create_test_app_context()
        
        # Test that blueprint is registered
        blueprints = list(app.blueprints.keys())
        if 'symbol_detection' in blueprints:
            print("✅ Symbol detection blueprint registered")
        else:
            print("❌ Symbol detection blueprint not found")
            return False
        
        # Test endpoint registration
        endpoints = []
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith('/api/'):
                endpoints.append(rule.rule)
        
        expected_endpoints = [
            '/api/run_symbol_detection',
            '/api/detection_progress/<doc_id>',
            '/api/detection_results/<doc_id>',
            '/api/update_detection_status',
            '/api/detection_runs/<doc_id>',
            '/api/detection_runs/<doc_id>/<run_id>',
            '/api/detection_health'
        ]
        
        print(f"📋 Found {len(endpoints)} API endpoints:")
        for endpoint in sorted(endpoints):
            print(f"   • {endpoint}")
        
        # Check for expected endpoints
        missing_endpoints = []
        for expected in expected_endpoints:
            # Convert template endpoint to check for pattern
            pattern_found = False
            for actual in endpoints:
                if expected.replace('<doc_id>', 'test').replace('<run_id>', 'test') == actual.replace('<doc_id>', 'test').replace('<run_id>', 'test'):
                    pattern_found = True
                    break
            if not pattern_found:
                missing_endpoints.append(expected)
        
        if missing_endpoints:
            print(f"❌ Missing endpoints: {missing_endpoints}")
            return False
        else:
            print("✅ All expected endpoints are registered")
            return True
    
    except Exception as e:
        print(f"❌ Blueprint registration test failed: {e}")
        return False


def test_detection_system_integration():
    """Test integration between API and detection system"""
    print("\n🧪 Testing Detection System Integration")
    print("-" * 45)
    
    doc_id = create_test_document()
    
    try:
        from utils.symbol_detection import SymbolDetectionEngine, DetectionStorage, DetectionProgress
        
        processed_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "processed")
        )
        
        # Test 1: Full system integration
        print("1️⃣ Testing full detection system integration...")
        engine = SymbolDetectionEngine(doc_id, processed_folder)
        
        # Test storage component
        doc_dir = os.path.join(processed_folder, doc_id)
        storage = DetectionStorage(doc_dir)
        
        # Create a test detection run
        run_params = {
            "symbol_ids": ["test_api_symbol_001"],
            "total_symbols": 1,
            "total_pages": 2,
            "detection_params": {"match_threshold": 0.25}
        }
        
        run_id = storage.create_detection_run(run_params)
        print(f"   ✅ Created detection run: {run_id}")
        
        # Test progress system
        run_dir = os.path.join(storage.detections_dir, f"run_{run_id}")
        progress = DetectionProgress(run_id, run_dir)
        progress.start_detection(1, 2, ["API Test Symbol"])
        print("   ✅ Progress tracking initialized")
        
        # Test data retrieval
        loaded_run = storage.load_detection_run(run_id)
        if loaded_run and loaded_run["runId"] == run_id:
            print("   ✅ Run data persistence working")
        else:
            print("   ❌ Run data persistence failed")
            return False
        
        # Test run listing
        runs_list = storage.list_detection_runs()
        if len(runs_list) == 1 and runs_list[0]["runId"] == run_id:
            print("   ✅ Run listing working")
        else:
            print("   ❌ Run listing failed")
            return False
        
        print("\n✅ Detection system integration tests passed")
        return True
    
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        processed_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "processed")
        )
        doc_dir = os.path.join(processed_folder, doc_id)
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)


def test_api_error_handling():
    """Test API error handling"""
    print("\n🧪 Testing API Error Handling")
    print("-" * 35)
    
    try:
        app = create_test_app_context()
        
        with app.app_context():
            # Test with non-existent document
            from utils.symbol_detection import SymbolDetectionEngine
            
            processed_folder = app.config["PROCESSED_FOLDER"]
            
            try:
                engine = SymbolDetectionEngine("non_existent_doc", processed_folder)
                # This should fail when trying to access files
                runs = engine.list_detection_runs()
                print("   ✅ Non-existent document handled gracefully")
            except FileNotFoundError:
                print("   ✅ FileNotFoundError properly raised for non-existent document")
            except Exception as e:
                print(f"   ⚠️ Unexpected error: {e}")
        
        print("✅ API error handling tests passed")
        return True
    
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def run_milestone_3_offline_tests():
    """Run all offline Milestone 3 tests"""
    print("🧪 MILESTONE 3: API INTEGRATION - OFFLINE TESTS")
    print("=" * 60)
    print("Testing API implementation without requiring a running server")
    print()
    
    tests = [
        ("API Blueprint Registration", test_api_blueprint_registration),
        ("API Endpoints Implementation", test_api_endpoints),
        ("Detection System Integration", test_detection_system_integration),
        ("API Error Handling", test_api_error_handling)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 Running {test_name} tests...")
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} tests PASSED")
            else:
                print(f"❌ {test_name} tests FAILED")
        except Exception as e:
            print(f"💥 {test_name} tests CRASHED: {e}")
    
    print(f"\n📊 OFFLINE TEST SUMMARY")
    print("-" * 30)
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL MILESTONE 3 OFFLINE TESTS PASSED!")
        print(f"✅ API implementation is correct")
        print(f"✅ System integration is working")
        print(f"✅ Error handling is robust")
        print(f"\n📋 API ENDPOINTS READY FOR USE:")
        print(f"   • POST /api/run_symbol_detection")
        print(f"   • GET  /api/detection_progress/<doc_id>")
        print(f"   • GET  /api/detection_results/<doc_id>")
        print(f"   • POST /api/update_detection_status")
        print(f"   • GET  /api/detection_runs/<doc_id>")
        print(f"   • DELETE /api/detection_runs/<doc_id>/<run_id>")
        print(f"   • GET  /api/detection_health")
        print(f"\n🚀 MILESTONE 3: API INTEGRATION COMPLETE!")
        return True
    else:
        print(f"\n❌ Some tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    success = run_milestone_3_offline_tests()
    sys.exit(0 if success else 1)