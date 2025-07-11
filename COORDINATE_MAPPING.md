# 🎯 TimberGem Coordinate Mapping & High-Resolution Clipping

## Overview

TimberGem now includes sophisticated coordinate mapping functionality that transforms canvas pixel coordinates back to original PDF coordinates for high-resolution clipping extraction. This ensures that key area annotations maintain maximum quality and precision.

## 🔄 Coordinate Transformation Pipeline

### **Three Coordinate Systems**

1. **Canvas Coordinates** - User interface display (e.g., 600x800 pixels)
2. **Image Coordinates** - Full-resolution PNG (e.g., 1700x2200 pixels at 200 DPI)  
3. **PDF Coordinates** - Original document points (e.g., 612x792 points for Letter size)

### **Transformation Steps**

```
Canvas Pixels → Image Pixels → PDF Points → High-Res Clipping
    (UI)           (PNG)         (Original)      (300 DPI)
```

## 🛠️ Technical Implementation

### **1. Metadata Collection (Backend)**

During PDF upload, the system stores transformation metadata:

```python
page_metadata = {
    "pdf_width": 612.0,      # Original PDF width in points
    "pdf_height": 792.0,     # Original PDF height in points  
    "image_width": 1700,     # PNG width in pixels
    "image_height": 2200,    # PNG height in pixels
    "dpi": 200,              # Resolution used for PNG generation
    "scale_x": 2.78,         # PDF-to-image scale factor X
    "scale_y": 2.78          # PDF-to-image scale factor Y
}
```

### **2. Canvas Dimension Tracking (Frontend)**

The React component tracks actual canvas display dimensions:

```javascript
setCanvasDimensions(prev => ({
    ...prev,
    [pageNumber]: {
        width: img.width * scale,   // Actual canvas width
        height: img.height * scale  // Actual canvas height
    }
}));
```

### **3. Coordinate Transformation (Backend)**

Two-step conversion process:

#### **Step 1: Canvas → Image Coordinates**
```python
canvas_to_image_scale_x = image_width / canvas_width
canvas_to_image_scale_y = image_height / canvas_height

image_left = canvas_coords["left"] * canvas_to_image_scale_x
image_top = canvas_coords["top"] * canvas_to_image_scale_y
```

#### **Step 2: Image → PDF Coordinates**
```python
pdf_left = image_left / scale_x
# Y-axis flip: PDF origin is bottom-left, canvas origin is top-left
pdf_top = pdf_height - (image_top / scale_y) - (image_height_coord / scale_y)
```

### **4. High-Resolution Clipping Generation**

Extracts at 300 DPI for maximum quality:

```python
# Create clipping rectangle in PDF coordinates
clip_rect = fitz.Rect(pdf_left, pdf_top, pdf_left + pdf_width, pdf_top + pdf_height)

# Generate 300 DPI pixmap
matrix = fitz.Matrix(300/72, 300/72)  # 300 DPI scaling
pix = page.get_pixmap(matrix=matrix, clip=rect=clip_rect)
```

## 📁 File Structure

```
data/processed/{docId}/
├── page_1.png              # Display images (200 DPI)
├── page_2.png
├── page_metadata.json      # Transformation metadata
├── original.pdf            # Original PDF for clipping
├── annotations.json        # Canvas annotations
├── summaries.json          # Page summaries
└── clippings/              # High-res clippings (300 DPI)
    ├── TitleBlock_{id}_clipping.png
    ├── DrawingArea_{id}_clipping.png
    └── NotesArea_{id}_clipping.png
```

## 🎨 User Workflow

1. **Upload PDF** → System generates 200 DPI images + metadata
2. **Create Annotations** → User draws rectangles on canvas
3. **Generate Clippings** → Click "Generate Knowledge Graph" 
4. **High-Res Output** → 300 DPI clippings saved automatically

## 🧪 Example Transformation

**Input (Canvas):**
```
Left: 100px, Top: 150px, Width: 200px, Height: 100px
Canvas: 600x800 pixels
```

**Output (PDF):**
```
Left: 102.0pts, Top: 544.5pts, Width: 204.0pts, Height: 99.0pts
Position: 16.7% from left, 68.8% from bottom
Size: 33.3% width × 12.5% height of page
```

**Final Clipping:**
```
High-resolution PNG at 300 DPI
Extracted from original PDF quality
```

## ⚡ API Endpoints

### **POST /api/generate_clippings**

Generates high-resolution clippings from canvas annotations.

**Request:**
```json
{
    "docId": "uuid-string",
    "annotations": [
        {
            "id": "annotation-id",
            "tag": "TitleBlock", 
            "left": 100,
            "top": 150,
            "width": 200,
            "height": 100,
            "pageNumber": 1
        }
    ],
    "canvasDimensions": {
        "1": { "width": 600, "height": 800 }
    }
}
```

**Response:**
```json
{
    "message": "Clippings generated successfully",
    "docId": "uuid-string",
    "clippings": [
        {
            "annotationId": "annotation-id",
            "tag": "TitleBlock",
            "pageNumber": 1,
            "canvasCoords": { "left": 100, "top": 150, "width": 200, "height": 100 },
            "pdfCoords": { "left": 102.0, "top": 544.5, "width": 204.0, "height": 99.0 },
            "clippingPath": "/path/to/clipping.png",
            "relativeUrl": "/data/processed/{docId}/clippings/TitleBlock_{id}_clipping.png"
        }
    ]
}
```

## 🎯 Key Benefits

- **High Fidelity**: 300 DPI clippings from original PDF
- **Pixel Perfect**: Accurate coordinate mapping
- **Scalable**: Works with any PDF size/resolution
- **Efficient**: Only generates clippings when needed
- **Quality**: No double-compression or quality loss

## 🔧 Configuration

**PDF Processing DPI**: 200 DPI (balance of quality/speed)  
**Clipping Output DPI**: 300 DPI (high quality for analysis)  
**Coordinate System**: Points (1/72 inch) for PDF compatibility

---

✅ **Ready for Production**: The coordinate mapping system is fully implemented and tested for accurate high-resolution clipping generation. 