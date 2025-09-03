import os
import uuid
import fitz  # PyMuPDF
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from utils.pdf_processor import PDFProcessor
from utils.coordinate_mapping import PageMetadata, DEFAULT_DPI, HIGH_RES_DPI


router = APIRouter(prefix="/api", tags=["documents"])


# Use repository root for storage to match legacy layout
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
UPLOADS_DIR = os.path.join(REPO_ROOT, "uploads")
PROCESSED_DIR = os.path.join(REPO_ROOT, "data", "processed")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def _process_document_task(temp_pdf_path: str, doc_id: str) -> None:
    try:
        output_dir = os.path.join(PROCESSED_DIR, doc_id)
        os.makedirs(output_dir, exist_ok=True)

        pdf_processor = PDFProcessor(dpi=300, high_res_dpi=300)
        pdf_processor.process_pdf(temp_pdf_path, output_dir, doc_id)

        # Create legacy page images and standard page metadata for UI
        doc = fitz.open(temp_pdf_path)
        num_pages = len(doc)

        page_metadata: Dict[int, Dict[str, Any]] = {}
        dpi = DEFAULT_DPI

        for page_num in range(num_pages):
            page = doc.load_page(page_num)
            page_number = page_num + 1

            pdf_rect = page.rect

            image_width_pixels = int(pdf_rect.width * dpi / 72.0)
            image_height_pixels = int(pdf_rect.height * dpi / 72.0)
            high_res_width_pixels = int(pdf_rect.width * HIGH_RES_DPI / 72.0)
            high_res_height_pixels = int(pdf_rect.height * HIGH_RES_DPI / 72.0)

            page_meta = PageMetadata(
                page_number=page_number,
                pdf_width_points=pdf_rect.width,
                pdf_height_points=pdf_rect.height,
                pdf_rotation_degrees=page.rotation,
                image_width_pixels=image_width_pixels,
                image_height_pixels=image_height_pixels,
                image_dpi=dpi,
                high_res_image_width_pixels=high_res_width_pixels,
                high_res_image_height_pixels=high_res_height_pixels,
                high_res_dpi=HIGH_RES_DPI,
            )

            pix = page.get_pixmap(dpi=dpi)
            image_path = os.path.join(output_dir, f"page_{page_number}.png")
            pix.save(image_path)

            page_metadata[page_number] = page_meta.to_dict()

        # Save page metadata & original PDF
        import json

        with open(os.path.join(output_dir, "page_metadata.json"), "w") as f:
            json.dump({"docId": doc_id, "totalPages": num_pages, "pages": page_metadata}, f, indent=2)

        # Save original PDF copy into processed dir
        try:
            import shutil

            shutil.copyfile(temp_pdf_path, os.path.join(output_dir, "original.pdf"))
        except Exception:
            pass
    finally:
        # Clean up temp upload
        try:
            os.remove(temp_pdf_path)
        except Exception:
            pass


@router.post("/documents/")
async def create_document(background_tasks: BackgroundTasks, file: UploadFile) -> Dict[str, Any]:
    if not file or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF file is required")

    doc_id = str(uuid.uuid4())
    temp_pdf_path = os.path.join(UPLOADS_DIR, file.filename)

    try:
        # Save upload to disk
        with open(temp_pdf_path, "wb") as out:
            out.write(await file.read())

        # Kick off background processing
        background_tasks.add_task(_process_document_task, temp_pdf_path=temp_pdf_path, doc_id=doc_id)

        return {"message": "File received. Processing started.", "docId": doc_id}
    except Exception as e:
        # cleanup temp file on error
        try:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


