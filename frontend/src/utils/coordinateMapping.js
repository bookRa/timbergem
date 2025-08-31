/**
 * TimberGem Frontend Coordinate Mapping System
 * 
 * JavaScript implementation that mirrors the backend coordinate transformation system.
 * Ensures consistent coordinate handling between frontend UI and backend processing.
 */

// Constants
export const DEFAULT_DPI = 200;
export const HIGH_RES_DPI = 300;
export const POINTS_PER_INCH = 72.0;
export const MAX_CANVAS_WIDTH = 1200;
export const MAX_CANVAS_HEIGHT = 900;

/**
 * PDF coordinates in points (72 DPI), origin at top-left.
 * This is the single source of truth for all coordinate systems.
 * Note: PyMuPDF uses top-left origin, not the PDF standard's bottom-left!
 */
export class PDFCoordinates {
    constructor(left, top, width, height) {
        this.left = left;
        this.top = top;
        this.width = width;
        this.height = height;
    }

    toDict() {
        return {
            left_points: this.left,
            top_points: this.top,
            width_points: this.width,
            height_points: this.height
        };
    }

    toRectTuple() {
        return [this.left, this.top, this.left + this.width, this.top + this.height];
    }
}

/**
 * Image coordinates in pixels at specific DPI, origin at top-left.
 * Used for pixmap generation and image-based operations.
 */
export class ImageCoordinates {
    constructor(left, top, width, height, dpi) {
        this.left = left;
        this.top = top;
        this.width = width;
        this.height = height;
        this.dpi = dpi;
    }

    toDict() {
        return {
            left_pixels: this.left,
            top_pixels: this.top,
            width_pixels: this.width,
            height_pixels: this.height,
            dpi: this.dpi
        };
    }
}

/**
 * Canvas coordinates in pixels for UI display, origin at top-left.
 * Includes canvas dimensions for scale calculations.
 */
export class CanvasCoordinates {
    constructor(left, top, width, height, canvasWidth, canvasHeight) {
        this.left = left;
        this.top = top;
        this.width = width;
        this.height = height;
        this.canvasWidth = canvasWidth;
        this.canvasHeight = canvasHeight;
    }

    toDict() {
        return {
            left_canvas_pixels: this.left,
            top_canvas_pixels: this.top,
            width_canvas_pixels: this.width,
            height_canvas_pixels: this.height,
            canvas_width_pixels: this.canvasWidth,
            canvas_height_pixels: this.canvasHeight
        };
    }
}

/**
 * Coordinates within a legend clipping image (pixels at clipping DPI).
 * Used for symbol annotations within extracted legend clippings.
 */
export class ClippingCoordinates {
    constructor(leftPixels, topPixels, widthPixels, heightPixels, clippingDpi) {
        this.leftPixels = leftPixels;
        this.topPixels = topPixels;
        this.widthPixels = widthPixels;
        this.heightPixels = heightPixels;
        this.clippingDpi = clippingDpi;
    }

    toDict() {
        return {
            left_clipping_pixels: this.leftPixels,
            top_clipping_pixels: this.topPixels,
            width_clipping_pixels: this.widthPixels,
            height_clipping_pixels: this.heightPixels,
            clipping_dpi: this.clippingDpi
        };
    }
}

/**
 * Complete page metadata for coordinate transformations.
 * Contains all information needed for accurate coordinate mapping.
 */
export class PageMetadata {
    constructor(data) {
        this.pageNumber = data.page_number;
        this.pdfWidthPoints = data.pdf_width_points;
        this.pdfHeightPoints = data.pdf_height_points;
        this.pdfRotationDegrees = data.pdf_rotation_degrees;
        this.imageWidthPixels = data.image_width_pixels;
        this.imageHeightPixels = data.image_height_pixels;
        this.imageDpi = data.image_dpi;
        this.highResImageWidthPixels = data.high_res_image_width_pixels;
        this.highResImageHeightPixels = data.high_res_image_height_pixels;
        this.highResDpi = data.high_res_dpi;
    }

    toDict() {
        return {
            page_number: this.pageNumber,
            pdf_width_points: this.pdfWidthPoints,
            pdf_height_points: this.pdfHeightPoints,
            pdf_rotation_degrees: this.pdfRotationDegrees,
            image_width_pixels: this.imageWidthPixels,
            image_height_pixels: this.imageHeightPixels,
            image_dpi: this.imageDpi,
            high_res_image_width_pixels: this.highResImageWidthPixels,
            high_res_image_height_pixels: this.highResImageHeightPixels,
            high_res_dpi: this.highResDpi
        };
    }
}

/**
 * Centralized coordinate transformation engine.
 * Handles all transformations between PDF, image, and canvas coordinate systems.
 */
export class CoordinateTransformer {
    constructor(pageMetadata) {
        this.pageMetadata = pageMetadata;
        
        // Pre-calculate transformation factors for efficiency
        this.pdfToImageScale = this._calculatePdfToImageScale();
        this.imageToPdfScale = 1.0 / this.pdfToImageScale;
        
        this.pdfToHighResScale = this._calculatePdfToHighResScale();
        this.highResToPdfScale = 1.0 / this.pdfToHighResScale;
    }

