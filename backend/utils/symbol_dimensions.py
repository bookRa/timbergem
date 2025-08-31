"""
Symbol Dimension Calculator for TimberGem

This module calculates the actual dimensions of symbol templates by analyzing
the non-white pixels (contours) in symbol images at 300 DPI.
"""

import numpy as np
import cv2
import fitz  # PyMuPDF
from PIL import Image
from typing import Tuple, Optional, Dict
from .coordinate_mapping import PDFCoordinates


class SymbolDimensionCalculator:
    """
    Calculates the actual dimensions of symbol templates by analyzing contours
    in the symbol images. Uses 300 DPI as the standard for measurements.
    """

    STANDARD_DPI = 300

    def __init__(self):
        pass

    def calculate_dimensions_from_pdf(
        self, pdf_document: fitz.Document, page_number: int, pdf_coords: PDFCoordinates
    ) -> Dict[str, int]:
        """
        Calculate symbol dimensions by extracting from PDF and analyzing contours.

        Args:
            pdf_document: The PDF document object
            page_number: Page number (1-indexed)
            pdf_coords: PDF coordinates of the symbol

        Returns:
            Dict with height_pixels_300dpi and width_pixels_300dpi
        """
        try:
            # Load the page (convert to 0-indexed)
            page = pdf_document[page_number - 1]

            # Create rectangle for symbol clipping
            symbol_rect = fitz.Rect(
                pdf_coords.left,
                pdf_coords.top,
                pdf_coords.left + pdf_coords.width,
                pdf_coords.top + pdf_coords.height,
            )

            # Extract symbol at 300 DPI
            symbol_pix = page.get_pixmap(clip=symbol_rect, dpi=self.STANDARD_DPI)

            # Convert to numpy array for contour analysis
            img_data = np.frombuffer(symbol_pix.samples, dtype=np.uint8).reshape(
                symbol_pix.h, symbol_pix.w, symbol_pix.n
            )

            # Calculate dimensions using contour analysis
            return self._analyze_contours(img_data)

        except Exception as e:
            print(f"Error calculating dimensions from PDF: {e}")
            return {"height_pixels_300dpi": 0, "width_pixels_300dpi": 0}

    def calculate_dimensions_from_image(self, image: Image.Image) -> Dict[str, int]:
        """
        Calculate symbol dimensions from a PIL Image by analyzing contours.

        Args:
            image: PIL Image of the symbol

        Returns:
            Dict with height_pixels_300dpi and width_pixels_300dpi
        """
        try:
            # Convert PIL Image to numpy array
            img_array = np.array(image)

            # If image has alpha channel, remove it
            if img_array.shape[2] == 4:
                img_array = img_array[:, :, :3]

            return self._analyze_contours(img_array)

        except Exception as e:
            print(f"Error calculating dimensions from image: {e}")
            return {"height_pixels_300dpi": 0, "width_pixels_300dpi": 0}

    def _analyze_contours(self, img_data: np.ndarray) -> Dict[str, int]:
        """
        Analyze contours in the image data to find actual symbol dimensions.

        Args:
            img_data: Numpy array of image data

        Returns:
            Dict with height_pixels_300dpi and width_pixels_300dpi
        """
        try:
            # Convert to grayscale if needed
            if len(img_data.shape) == 3 and img_data.shape[2] > 1:
                gray_image = cv2.cvtColor(img_data, cv2.COLOR_RGB2GRAY)
            else:
                gray_image = img_data.reshape(img_data.shape[0], img_data.shape[1])

            # Find contours (invert image so dark pixels become foreground)
            contours, _ = cv2.findContours(
                cv2.bitwise_not(gray_image), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                # Combine all contours to get the overall bounding box
                all_points = np.concatenate([cnt for cnt in contours])
                x, y, w, h = cv2.boundingRect(all_points)

                return {"height_pixels_300dpi": int(h), "width_pixels_300dpi": int(w)}
            else:
                # No contours found, return zero dimensions
                return {"height_pixels_300dpi": 0, "width_pixels_300dpi": 0}

        except Exception as e:
            print(f"Error analyzing contours: {e}")
            return {"height_pixels_300dpi": 0, "width_pixels_300dpi": 0}
    
    def generate_tight_template(self, image_path: str, output_path: str) -> Dict[str, any]:
        """
        Generate a tightly-cropped template from a symbol image by removing whitespace.
        
        Args:
            image_path: Path to the original symbol clipping
            output_path: Path where the tight template should be saved
            
        Returns:
            Dict containing:
                - template_dimensions: {width_pixels_300dpi, height_pixels_300dpi}
                - crop_offset: {left, top} - offset from original to template
                - success: boolean indicating if generation was successful
        """
        try:
            print(f"🔍 Generating tight template from: {image_path}")
            
            # Load the original image
            image = Image.open(image_path)
            img_array = np.array(image)
            
            # Handle alpha channel
            if img_array.shape[2] == 4:
                img_array = img_array[:, :, :3]
            
            # Convert to grayscale for contour detection
            if len(img_array.shape) == 3 and img_array.shape[2] > 1:
                gray_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray_image = img_array.reshape(img_array.shape[0], img_array.shape[1])
            
            # Find contours (invert so dark pixels are foreground)
            contours, _ = cv2.findContours(
                cv2.bitwise_not(gray_image), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                print(f"❌ No contours found in {image_path}")
                return {
                    "template_dimensions": {"width_pixels_300dpi": 0, "height_pixels_300dpi": 0},
                    "crop_offset": {"left": 0, "top": 0},
                    "success": False
                }
            
            # Get combined bounding box of all contours
            all_points = np.concatenate([cnt for cnt in contours])
            x, y, w, h = cv2.boundingRect(all_points)
            
            print(f"📐 Detected symbol bounds: ({x}, {y}) {w}x{h} pixels")
            
            # Add small padding (2-3 pixels) to ensure complete symbol capture
            padding = 2
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img_array.shape[1] - x, w + 2 * padding)
            h = min(img_array.shape[0] - y, h + 2 * padding)
            
            # Crop the original image to the tight bounds
            if len(img_array.shape) == 3:
                cropped_image = img_array[y:y+h, x:x+w, :]
            else:
                cropped_image = img_array[y:y+h, x:x+w]
            
            # Save the tight template
            cropped_pil = Image.fromarray(cropped_image)
            cropped_pil.save(output_path)
            
            print(f"✅ Tight template saved: {output_path}")
            print(f"📏 Template dimensions: {w}x{h} pixels")
            print(f"📍 Crop offset: ({x}, {y}) from original")
            
            return {
                "template_dimensions": {"width_pixels_300dpi": int(w), "height_pixels_300dpi": int(h)},
                "crop_offset": {"left": int(x), "top": int(y)},
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Error generating tight template: {e}")
            return {
                "template_dimensions": {"width_pixels_300dpi": 0, "height_pixels_300dpi": 0},
                "crop_offset": {"left": 0, "top": 0},
                "success": False
            }


def calculate_symbol_dimensions_from_pdf(
    pdf_document: fitz.Document, page_number: int, pdf_coords: PDFCoordinates
) -> Dict[str, int]:
    """
    Convenience function to calculate symbol dimensions from PDF coordinates.

    Args:
        pdf_document: The PDF document object
        page_number: Page number (1-indexed)
        pdf_coords: PDF coordinates of the symbol

    Returns:
        Dict with height_pixels_300dpi and width_pixels_300dpi
    """
    calculator = SymbolDimensionCalculator()
    return calculator.calculate_dimensions_from_pdf(
        pdf_document, page_number, pdf_coords
    )


def calculate_symbol_dimensions_from_image(image: Image.Image) -> Dict[str, int]:
    """
    Convenience function to calculate symbol dimensions from a PIL Image.

    Args:
        image: PIL Image of the symbol

    Returns:
        Dict with height_pixels_300dpi and width_pixels_300dpi
    """
    calculator = SymbolDimensionCalculator()
    return calculator.calculate_dimensions_from_image(image)
