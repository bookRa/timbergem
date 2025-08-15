# Canvas Styling Reference

## Main Layout Container
```css
.symbol-review-canvas-layout {
    /* Controls overall grid layout */
    height: calc(100vh - 200px);  /* Adjust 200px to control total height */
    min-height: 700px;            /* Remove or adjust minimum height */
    grid-template-columns: 1fr 300px; /* Left canvas area vs right panel width */
}
```

## Canvas Container (Main Image Area)
```css
.canvas-container {
    /* Controls the image display area */
    flex: 1;                      /* Takes remaining space */
    padding: 20px;                /* Space around canvas */
    max-height: 100%;             /* Prevents overflow */
    overflow: auto;               /* Adds scrollbars if needed */
}
```

## Interactive Canvas Component
```css
.interactive-detection-canvas {
    /* Controls canvas component height */
    height: 100%;                 /* Fill parent container */
    min-height: 600px;            /* Remove or adjust for smaller screens */
}
```

## Canvas Element Sizing (JavaScript)
```javascript
// In InteractiveDetectionCanvas.jsx, setupCanvas function:
const scale = Math.min(scaleX, scaleY, 1.0); // Controls image scaling

// Container size calculation:
const containerWidth = containerRect.width - 40;   // Adjust padding (40px)
const containerHeight = containerRect.height - 100; // Adjust for controls (100px)
```

## Quick Fixes to Try:

### 1. Make canvas bigger:
```css
.symbol-review-canvas-layout {
    height: calc(100vh - 120px); /* Reduce from 200px to 120px */
}
```

### 2. Remove minimum height constraints:
```css
.interactive-detection-canvas {
    min-height: auto; /* Remove 600px minimum */
}
```

### 3. Adjust grid proportions:
```css
.symbol-review-canvas-layout {
    grid-template-columns: 2fr 300px; /* Give more space to canvas */
}
```

### 4. Increase canvas scale in JavaScript:
Change the scale calculation to allow larger display:
```javascript
const scale = Math.min(scaleX, scaleY, 2.0); // Allow up to 2x scaling
```

## Files to Edit:
- **CSS**: `frontend/src/App.css` (search for classes above)
- **JavaScript**: `frontend/src/components/InteractiveDetectionCanvas.jsx` (setupCanvas function)