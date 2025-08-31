"""
TimberGem Coordinate Mapping System

This module provides a centralized, clean coordinate transformation system for TimberGem.
PDF coordinates (in points) are the single source of truth, with clear transformations
to image coordinates (pixels) and canvas coordinates (UI pixels).

Key Principles:
- PDF coordinates: top-left origin, points (72 DPI) - PyMuPDF uses top-left, not bottom-left!
- Image coordinates: top-left origin, pixels at specific DPI
- Canvas coordinates: top-left origin, scaled pixels for UI display
"""

from dataclasses import dataclass, asdict
from typing import Dict, Tuple
import math


@dataclass
class PDFCoordinates:
    """
    PDF coordinates in points (72 DPI), origin at top-left.
    This is the single source of truth for all coordinate systems.
    Note: PyMuPDF uses top-left origin, not the PDF standard's bottom-left!
    """

    left: float
    top: float
    width: float
    height: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "left_points": self.left,
            "top_points": self.top,
            "width_points": self.width,
            "height_points": self.height,
        }

    def to_rect_tuple(self) -> Tuple[float, float, float, float]:
        """Return as (x0, y0, x1, y1) tuple for PyMuPDF Rect"""
        return (self.left, self.top, self.left + self.width, self.top + self.height)


@dataclass
class ImageCoordinates:
    """
    Image coordinates in pixels at specific DPI, origin at top-left.
    Used for pixmap generation and image-based operations.
    """

    left: int
    top: int
    width: int
    height: int
    dpi: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "left_pixels": self.left,
            "top_pixels": self.top,
            "width_pixels": self.width,
            "height_pixels": self.height,
            "dpi": self.dpi,
        }


@dataclass
class CanvasCoordinates:
    """
    Canvas coordinates in pixels for UI display, origin at top-left.
    Includes canvas dimensions for scale calculations.
    """

    left: float
    top: float
    width: float
    height: float
    canvas_width: float
    canvas_height: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "left_canvas_pixels": self.left,
            "top_canvas_pixels": self.top,
            "width_canvas_pixels": self.width,
            "height_canvas_pixels": self.height,
            "canvas_width_pixels": self.canvas_width,
            "canvas_height_pixels": self.canvas_height,
        }


@dataclass
class ClippingCoordinates:
    """
    Coordinates within a legend clipping image (pixels at clipping DPI).
    Used for symbol annotations within extracted legend clippings.
    """

    left_pixels: int
    top_pixels: int
    width_pixels: int
    height_pixels: int
    clipping_dpi: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "left_clipping_pixels": self.left_pixels,
            "top_clipping_pixels": self.top_pixels,
            "width_clipping_pixels": self.width_pixels,
            "height_clipping_pixels": self.height_pixels,
            "clipping_dpi": self.clipping_dpi,
        }


@dataclass
class PageMetadata:
    """
    Complete page metadata for coordinate transformations.
    Contains all information needed for accurate coordinate mapping.
    """

    page_number: int

    # PDF properties (points, 72 DPI)
    pdf_width_points: float
    pdf_height_points: float
    pdf_rotation_degrees: int

    # Standard image properties (for display)
    image_width_pixels: int
    image_height_pixels: int
    image_dpi: int

    # High-resolution image properties (for clipping extraction)
    high_res_image_width_pixels: int
    high_res_image_height_pixels: int
    high_res_dpi: int

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "PageMetadata":
        return cls(**data)


