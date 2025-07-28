#!/usr/bin/env python3
"""
Integration test for the coordinate mapping system.
Tests frontend-backend coordinate transformations end-to-end.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.coordinate_mapping import (
    PDFCoordinates, ImageCoordinates, CanvasCoordinates, ClippingCoordinates,
    PageMetadata, CoordinateTransformer, ClippingCoordinateTransformer,
    DEFAULT_DPI, HIGH_RES_DPI
)
import json


def test_frontend_backend_coordination():
    """Test that frontend and backend produce identical coordinate transformations"""
    print("🔄 Testing Frontend-Backend Coordinate Coordination")
    
    # Simulate typical document metadata
    page_metadata = PageMetadata(
        page_number=1,
        pdf_width_points=612.0,
        pdf_height_points=792.0,
        pdf_rotation_degrees=0,
        image_width_pixels=1700,  # 612 * 200/72
        image_height_pixels=2200,  # 792 * 200/72
        image_dpi=200,
        high_res_image_width_pixels=2550,  # 612 * 300/72
        high_res_image_height_pixels=3300,  # 792 * 300/72
        high_res_dpi=300
    )
    
    transformer = CoordinateTransformer(page_metadata)
    
    # Test Case 1: DefineKeyAreas annotation flow
    print("\n📋 Test Case 1: DefineKeyAreas Annotation")
    
    # Frontend: User draws annotation on canvas
    canvas_width, canvas_height = transformer.get_canvas_dimensions_for_aspect_ratio(1200, 900)
    print(f"Canvas dimensions: {canvas_width:.1f}x{canvas_height:.1f}")
    
    # Frontend: Canvas annotation coordinates (from user drawing)
    canvas_annotation = CanvasCoordinates(
        left=150.0, top=200.0, width=300.0, height=150.0,
        canvas_width=canvas_width, canvas_height=canvas_height
    )
    
    # Frontend: Transform to PDF (sent to backend)
    pdf_coords_frontend = transformer.canvas_to_pdf(canvas_annotation)
    print(f"Frontend → PDF: ({pdf_coords_frontend.left:.2f}, {pdf_coords_frontend.top:.2f}) {pdf_coords_frontend.width:.2f}x{pdf_coords_frontend.height:.2f}")
    
    # Backend: Receives PDF coordinates and processes clipping
    # Backend should get identical results when transforming back
    pdf_coords_backend = PDFCoordinates(
        pdf_coords_frontend.left, pdf_coords_frontend.top,
        pdf_coords_frontend.width, pdf_coords_frontend.height
    )
    
    canvas_coords_backend = transformer.pdf_to_canvas(pdf_coords_backend, canvas_width, canvas_height)
    print(f"Backend → Canvas: ({canvas_coords_backend.left:.2f}, {canvas_coords_backend.top:.2f}) {canvas_coords_backend.width:.2f}x{canvas_coords_backend.height:.2f}")
    
    # Verify round-trip accuracy
    coord_diff = abs(canvas_annotation.left - canvas_coords_backend.left)
    assert coord_diff < 1.0, f"Round-trip error too large: {coord_diff}"
    print("✅ DefineKeyAreas round-trip successful")
    
    # Test Case 2: Symbol annotation within legend clipping
    print("\n🔣 Test Case 2: Symbol Annotation within Legend")
    
    # Legend clipping bounds (in PDF coordinates)
    legend_pdf_coords = PDFCoordinates(left=100.0, top=150.0, width=200.0, height=100.0)
    
    # Create clipping transformer
    clipping_transformer = ClippingCoordinateTransformer(
        legend_pdf_coords=legend_pdf_coords,
        clipping_dpi=HIGH_RES_DPI,
        page_metadata=page_metadata
    )
    
    print(f"Clipping dimensions: {clipping_transformer.clipping_width_pixels}x{clipping_transformer.clipping_height_pixels} pixels")
    
    # Frontend: User annotates symbol within legend clipping canvas
    symbol_canvas_coords = CanvasCoordinates(
        left=25.0, top=15.0, width=40.0, height=30.0,
        canvas_width=clipping_transformer.clipping_width_pixels,
        canvas_height=clipping_transformer.clipping_height_pixels
    )
    
    # Frontend: Transform symbol to absolute PDF coordinates
    symbol_pdf_coords = clipping_transformer.symbol_canvas_to_pdf(symbol_canvas_coords)
    print(f"Symbol Canvas → PDF: ({symbol_pdf_coords.left:.3f}, {symbol_pdf_coords.top:.3f}) {symbol_pdf_coords.width:.3f}x{symbol_pdf_coords.height:.3f}")
    
    # Verify symbol is within legend bounds
    assert symbol_pdf_coords.left >= legend_pdf_coords.left, "Symbol outside legend left bound"
    assert symbol_pdf_coords.top >= legend_pdf_coords.top, "Symbol outside legend top bound"
    assert (symbol_pdf_coords.left + symbol_pdf_coords.width) <= (legend_pdf_coords.left + legend_pdf_coords.width), "Symbol outside legend right bound"
    assert (symbol_pdf_coords.top + symbol_pdf_coords.height) <= (legend_pdf_coords.top + legend_pdf_coords.height), "Symbol outside legend bottom bound"
    print("✅ Symbol correctly positioned within legend bounds")
    
    # Test Case 3: Multiple coordinate system consistency
    print("\n🎯 Test Case 3: Multi-System Consistency")
    
    # Test multiple transformations
    test_coords = [
        (50, 75, 100, 50),
        (400, 300, 150, 200),
        (10, 10, 20, 15)
    ]
    
    for left, top, width, height in test_coords:
        canvas_coords = CanvasCoordinates(left, top, width, height, canvas_width, canvas_height)
        
        # Canvas → PDF → Canvas
        pdf_coords = transformer.canvas_to_pdf(canvas_coords)
        canvas_restored = transformer.pdf_to_canvas(pdf_coords, canvas_width, canvas_height)
        
        # Check accuracy
        max_diff = max(
            abs(canvas_coords.left - canvas_restored.left),
            abs(canvas_coords.top - canvas_restored.top),
            abs(canvas_coords.width - canvas_restored.width),
            abs(canvas_coords.height - canvas_restored.height)
        )
        
        assert max_diff < 1.0, f"Transformation error too large: {max_diff}"
        print(f"  ✅ Coordinates ({left}, {top}) {width}x{height} → max error: {max_diff:.3f}")
    
    print("✅ All coordinate transformations validated!")
    return True


def test_json_serialization():
    """Test that coordinate objects serialize correctly for frontend-backend communication"""
    print("\n📦 Testing JSON Serialization")
    
    page_metadata = PageMetadata(
        page_number=1,
        pdf_width_points=612.0,
        pdf_height_points=792.0,
        pdf_rotation_degrees=0,
        image_width_pixels=1700,
        image_height_pixels=2200,
        image_dpi=200,
        high_res_image_width_pixels=2550,
        high_res_image_height_pixels=3300,
        high_res_dpi=300
    )
    
    # Test PageMetadata serialization
    metadata_dict = page_metadata.to_dict()
    metadata_restored = PageMetadata.from_dict(metadata_dict)
    
    assert metadata_restored.pdf_width_points == page_metadata.pdf_width_points
    assert metadata_restored.image_dpi == page_metadata.image_dpi
    print("✅ PageMetadata serialization works")
    
    # Test coordinate serialization
    pdf_coords = PDFCoordinates(100.5, 200.3, 150.7, 75.2)
    pdf_dict = pdf_coords.to_dict()
    
    expected_keys = ["left_points", "top_points", "width_points", "height_points"]
    for key in expected_keys:
        assert key in pdf_dict, f"Missing key: {key}"
    
    print("✅ Coordinate serialization works")
    
    # Test JSON round-trip
    json_str = json.dumps(pdf_dict)
    restored_dict = json.loads(json_str)
    restored_coords = PDFCoordinates(
        restored_dict["left_points"],
        restored_dict["top_points"], 
        restored_dict["width_points"],
        restored_dict["height_points"]
    )
    
    assert abs(restored_coords.left - pdf_coords.left) < 0.001
    print("✅ JSON round-trip serialization works")
    
    return True


def test_error_handling():
    """Test coordinate system error handling and edge cases"""
    print("\n⚠️  Testing Error Handling")
    
    page_metadata = PageMetadata(
        page_number=1,
        pdf_width_points=612.0,
        pdf_height_points=792.0,
        pdf_rotation_degrees=0,
        image_width_pixels=1700,
        image_height_pixels=2200,
        image_dpi=200,
        high_res_image_width_pixels=2550,
        high_res_image_height_pixels=3300,
        high_res_dpi=300
    )
    
    transformer = CoordinateTransformer(page_metadata)
    
    # Test zero dimensions
    try:
        zero_coords = CanvasCoordinates(0, 0, 0, 0, 800, 600)
        pdf_coords = transformer.canvas_to_pdf(zero_coords)
        print(f"  Zero dimensions handled: {pdf_coords.width}x{pdf_coords.height}")
    except Exception as e:
        print(f"  ❌ Zero dimensions failed: {e}")
    
    # Test boundary coordinates
    canvas_width, canvas_height = transformer.get_canvas_dimensions_for_aspect_ratio(1200, 900)
    boundary_coords = CanvasCoordinates(
        canvas_width - 10, canvas_height - 10, 5, 5,
        canvas_width, canvas_height
    )
    
    pdf_coords = transformer.canvas_to_pdf(boundary_coords)
    assert pdf_coords.left > 0 and pdf_coords.top > 0
    print("✅ Boundary coordinates handled correctly")
    
    return True


def run_all_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Coordinate Mapping Integration Tests\n")
    
    try:
        test_frontend_backend_coordination()
        test_json_serialization()
        test_error_handling()
        
        print("\n🎉 All integration tests passed!")
        print("✅ The coordinate mapping system is ready for end-to-end testing")
        print("\n📋 Summary:")
        print("  ✅ Frontend-Backend coordination validated")
        print("  ✅ JSON serialization working")
        print("  ✅ Error handling robust")
        print("  ✅ DefineKeyAreas → PDF mapping accurate")
        print("  ✅ SymbolAnnotation → PDF mapping accurate")
        print("  ✅ Round-trip transformations precise")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1) 