    _calculatePdfToImageScale() {
        return this.pageMetadata.imageDpi / 72.0; // 72 points per inch
    }

    _calculatePdfToHighResScale() {
        return this.pageMetadata.highResDpi / 72.0;
    }

    /**
     * Transform PDF coordinates to standard image coordinates.
     * Both use top-left origin, so no Y-axis flip needed!
     */
    pdfToImage(pdfCoords) {
        // Convert points to pixels - simple scaling, no coordinate system changes
        const imageLeft = Math.round(pdfCoords.left * this.pdfToImageScale);
        const imageTop = Math.round(pdfCoords.top * this.pdfToImageScale);
        const imageWidth = Math.round(pdfCoords.width * this.pdfToImageScale);
        const imageHeight = Math.round(pdfCoords.height * this.pdfToImageScale);
        
        return new ImageCoordinates(imageLeft, imageTop, imageWidth, imageHeight, this.pageMetadata.imageDpi);
    }

    /**
     * Transform image coordinates back to PDF coordinates.
     * Both use top-left origin, so no Y-axis flip needed!
     */
    imageToPdf(imageCoords) {
        // Convert pixels to points - simple scaling, no coordinate system changes
        const pdfLeft = imageCoords.left * this.imageToPdfScale;
        const pdfTop = imageCoords.top * this.imageToPdfScale;
        const pdfWidth = imageCoords.width * this.imageToPdfScale;
        const pdfHeight = imageCoords.height * this.imageToPdfScale;
        
        return new PDFCoordinates(pdfLeft, pdfTop, pdfWidth, pdfHeight);
    }

    /**
     * Transform image coordinates to canvas coordinates.
     * Maintains aspect ratio using uniform scaling.
     */
    imageToCanvas(imageCoords, canvasWidth, canvasHeight) {
        // Calculate scale factors
        const scaleX = canvasWidth / this.pageMetadata.imageWidthPixels;
        const scaleY = canvasHeight / this.pageMetadata.imageHeightPixels;
        
        // Use uniform scale to maintain aspect ratio
        const scale = Math.min(scaleX, scaleY);
        
        return new CanvasCoordinates(
            imageCoords.left * scale,
            imageCoords.top * scale,
            imageCoords.width * scale,
            imageCoords.height * scale,
            canvasWidth,
            canvasHeight
        );
    }

    /**
     * Transform canvas coordinates back to image coordinates.
     * Reverses the uniform scaling applied in imageToCanvas.
     */
    canvasToImage(canvasCoords) {
        // Calculate reverse scale factors
        const scaleX = canvasCoords.canvasWidth / this.pageMetadata.imageWidthPixels;
        const scaleY = canvasCoords.canvasHeight / this.pageMetadata.imageHeightPixels;
        
        // Use uniform scale (same as forward transformation)
        const scale = Math.min(scaleX, scaleY);
        
        return new ImageCoordinates(
            Math.round(canvasCoords.left / scale),
            Math.round(canvasCoords.top / scale),
            Math.round(canvasCoords.width / scale),
            Math.round(canvasCoords.height / scale),
            this.pageMetadata.imageDpi
        );
    }

    /**
     * Transform canvas coordinates directly to PDF coordinates.
     * Convenience method that combines canvasToImage and imageToPdf.
     */
    canvasToPdf(canvasCoords) {
        const imageCoords = this.canvasToImage(canvasCoords);
        return this.imageToPdf(imageCoords);
    }

    /**
     * Transform PDF coordinates directly to canvas coordinates.
     * Convenience method that combines pdfToImage and imageToCanvas.
     */
    pdfToCanvas(pdfCoords, canvasWidth, canvasHeight) {
        const imageCoords = this.pdfToImage(pdfCoords);
        return this.imageToCanvas(imageCoords, canvasWidth, canvasHeight);
    }

    /**
     * Calculate optimal canvas dimensions that maintain image aspect ratio.
     * Used by frontend to determine proper canvas sizing.
     */
    getCanvasDimensionsForAspectRatio(maxWidth, maxHeight) {
        const imageAspectRatio = this.pageMetadata.imageWidthPixels / this.pageMetadata.imageHeightPixels;
        const maxAspectRatio = maxWidth / maxHeight;
        
        let canvasWidth, canvasHeight;
        
        if (imageAspectRatio > maxAspectRatio) {
            // Image is wider - fit to width
            canvasWidth = maxWidth;
            canvasHeight = maxWidth / imageAspectRatio;
        } else {
            // Image is taller - fit to height
            canvasHeight = maxHeight;
            canvasWidth = maxHeight * imageAspectRatio;
        }
        
        return { width: canvasWidth, height: canvasHeight };
    }
}

/**
 * Handles coordinate transformations within legend clippings.
 * Used for symbol annotations that occur within extracted legend images.
 */