class CoordinateTransformer:
    """
    Centralized coordinate transformation engine.
    Handles all transformations between PDF, image, and canvas coordinate systems.
    """

    def __init__(self, page_metadata: PageMetadata):
        self.page_metadata = page_metadata

        # Pre-calculate transformation factors for efficiency
        self.pdf_to_image_scale = self._calculate_pdf_to_image_scale()
        self.image_to_pdf_scale = 1.0 / self.pdf_to_image_scale

        self.pdf_to_high_res_scale = self._calculate_pdf_to_high_res_scale()
        self.high_res_to_pdf_scale = 1.0 / self.pdf_to_high_res_scale

    def _calculate_pdf_to_image_scale(self) -> float:
        """Calculate scale factor from PDF points to standard image pixels"""
        return self.page_metadata.image_dpi / 72.0  # 72 points per inch

    def _calculate_pdf_to_high_res_scale(self) -> float:
        """Calculate scale factor from PDF points to high-res image pixels"""
        return self.page_metadata.high_res_dpi / 72.0

    def pdf_to_image(self, pdf_coords: PDFCoordinates) -> ImageCoordinates:
        """
        Transform PDF coordinates to standard image coordinates.
        Both use top-left origin, so no Y-axis flip needed!
        """
        # Convert points to pixels - simple scaling, no coordinate system changes
        image_left = int(pdf_coords.left * self.pdf_to_image_scale)
        image_top = int(pdf_coords.top * self.pdf_to_image_scale)
        image_width = int(pdf_coords.width * self.pdf_to_image_scale)
        image_height = int(pdf_coords.height * self.pdf_to_image_scale)

        return ImageCoordinates(
            left=image_left,
            top=image_top,
            width=image_width,
            height=image_height,
            dpi=self.page_metadata.image_dpi,
        )

    def image_to_pdf(self, image_coords: ImageCoordinates) -> PDFCoordinates:
        """
        Transform image coordinates back to PDF coordinates.
        Both use top-left origin, so no Y-axis flip needed!
        """
        # Use the actual DPI of the image coordinates to scale back to points.
        # This ensures 300 DPI detection/image coords map correctly even if the
        # page's standard image_dpi differs.
        points_per_pixel = 72.0 / float(image_coords.dpi)

        pdf_left = image_coords.left * points_per_pixel
        pdf_top = image_coords.top * points_per_pixel
        pdf_width = image_coords.width * points_per_pixel
        pdf_height = image_coords.height * points_per_pixel

        return PDFCoordinates(
            left=pdf_left, top=pdf_top, width=pdf_width, height=pdf_height
        )

    def image_to_canvas(
        self, image_coords: ImageCoordinates, canvas_width: float, canvas_height: float
    ) -> CanvasCoordinates:
        """
        Transform image coordinates to canvas coordinates.
        Maintains aspect ratio using uniform scaling.
        """
        # Calculate scale factors
        scale_x = canvas_width / self.page_metadata.image_width_pixels
        scale_y = canvas_height / self.page_metadata.image_height_pixels

        # Use uniform scale to maintain aspect ratio
        scale = min(scale_x, scale_y)

        return CanvasCoordinates(
            left=image_coords.left * scale,
            top=image_coords.top * scale,
            width=image_coords.width * scale,
            height=image_coords.height * scale,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )

    def canvas_to_image(self, canvas_coords: CanvasCoordinates) -> ImageCoordinates:
        """
        Transform canvas coordinates back to image coordinates.
        Reverses the uniform scaling applied in image_to_canvas.
        """
        # Calculate reverse scale factors
        scale_x = canvas_coords.canvas_width / self.page_metadata.image_width_pixels
        scale_y = canvas_coords.canvas_height / self.page_metadata.image_height_pixels

        # Use uniform scale (same as forward transformation)
        scale = min(scale_x, scale_y)

        return ImageCoordinates(
            left=int(canvas_coords.left / scale),
            top=int(canvas_coords.top / scale),
            width=int(canvas_coords.width / scale),
            height=int(canvas_coords.height / scale),
            dpi=self.page_metadata.image_dpi,
        )

    def canvas_to_pdf(self, canvas_coords: CanvasCoordinates) -> PDFCoordinates:
        """
        Transform canvas coordinates directly to PDF coordinates.
        Convenience method that combines canvas_to_image and image_to_pdf.
        """
        image_coords = self.canvas_to_image(canvas_coords)
        return self.image_to_pdf(image_coords)

    def pdf_to_canvas(
        self, pdf_coords: PDFCoordinates, canvas_width: float, canvas_height: float
    ) -> CanvasCoordinates:
        """
        Transform PDF coordinates directly to canvas coordinates.
        Convenience method that combines pdf_to_image and image_to_canvas.
        """
        image_coords = self.pdf_to_image(pdf_coords)
        return self.image_to_canvas(image_coords, canvas_width, canvas_height)

    def get_canvas_dimensions_for_aspect_ratio(
        self, max_width: float, max_height: float
    ) -> Tuple[float, float]:
        """
        Calculate optimal canvas dimensions that maintain image aspect ratio.
        Used by frontend to determine proper canvas sizing.
        """
        image_aspect_ratio = (
            self.page_metadata.image_width_pixels
            / self.page_metadata.image_height_pixels
        )
        max_aspect_ratio = max_width / max_height

        if image_aspect_ratio > max_aspect_ratio:
            # Image is wider - fit to width
            canvas_width = max_width
            canvas_height = max_width / image_aspect_ratio
        else:
            # Image is taller - fit to height
            canvas_height = max_height
            canvas_width = max_height * image_aspect_ratio

        return canvas_width, canvas_height


