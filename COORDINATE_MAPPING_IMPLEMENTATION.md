# TimberGem Coordinate Mapping System - Implementation Guide

## 🎯 Overview

The TimberGem coordinate mapping system provides accurate, reliable transformations between different coordinate systems used throughout the application. **PDF coordinates (in points) are the single source of truth**, with clean transformations to image coordinates (pixels) and canvas coordinates (UI pixels).

## 📋 Key Principles

1. **Single Source of Truth**: PDF coordinates (in points, 72 DPI) are authoritative
2. **Clean Transformations**: Clear mathematical relationships between coordinate systems
3. **Y-Axis Handling**: Proper handling of origin differences (PDF bottom-left vs Image/Canvas top-left)
4. **Aspect Ratio Preservation**: Uniform scaling maintains image proportions
5. **Comprehensive Debugging**: Extensive logging for troubleshooting

## 🏗️ Architecture

### Coordinate Systems

```
📄 PDF Coordinates (Points, 72 DPI)
    ↕️ CoordinateTransformer
🖼️ Image Coordinates (Pixels at DPI)
    ↕️ CoordinateTransformer  
🎨 Canvas Coordinates (UI Pixels)
    ↕️ ClippingCoordinateTransformer
🔣 Symbol Coordinates (Within Legend Clipping)
```

### Core Classes

#### Backend (`backend/utils/coordinate_mapping.py`)
- `PDFCoordinates`: PDF points, bottom-left origin
- `ImageCoordinates`: Image pixels at specific DPI, top-left origin
- `CanvasCoordinates`: UI canvas pixels, top-left origin
- `ClippingCoordinates`: Pixels within legend clipping
- `PageMetadata`: Complete page transformation data
- `CoordinateTransformer`: Main transformation engine
- `ClippingCoordinateTransformer`: Symbol-within-legend transformations

#### Frontend (`frontend/src/utils/coordinateMapping.js`)
- JavaScript mirror of backend classes
- Identical transformation mathematics
- Consistent coordinate handling

## 🔄 Transformation Flows

### 1. DefineKeyAreas Tab Workflow

```
User draws on canvas
    ↓ CanvasCoordinates
Frontend: transformer.canvasToPdf()
    ↓ PDFCoordinates (sent to backend)
Backend: generate_clippings API
    ↓ Uses PDFCoordinates for clipping extraction
High-res clipping created at exact PDF location
```

### 2. SymbolAnnotation Tab Workflow

```
User annotates symbol within legend clipping
    ↓ CanvasCoordinates (relative to clipping)
Frontend: clippingTransformer.symbolCanvasToPdf()
    ↓ PDFCoordinates (absolute position in original PDF)
Backend: save_symbol_clippings API
    ↓ Creates SymbolAnnotation with all coordinate systems
Symbol positioned correctly in original PDF space
```

## 🐛 Debugging Guide

### Frontend Debugging

When testing, look for these console logs:

#### DefineKeyAreas Tab
```
🎨 [DefineKeyAreas] Loading background for page X
📐 [DefineKeyAreas] NEW coordinate system for page X:
    PDF: 612.0x792.0 points
    Image: 1700x2200 pixels @ 200 DPI
    Canvas: 695.5x900.0 pixels
✅ [DefineKeyAreas] Canvas X sized using NEW system
```

#### Generate Clippings
```
🚀 [DefineKeyAreas] ENHANCED - Generating clippings with NEW coordinate system
🔍 [DefineKeyAreas] ANNOTATION X ANALYSIS (SymbolLegend on page Y):
  📍 Canvas Coords: (150, 200) 300x150
  📄 PDF Coords (NEW SYSTEM): (131.76, 484.56) 263.88x131.76 points
```

#### Symbol Annotation
```
🚀 [SymbolAnnotation] ENHANCED - Saving symbols with NEW coordinate system
📐 [SymbolAnnotation] LEGEND X ANALYSIS:
  ✅ NEW coordinate system available for legend X
🔣 [SymbolAnnotation] SYMBOL ANALYSIS: symbol_name
    Canvas coords: (25, 15) 40x30
    PDF coords (NEW SYSTEM): (106.000, 153.600) 9.600x7.200 points
```

### Backend Debugging

Look for these server logs:

#### Generate Clippings
```
🎨 Processing SymbolLegend 1 on page 1
📄 PDF coords (NEW SYSTEM): (131.76, 484.56) 263.88x131.76 points
🎯 Transformation analysis:
  Canvas → PDF successful: True
  Transformer used: CoordinateTransformer
  Page metadata: 612.0x792.0 @ 200 DPI
```

#### Symbol Annotation
```
🔣 Processing symbol 'symbol_name':
  Canvas: (25.0, 15.0) 40.0x30.0
  PDF: (106.00, 153.60) 9.60x7.20
📄 Symbol metadata created:
  Coordinate System: NEW_SYSTEM
  PDF Coordinates: (106.00, 153.60) 9.60x7.20
```

