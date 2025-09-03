import os
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.page_to_html_pipeline import PageToHTMLPipeline, PageToHTMLConfig


router = APIRouter(prefix="/api", tags=["page_to_html"])


# Use repository root for processed artifacts (aligns with legacy layout)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
PROCESSED_DIR = os.path.join(REPO_ROOT, "data", "processed")


class ProcessHTMLRequest(BaseModel):
    docId: str
    config: Optional[Dict[str, Any]] = None


@router.post("/process_pdf_to_html")
async def process_pdf_to_html(payload: ProcessHTMLRequest) -> Dict[str, Any]:
    doc_id = payload.docId
    config_data = payload.config or {}

    doc_dir = os.path.join(PROCESSED_DIR, doc_id)
    if not os.path.exists(doc_dir):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    original_pdf_path = os.path.join(doc_dir, "original.pdf")
    if not os.path.exists(original_pdf_path):
        raise HTTPException(status_code=404, detail=f"Original PDF not found for document {doc_id}")

    # Auto-load API keys from environment if not provided
    gemini_api_key = config_data.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
    openai_api_key = config_data.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    anthropic_api_key = config_data.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")

    config = PageToHTMLConfig(
        llm_provider=config_data.get("llm_provider", "mock"),
        llm_model=config_data.get("llm_model"),
        dpi=config_data.get("dpi", 300),
        high_res_dpi=config_data.get("high_res_dpi", 300),
        max_concurrent_requests=config_data.get("max_concurrent_requests", 7),
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
    )

    pipeline = PageToHTMLPipeline(config)
    results = await pipeline.process_pdf_to_html(original_pdf_path, doc_dir, doc_id)

    return {"message": "PDF processed to HTML successfully", "docId": doc_id, "results": results}


@router.get("/load_html_results/{doc_id}")
def load_html_results(doc_id: str) -> Dict[str, Any]:
    doc_dir = os.path.join(PROCESSED_DIR, doc_id)
    results_file = os.path.join(doc_dir, "page_to_html_results.json")
    if not os.path.exists(results_file):
        return {"docId": doc_id, "results": None, "message": "No HTML processing results found"}
    with open(results_file, "r") as f:
        results = json.load(f)
    return {"docId": doc_id, "results": results}


@router.get("/get_page_html/{doc_id}/{page_number}")
def get_page_html(doc_id: str, page_number: int) -> Dict[str, Any]:
    doc_dir = os.path.join(PROCESSED_DIR, doc_id)
    page_dir = os.path.join(doc_dir, f"page_{page_number}")
    html_file = os.path.join(page_dir, f"page_{page_number}.html")
    if not os.path.exists(html_file):
        raise HTTPException(status_code=404, detail=f"HTML file not found for document {doc_id}, page {page_number}")
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    return {"docId": doc_id, "pageNumber": page_number, "htmlContent": html_content, "htmlFilePath": html_file}


