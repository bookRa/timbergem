#!/usr/bin/env python3
"""
Test suite for the coordinate mapping system.
Validates all coordinate transformations and edge cases.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.coordinate_mapping import (
    PDFCoordinates, ImageCoordinates, CanvasCoordinates, ClippingCoordinates,
    PageMetadata, CoordinateTransformer, ClippingCoordinateTransformer,
    validate_coordinates, DEFAULT_DPI, HIGH_RES_DPI
)
import math


def test_coordinate_classes():
    """Test coordinate class creation and serialization"""
    print("🧪 Testing coordinate classes...")
    
    # Test PDFCoordinates
    pdf_coords = PDFCoordinates(left=100.0, top=200.0, width=150.0, height=75.0)
    pdf_dict = pdf_coords.to_dict()
    assert pdf_dict["left_points"] == 100.0
    assert pdf_dict["top_points"] == 200.0
    assert pdf_dict["width_points"] == 150.0
    assert pdf_dict["height_points"] == 75.0
    
    rect_tuple = pdf_coords.to_rect_tuple()
    assert rect_tuple == (100.0, 200.0, 250.0, 275.0)
    
    # Test ImageCoordinates
    img_coords = ImageCoordinates(left=278, top=556, width=417, height=208, dpi=200)
    img_dict = img_coords.to_dict()
    assert img_dict["left_pixels"] == 278
    assert img_dict["dpi"] == 200
    
    # Test CanvasCoordinates
    canvas_coords = CanvasCoordinates(left=150.2, top=300.4, width=225.6, height=112.8, 
                                    canvas_width=1200.0, canvas_height=900.0)
    canvas_dict = canvas_coords.to_dict()
    assert canvas_dict["canvas_width_pixels"] == 1200.0
    
    # Test ClippingCoordinates
    clipping_coords = ClippingCoordinates(left_pixels=50, top_pixels=25, width_pixels=100, 
                                        height_pixels=50, clipping_dpi=300)
    clipping_dict = clipping_coords.to_dict()
    assert clipping_dict["clipping_dpi"] == 300
    
    print("✅ Coordinate classes test passed")


def test_page_metadata():
    """Test page metadata creation and serialization"""
    print("🧪 Testing page metadata...")
    
    metadata = PageMetadata(
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
    
    metadata_dict = metadata.to_dict()
    assert metadata_dict["page_number"] == 1
    assert metadata_dict["pdf_width_points"] == 612.0
    assert metadata_dict["high_res_dpi"] == 300
    
    # Test round-trip serialization
    metadata_restored = PageMetadata.from_dict(metadata_dict)
    assert metadata_restored.page_number == 1
    assert metadata_restored.pdf_width_points == 612.0
    
    print("✅ Page metadata test passed")


def test_basic_transformations():
    """Test basic PDF ↔ Image ↔ Canvas transformations"""
    print("🧪 Testing basic coordinate transformations...")
    
    # Create test page metadata (Letter size at 200 DPI)
    metadata = PageMetadata(
        page_number=1,
        pdf_width_points=612.0,
        pdf_height_points=792.0,
        pdf_rotation_degrees=0,
        image_width_pixels=1700,  # 612 * 200/72 ≈ 1700
        image_height_pixels=2200,  # 792 * 200/72 ≈ 2200
        image_dpi=200,
        high_res_image_width_pixels=2550,
        high_res_image_height_pixels=3300,
        high_res_dpi=300
    )
    
    transformer = CoordinateTransformer(metadata)
    
    # Test PDF to Image transformation
    pdf_coords = PDFCoordinates(left=100.0, top=200.0, width=150.0, height=75.0)
    image_coords = transformer.pdf_to_image(pdf_coords)
    
    # Verify scaling (200 DPI / 72 ≈ 2.78)
    expected_scale = 200.0 / 72.0
    assert abs(image_coords.left - int(100.0 * expected_scale)) <= 1
    assert abs(image_coords.width - int(150.0 * expected_scale)) <= 1
    assert image_coords.dpi == 200
    
    # Test Y coordinate (no flip needed - both use top-left origin)
    # PDF top=200 should directly scale to image top = 200 * scale
    expected_image_top = int(200.0 * expected_scale)
    assert abs(image_coords.top - expected_image_top) <= 1
    
    # Test reverse transformation
    pdf_coords_restored = transformer.image_to_pdf(image_coords)
    assert abs(pdf_coords_restored.left - pdf_coords.left) < 1.0
    assert abs(pdf_coords_restored.top - pdf_coords.top) < 1.0
    assert abs(pdf_coords_restored.width - pdf_coords.width) < 1.0
    assert abs(pdf_coords_restored.height - pdf_coords.height) < 1.0
    
    print("✅ Basic transformations test passed")


def test_canvas_transformations():
    """Test Image ↔ Canvas transformations with aspect ratio"""
    print("🧪 Testing canvas transformations...")
    
    metadata = PageMetadata(
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
    
    transformer = CoordinateTransformer(metadata)
    
    # Test canvas dimension calculation
    canvas_width, canvas_height = transformer.get_canvas_dimensions_for_aspect_ratio(1200, 900)
    
    # Image aspect ratio: 1700/2200 ≈ 0.77
    # Max aspect ratio: 1200/900 ≈ 1.33
    # Since image is taller, should fit to height: width = 900 * 0.77 ≈ 695
    expected_width = 900 * (1700 / 2200)
    assert abs(canvas_width - expected_width) < 1.0
    assert canvas_height == 900
    
    # Test image to canvas transformation
    image_coords = ImageCoordinates(left=278, top=556, width=417, height=208, dpi=200)
    canvas_coords = transformer.image_to_canvas(image_coords, canvas_width, canvas_height)
    
    # Verify uniform scaling
    expected_scale = min(canvas_width / 1700, canvas_height / 2200)
    assert abs(canvas_coords.left - image_coords.left * expected_scale) < 1.0
    assert abs(canvas_coords.width - image_coords.width * expected_scale) < 1.0
    
    # Test reverse transformation
    image_coords_restored = transformer.canvas_to_image(canvas_coords)
    assert abs(image_coords_restored.left - image_coords.left) <= 1
    assert abs(image_coords_restored.top - image_coords.top) <= 1
    assert abs(image_coords_restored.width - image_coords.width) <= 1
    assert abs(image_coords_restored.height - image_coords.height) <= 1
    
    print("✅ Canvas transformations test passed")


def test_direct_canvas_pdf_transformation():
    """Test direct Canvas ↔ PDF transformations"""
    print("🧪 Testing direct canvas-PDF transformations...")
    
    metadata = PageMetadata(
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
    
    transformer = CoordinateTransformer(metadata)
    
    # Test canvas to PDF direct transformation
    canvas_coords = CanvasCoordinates(left=150.0, top=200.0, width=300.0, height=150.0,
                                    canvas_width=695.0, canvas_height=900.0)
    pdf_coords = transformer.canvas_to_pdf(canvas_coords)
    
    # Test reverse transformation
    canvas_coords_restored = transformer.pdf_to_canvas(pdf_coords, 695.0, 900.0)
    
    # Should be very close to original
    assert abs(canvas_coords_restored.left - canvas_coords.left) < 2.0
    assert abs(canvas_coords_restored.top - canvas_coords.top) < 2.0
    assert abs(canvas_coords_restored.width - canvas_coords.width) < 2.0
    assert abs(canvas_coords_restored.height - canvas_coords.height) < 2.0
    
    print("✅ Direct canvas-PDF transformations test passed")


def test_clipping_transformations():
    """Test symbol annotation within legend clippings"""
    print("🧪 Testing clipping coordinate transformations...")
    
    # Create test scenario: Legend clipping within a page
    metadata = PageMetadata(
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
    
    # Legend area in PDF coordinates (100x50 points at position 50,100)
    legend_pdf_coords = PDFCoordinates(left=50.0, top=100.0, width=100.0, height=50.0)
    
    # Create clipping transformer (300 DPI clipping)
    clipping_transformer = ClippingCoordinateTransformer(
        legend_pdf_coords=legend_pdf_coords,
        clipping_dpi=300,
        page_metadata=metadata
    )
    
    # Verify clipping dimensions calculation
    # 100 points * 300 DPI / 72 = 416.67 ≈ 416 pixels
    expected_width = int(100.0 * 300 / 72)
    expected_height = int(50.0 * 300 / 72)
    assert clipping_transformer.clipping_width_pixels == expected_width
    assert clipping_transformer.clipping_height_pixels == expected_height
    
    # Test symbol annotation within clipping
    # Symbol at position (20, 10) with size (15, 8) within the clipping canvas
    symbol_canvas_coords = CanvasCoordinates(
        left=20.0, top=10.0, width=15.0, height=8.0,
        canvas_width=416.0, canvas_height=208.0  # Canvas matches clipping dimensions
    )
    
    # Transform to PDF coordinates
    symbol_pdf_coords = clipping_transformer.symbol_canvas_to_pdf(symbol_canvas_coords)
    
    # Verify the symbol is positioned correctly within the legend area
    # Canvas position (20, 10) should map to PDF position (50 + offset, 100 + offset)
    # where offset = canvas_position * (72/300) = canvas_position * 0.24
    expected_pdf_left = 50.0 + (20.0 * 72.0 / 300.0)
    expected_pdf_top = 100.0 + (10.0 * 72.0 / 300.0)
    
    assert abs(symbol_pdf_coords.left - expected_pdf_left) < 0.1
    assert abs(symbol_pdf_coords.top - expected_pdf_top) < 0.1
    
    # Verify symbol dimensions
    expected_pdf_width = 15.0 * 72.0 / 300.0
    expected_pdf_height = 8.0 * 72.0 / 300.0
    assert abs(symbol_pdf_coords.width - expected_pdf_width) < 0.1
    assert abs(symbol_pdf_coords.height - expected_pdf_height) < 0.1
    
    # Test reverse transformation
    clipping_coords = clipping_transformer.pdf_to_clipping(symbol_pdf_coords)
    canvas_coords_restored = clipping_transformer.canvas_to_clipping(symbol_canvas_coords)
    
    assert abs(clipping_coords.left_pixels - canvas_coords_restored.left_pixels) <= 1
    assert abs(clipping_coords.top_pixels - canvas_coords_restored.top_pixels) <= 1
    
    print("✅ Clipping transformations test passed")


def test_coordinate_validation():
    """Test coordinate validation functions"""
    print("🧪 Testing coordinate validation...")
    
    # Valid coordinates
    valid_pdf = PDFCoordinates(left=10.0, top=20.0, width=100.0, height=50.0)
    assert validate_coordinates(valid_pdf, "pdf") == True
    
    valid_image = ImageCoordinates(left=10, top=20, width=100, height=50, dpi=200)
    assert validate_coordinates(valid_image, "image") == True
    
    valid_canvas = CanvasCoordinates(left=10.0, top=20.0, width=100.0, height=50.0,
                                   canvas_width=800.0, canvas_height=600.0)
    assert validate_coordinates(valid_canvas, "canvas") == True
    
    # Invalid coordinates (negative dimensions)
    invalid_pdf = PDFCoordinates(left=10.0, top=20.0, width=-100.0, height=50.0)
    assert validate_coordinates(invalid_pdf, "pdf") == False
    
    invalid_image = ImageCoordinates(left=10, top=20, width=100, height=50, dpi=0)
    assert validate_coordinates(invalid_image, "image") == False
    
    print("✅ Coordinate validation test passed")


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("🧪 Testing edge cases...")
    
    metadata = PageMetadata(
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
    
    transformer = CoordinateTransformer(metadata)
    
    # Test coordinates at origin
    origin_pdf = PDFCoordinates(left=0.0, top=0.0, width=10.0, height=10.0)
    origin_image = transformer.pdf_to_image(origin_pdf)
    origin_pdf_restored = transformer.image_to_pdf(origin_image)
    
    assert abs(origin_pdf_restored.left - origin_pdf.left) < 1.0
    assert abs(origin_pdf_restored.top - origin_pdf.top) < 1.0
    
    # Test coordinates at page boundaries
    boundary_pdf = PDFCoordinates(left=602.0, top=782.0, width=10.0, height=10.0)
    boundary_image = transformer.pdf_to_image(boundary_pdf)
    boundary_pdf_restored = transformer.image_to_pdf(boundary_image)
    
    assert abs(boundary_pdf_restored.left - boundary_pdf.left) < 1.0
    assert abs(boundary_pdf_restored.top - boundary_pdf.top) < 1.0
    
    # Test very small coordinates
    tiny_pdf = PDFCoordinates(left=100.0, top=100.0, width=0.1, height=0.1)
    tiny_image = transformer.pdf_to_image(tiny_pdf)
    # Should handle sub-pixel coordinates (may result in 0 pixels for very small areas)
    assert tiny_image.width >= 0  # Can be 0 for very small areas
    assert tiny_image.height >= 0
    
    # Test minimum viable coordinates (should result in at least 1 pixel)
    min_pdf = PDFCoordinates(left=100.0, top=100.0, width=1.0, height=1.0)
    min_image = transformer.pdf_to_image(min_pdf)
    assert min_image.width >= 1
    assert min_image.height >= 1
    
    print("✅ Edge cases test passed")


def run_all_tests():
    """Run all coordinate mapping tests"""
    print("🚀 Starting coordinate mapping test suite...\n")
    
    try:
        test_coordinate_classes()
        test_page_metadata()
        test_basic_transformations()
        test_canvas_transformations()
        test_direct_canvas_pdf_transformation()
        test_clipping_transformations()
        test_coordinate_validation()
        test_edge_cases()
        
        print("\n🎉 All coordinate mapping tests passed!")
        print("✅ The coordinate transformation system is working correctly.")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 