export class ClippingCoordinateTransformer {
    constructor(legendPdfCoords, clippingDpi, pageMetadata) {
        this.legendPdfCoords = legendPdfCoords;
        this.clippingDpi = clippingDpi;
        this.pageMetadata = pageMetadata;
        
        // Calculate clipping dimensions in pixels
        this.clippingWidthPixels = Math.round(legendPdfCoords.width * clippingDpi / 72.0);
        this.clippingHeightPixels = Math.round(legendPdfCoords.height * clippingDpi / 72.0);
        
        // Pre-calculate scale factors
        this.pointsPerPixel = 72.0 / clippingDpi;
    }

    /**
     * Transform symbol annotation coordinates to absolute PDF coordinates.
     * This is the key method for mapping symbols back to the original PDF.
     */
    symbolCanvasToPdf(symbolCanvasCoords) {
        // Step 1: Canvas → Clipping image coordinates
        const clippingCoords = this.canvasToClipping(symbolCanvasCoords);
        
        // Step 2: Clipping image coordinates → PDF coordinates
        return this.clippingToPdf(clippingCoords);
    }

    /**
     * Transform canvas coordinates to clipping image coordinates.
     */
    canvasToClipping(canvasCoords) {
        // Calculate canvas scale factor (maintaining aspect ratio)
        const canvasScaleX = canvasCoords.canvasWidth / this.clippingWidthPixels;
        const canvasScaleY = canvasCoords.canvasHeight / this.clippingHeightPixels;
        const canvasScale = Math.min(canvasScaleX, canvasScaleY);
        
        // Transform to clipping coordinates
        const clippingLeft = Math.round(canvasCoords.left / canvasScale);
        const clippingTop = Math.round(canvasCoords.top / canvasScale);
        const clippingWidth = Math.round(canvasCoords.width / canvasScale);
        const clippingHeight = Math.round(canvasCoords.height / canvasScale);
        
        return new ClippingCoordinates(
            clippingLeft, clippingTop, clippingWidth, clippingHeight, this.clippingDpi
        );
    }

    /**
     * Transform clipping coordinates to absolute PDF coordinates.
     */
    clippingToPdf(clippingCoords) {
        // Convert clipping pixels to points
        const pdfXOffset = clippingCoords.leftPixels * this.pointsPerPixel;
        const pdfYOffset = clippingCoords.topPixels * this.pointsPerPixel;
        const pdfSymbolWidth = clippingCoords.widthPixels * this.pointsPerPixel;
        const pdfSymbolHeight = clippingCoords.heightPixels * this.pointsPerPixel;
        
        // Add legend offset to get absolute PDF coordinates
        // Note: Clipping coordinates have same origin as PDF (top-left of clipping = top-left of legend in PDF space)
        const absolutePdfLeft = this.legendPdfCoords.left + pdfXOffset;
        const absolutePdfTop = this.legendPdfCoords.top + pdfYOffset;
        
        return new PDFCoordinates(absolutePdfLeft, absolutePdfTop, pdfSymbolWidth, pdfSymbolHeight);
    }

    /**
     * Transform absolute PDF coordinates to clipping coordinates.
     * Used for reverse transformations if needed.
     */
    pdfToClipping(pdfCoords) {
        // Calculate relative position within legend
        const pdfXOffset = pdfCoords.left - this.legendPdfCoords.left;
        const pdfYOffset = pdfCoords.top - this.legendPdfCoords.top;
        
        // Convert to clipping pixels
        const clippingLeft = Math.round(pdfXOffset / this.pointsPerPixel);
        const clippingTop = Math.round(pdfYOffset / this.pointsPerPixel);
        const clippingWidth = Math.round(pdfCoords.width / this.pointsPerPixel);
        const clippingHeight = Math.round(pdfCoords.height / this.pointsPerPixel);
        
        return new ClippingCoordinates(
            clippingLeft, clippingTop, clippingWidth, clippingHeight, this.clippingDpi
        );
    }
}

/**
 * Validate coordinate objects for basic sanity checks.
 */
export function validateCoordinates(coords, coordType) {
    if (coordType === "pdf") {
        return coords.width > 0 && coords.height > 0 && coords.left >= 0 && coords.top >= 0;
    } else if (coordType === "image") {
        return coords.width > 0 && coords.height > 0 && coords.left >= 0 && coords.top >= 0 && coords.dpi > 0;
    } else if (coordType === "canvas") {
        return coords.width > 0 && coords.height > 0 && coords.left >= 0 && coords.top >= 0 && 
               coords.canvasWidth > 0 && coords.canvasHeight > 0;
    } else if (coordType === "clipping") {
        return coords.widthPixels > 0 && coords.heightPixels > 0 && coords.leftPixels >= 0 && 
               coords.topPixels >= 0 && coords.clippingDpi > 0;
    }
    
    return false;
}

/**
 * Utility function to create PageMetadata from backend response
 */
export function createPageMetadata(backendData) {
    return new PageMetadata(backendData);
}

/**
 * Utility function to get canvas dimensions for a page
 */
export function getOptimalCanvasDimensions(pageMetadata, maxWidth = MAX_CANVAS_WIDTH, maxHeight = MAX_CANVAS_HEIGHT) {
    const transformer = new CoordinateTransformer(pageMetadata);
    return transformer.getCanvasDimensionsForAspectRatio(maxWidth, maxHeight);
} 