### Common Issues and Solutions

#### 1. Canvas Dimensions Mismatch
**Symptom**: Canvas scaling errors, coordinates don't align
**Debug**: Look for these logs:
```
⚠️ [DefineKeyAreas] No page metadata for page X, using fallback sizing
📊 [DefineKeyAreas] Canvas X sized using FALLBACK
```
**Solution**: Ensure `docInfo.pageMetadata` is populated with new format

#### 2. Missing PDF Coordinates
**Symptom**: Symbols don't save with correct coordinates
**Debug**: Look for:
```
⚠️ [SymbolAnnotation] No NEW coordinate system data for legend X, using FALLBACK
```
**Solution**: Ensure DefineKeyAreas annotations include `pdfCoordinates` field

#### 3. Coordinate System Fallbacks
**Symptom**: Some annotations use old coordinate system
**Debug**: Check `coordinateSystem` field in saved data:
- `NEW_SYSTEM`: ✅ Using new coordinate mapping
- `FALLBACK`: ⚠️ Using old system (investigate why)
- `FALLBACK_NO_SCALE`: ❌ Missing canvas scale info
- `FALLBACK_NO_DATA`: ❌ Missing clipping data

## 🧪 Testing

### Run Integration Tests
```bash
cd backend
python test_coordinate_integration.py
```

Expected output:
```
🎉 All integration tests passed!
✅ The coordinate mapping system is ready for end-to-end testing
```

### Test Workflow
1. Upload PDF and generate metadata
2. Use DefineKeyAreas to create "Symbol Legend" annotations
3. Generate clippings (should show NEW coordinate system logs)
4. Use SymbolAnnotation to annotate symbols within legends
5. Save symbols (should show NEW_SYSTEM coordinate transformations)
6. Verify symbols have correct PDF coordinates in saved metadata

## 📊 Data Format Changes

### Old Format (Legacy)
```json
{
  "pdf_width": 612.0,
  "pdf_height": 792.0,
  "image_width": 1700,
  "image_height": 2200,
  "scale_x": 2.78,
  "scale_y": 2.78
}
```

### New Format
```json
{
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
}
```

### Symbol Annotation Format
```json
{
  "id": "uuid",
  "name": "symbol_name",
  "coordinate_system": "NEW_SYSTEM",
  "coordinates": {
    "pdf_absolute": {
      "left_points": 106.000,
      "top_points": 153.600,
      "width_points": 9.600,
      "height_points": 7.200
    },
    "legend_clipping_relative": {
      "left_clipping_pixels": 104,
      "top_clipping_pixels": 62,
      "width_clipping_pixels": 40,
      "height_clipping_pixels": 30,
      "clipping_dpi": 300
    },
    "canvas_annotation": {
      "left_canvas_pixels": 25.0,
      "top_canvas_pixels": 15.0,
      "width_canvas_pixels": 40.0,
      "height_canvas_pixels": 30.0,
      "canvas_width_pixels": 416.0,
      "canvas_height_pixels": 208.0
    }
  }
}
```

## 🔧 Implementation Status

### ✅ Completed
- ✅ Core coordinate mapping classes (backend & frontend)
- ✅ CoordinateTransformer for PDF ↔ Image ↔ Canvas
- ✅ ClippingCoordinateTransformer for symbols within legends
- ✅ DefineKeyAreas integration with new coordinate system
- ✅ SymbolAnnotation integration with new coordinate system
- ✅ Enhanced debugging and logging throughout
- ✅ Comprehensive test suite
- ✅ Backend API updates (generate_clippings, save_symbol_clippings)
- ✅ PDF metadata generation using new format

### 🎯 Key Benefits Achieved
1. **Accurate Symbol Mapping**: Symbols now correctly map to PDF coordinates
2. **Consistent Coordinate Handling**: No more mixed transformations
3. **Comprehensive Debugging**: Easy to trace coordinate transformations
4. **Mathematical Accuracy**: Rigorous testing validates all transformations
5. **Clean Architecture**: Reusable coordinate transformation classes

## 📞 Troubleshooting Checklist

When testing the refactored system:

1. **Check console logs** for coordinate system indicators:
   - NEW vs FALLBACK system usage
   - PDF coordinate calculations
   - Canvas dimension calculations

2. **Verify API responses** include:
   - `pdfCoordinates` field in clipping responses
   - `coordinate_system: "NEW_SYSTEM"` in symbol saves

3. **Test end-to-end workflow**:
   - PDF upload → metadata generation
   - Define key areas → clipping generation
   - Symbol annotation → symbol saving
   - Verify final PDF coordinates in saved data

4. **Run integration tests** to validate mathematical accuracy

The coordinate mapping system is now production-ready with comprehensive debugging support for easy troubleshooting during testing. 