class ClippingCoordinateTransformer:
    """
    Handles coordinate transformations within legend clippings.
    Used for symbol annotations that occur within extracted legend images.
    """

    def __init__(
        self,
        legend_pdf_coords: PDFCoordinates,
        clipping_dpi: int,
        page_metadata: PageMetadata,
    ):
        self.legend_pdf_coords = legend_pdf_coords
        self.clipping_dpi = clipping_dpi
        self.page_metadata = page_metadata

        # Calculate clipping dimensions in pixels
        self.clipping_width_pixels = int(legend_pdf_coords.width * clipping_dpi / 72.0)
        self.clipping_height_pixels = int(
            legend_pdf_coords.height * clipping_dpi / 72.0
        )

        # Pre-calculate scale factors
        self.points_per_pixel = 72.0 / clipping_dpi

    def symbol_canvas_to_pdf(
        self, symbol_canvas_coords: CanvasCoordinates
    ) -> PDFCoordinates:
        """
        Transform symbol annotation coordinates to absolute PDF coordinates.
        This is the key method for mapping symbols back to the original PDF.
        """
        # Step 1: Canvas → Clipping image coordinates
        clipping_coords = self.canvas_to_clipping(symbol_canvas_coords)

        # Step 2: Clipping image coordinates → PDF coordinates
        return self.clipping_to_pdf(clipping_coords)

    def canvas_to_clipping(
        self, canvas_coords: CanvasCoordinates
    ) -> ClippingCoordinates:
        """
        Transform canvas coordinates to clipping image coordinates.
        """
        # Calculate canvas scale factor (maintaining aspect ratio)
        canvas_scale_x = canvas_coords.canvas_width / self.clipping_width_pixels
        canvas_scale_y = canvas_coords.canvas_height / self.clipping_height_pixels
        canvas_scale = min(canvas_scale_x, canvas_scale_y)

        # Transform to clipping coordinates
        clipping_left = int(canvas_coords.left / canvas_scale)
        clipping_top = int(canvas_coords.top / canvas_scale)
        clipping_width = int(canvas_coords.width / canvas_scale)
        clipping_height = int(canvas_coords.height / canvas_scale)

        return ClippingCoordinates(
            left_pixels=clipping_left,
            top_pixels=clipping_top,
            width_pixels=clipping_width,
            height_pixels=clipping_height,
            clipping_dpi=self.clipping_dpi,
        )

    def clipping_to_pdf(self, clipping_coords: ClippingCoordinates) -> PDFCoordinates:
        """
        Transform clipping coordinates to absolute PDF coordinates.
        """
        # Convert clipping pixels to points
        pdf_x_offset = clipping_coords.left_pixels * self.points_per_pixel
        pdf_y_offset = clipping_coords.top_pixels * self.points_per_pixel
        pdf_symbol_width = clipping_coords.width_pixels * self.points_per_pixel
        pdf_symbol_height = clipping_coords.height_pixels * self.points_per_pixel

        # Add legend offset to get absolute PDF coordinates
        # Note: Clipping coordinates have same origin as PDF (top-left of clipping = top-left of legend in PDF space)
        absolute_pdf_left = self.legend_pdf_coords.left + pdf_x_offset
        absolute_pdf_top = self.legend_pdf_coords.top + pdf_y_offset

        return PDFCoordinates(
            left=absolute_pdf_left,
            top=absolute_pdf_top,
            width=pdf_symbol_width,
            height=pdf_symbol_height,
        )

    def pdf_to_clipping(self, pdf_coords: PDFCoordinates) -> ClippingCoordinates:
        """
        Transform absolute PDF coordinates to clipping coordinates.
        Used for reverse transformations if needed.
        """
        # Calculate relative position within legend
        pdf_x_offset = pdf_coords.left - self.legend_pdf_coords.left
        pdf_y_offset = pdf_coords.top - self.legend_pdf_coords.top

        # Convert to clipping pixels
        clipping_left = int(pdf_x_offset / self.points_per_pixel)
        clipping_top = int(pdf_y_offset / self.points_per_pixel)
        clipping_width = int(pdf_coords.width / self.points_per_pixel)
        clipping_height = int(pdf_coords.height / self.points_per_pixel)

        return ClippingCoordinates(
            left_pixels=clipping_left,
            top_pixels=clipping_top,
            width_pixels=clipping_width,
            height_pixels=clipping_height,
            clipping_dpi=self.clipping_dpi,
        )


def validate_coordinates(coords, coord_type: str) -> bool:
    """
    Validate coordinate objects for basic sanity checks.
    """
    if coord_type == "pdf":
        return (
            coords.width > 0
            and coords.height > 0
            and coords.left >= 0
            and coords.top >= 0
        )
    elif coord_type == "image":
        return (
            coords.width > 0
            and coords.height > 0
            and coords.left >= 0
            and coords.top >= 0
            and coords.dpi > 0
        )
    elif coord_type == "canvas":
        return (
            coords.width > 0
            and coords.height > 0
            and coords.left >= 0
            and coords.top >= 0
            and coords.canvas_width > 0
            and coords.canvas_height > 0
        )
    elif coord_type == "clipping":
        return (
            coords.width_pixels > 0
            and coords.height_pixels > 0
            and coords.left_pixels >= 0
            and coords.top_pixels >= 0
            and coords.clipping_dpi > 0
        )

    return False


# Constants
DEFAULT_DPI = 300
HIGH_RES_DPI = 300
POINTS_PER_INCH = 72.0
MAX_CANVAS_WIDTH = 1200
MAX_CANVAS_HEIGHT = 900
