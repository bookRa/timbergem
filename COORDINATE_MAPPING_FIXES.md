# 🔧 TimberGem Coordinate Mapping & Clipping Fixes

## 🐛 Issues Identified

From analysis of the test data (`data/processed/63a84b14-09de-4b7e-b8ea-294cdbddc0a5`):

### **1. Canvas Dimension Mismatch**
- **Problem**: Frontend calculates canvas as 600.6x464.1 but may be sending different values
- **Evidence**: PDF is 792x612 pts, image is 2200x1700 px, scale factor should be ~0.273
- **Impact**: Coordinate transformation uses wrong scale factors

### **2. Directory Structure**
- **Current**: All clippings in single `/clippings/` directory  
- **Required**: Organize by page: `/clippings/page1/`, `/clippings/page2/`
- **Naming**: Change from `Type_annotationId_clipping.png` to `Type_1.png`, `Type_2.png`

### **3. Coordinate System Issues**
- **Y-axis Flipping**: PDF origin (bottom-left) vs Canvas origin (top-left)
- **Multiple Scales**: Canvas → Image → PDF requires precise scale factors
- **Bounds Checking**: Need validation for out-of-bounds coordinates

## ✅ Fixes Implemented

### **Frontend Changes (`DefineKeyAreasTab.jsx`)**

1. **Precise Canvas Dimensions**:
```javascript
const actualCanvasWidth = img.width * scale;
const actualCanvasHeight = img.height * scale;
setCanvasDimensions(prev => ({
    ...prev,
    [pageNumber]: {
        width: actualCanvasWidth,  // Exact canvas size
        height: actualCanvasHeight // Exact canvas size  
    }
}));
```

2. **Debug Logging**:
```javascript
console.log(`Canvas ${pageNumber} initialized: ${actualCanvasWidth.toFixed(1)}x${actualCanvasHeight.toFixed(1)}`);
```

### **Backend Changes (`app.py`)**

1. **Page-Based Directory Structure**:
```python
# Create page directories: /clippings/page1/, /clippings/page2/
page_clippings_dir = os.path.join(clippings_base_dir, f"page{page_num}")
os.makedirs(page_clippings_dir, exist_ok=True)
```

2. **Sequential Naming by Type**:
```python
# Group by type and number sequentially: DrawingArea_1.png, DrawingArea_2.png
for i, annotation in enumerate(tag_annotations, 1):
    clipping_filename = f"{tag}_{i}.png"
```

3. **Enhanced Coordinate Debugging**:
```python
print(f"Canvas to image scale: {canvas_to_image_scale_x:.3f}x{canvas_to_image_scale_y:.3f}")
print(f"Image coords: ({image_left:.1f}, {image_top:.1f})")
print(f"PDF coords: ({pdf_left:.1f}, {pdf_top:.1f})")
```

4. **Bounds Validation**:
```python
if pdf_left < 0 or pdf_top < 0 or pdf_left + pdf_width_coord > pdf_width:
    print(f"⚠️  WARNING: PDF coordinates out of bounds!")
```

## 🧪 Test Strategy

### **Step 1: Verify Canvas Dimensions**
1. Upload test PDF
2. Create annotation  
3. Check browser console for canvas dimensions
4. Verify dimensions match image scaling calculations

### **Step 2: Test Coordinate Transformation**
```python
# Expected for landscape PDF (792x612 pts, 2200x1700 px image)
canvas_scale = min(600/2200, 800/1700)  # ≈ 0.273
actual_canvas_width = 2200 * 0.273  # ≈ 600.6
actual_canvas_height = 1700 * 0.273  # ≈ 464.1

# Test annotation at (37, 47.9) 425x83 on canvas
# Should map to reasonable PDF coordinates within page bounds
```

### **Step 3: Validate Clipping Output**
Expected file structure:
```
data/processed/{docId}/clippings/
├── page1/
│   ├── DrawingArea_1.png  
│   ├── Legend_1.png
│   └── NotesArea_1.png
└── page2/
    └── TitleBlock_1.png
```

## 🎯 Testing Commands

### **Manual Canvas Test**:
```javascript
// In browser console after creating annotations:
console.log('Canvas dimensions:', canvasDimensions);
console.log('Annotations:', allAnnotations);
```

### **API Test**:
```python
# Test with corrected dimensions
POST /api/generate_clippings
{
    "docId": "63a84b14-09de-4b7e-b8ea-294cdbddc0a5",
    "annotations": [...],
    "canvasDimensions": {
        "1": { "width": 600.6, "height": 464.1 }
    }
}
```

## 🔍 Debugging Checklist

1. ✅ **Canvas dimensions logged correctly**
2. ✅ **Coordinate transformation debug output** 
3. ✅ **Page-based directory structure**
4. ✅ **Sequential type-based naming**
5. ⏳ **Bounds validation working**
6. ⏳ **Clippings match annotations visually**

## 🚀 Next Steps

1. **Test with Frontend**: Use browser to create annotations and check console logs
2. **Verify API Response**: Ensure clipping generation completes successfully  
3. **Visual Validation**: Compare generated clippings with original annotations
4. **Scale Testing**: Test with different PDF sizes and orientations

---

**Key Insight**: The coordinate mapping requires THREE precise measurements:
1. **Original Image Size** (from page_metadata.json)
2. **Canvas Display Size** (calculated by frontend, sent in API call)  
3. **PDF Page Size** (from page_metadata.json)

All transformations must use these exact values for pixel-perfect accuracy. 