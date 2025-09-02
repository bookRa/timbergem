import os
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api", tags=["sheets"])


_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
_PROCESSED_DIR = os.path.join(_BASE_DIR, "data", "processed")


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


@router.get("/documents/{doc_id}/pages")
def list_document_pages(doc_id: str) -> Dict[str, Any]:
    doc_dir = os.path.join(_PROCESSED_DIR, doc_id)
    meta_path = os.path.join(doc_dir, "page_metadata.json")
    if not os.path.exists(doc_dir) or not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Document or metadata not found")

    metadata = _read_json(meta_path) or {}
    pages_meta = metadata.get("pages", {})

    page_numbers: List[int] = []
    for k in pages_meta.keys():
        try:
            page_numbers.append(int(k))
        except Exception:
            pass
    page_numbers.sort()

    pages: List[Dict[str, Any]] = []
    for pn in page_numbers:
        pm = pages_meta.get(str(pn), {})
        pages.append({
            "page_number": pn,
            "sheet_number": pm.get("sheet_number"),
            "title": pm.get("title"),
        })

    return {"docId": doc_id, "pages": pages}


@router.get("/documents/{doc_id}/pages/{page_number}/entities")
def list_page_entities(doc_id: str, page_number: int) -> Dict[str, Any]:
    doc_dir = os.path.join(_PROCESSED_DIR, doc_id)
    if not os.path.exists(doc_dir):
        raise HTTPException(status_code=404, detail="Document not found")

    annotations_path = os.path.join(doc_dir, "annotations.json")
    summaries_path = os.path.join(doc_dir, "summaries.json")
    entities_dir = os.path.join(doc_dir, "entities")
    page_entities_path = os.path.join(entities_dir, f"page_{page_number}.json")

    annotations_data = _read_json(annotations_path) or {}
    summaries_data = _read_json(summaries_path) or {}
    entities_file_data = _read_json(page_entities_path) or {}

    annotations = [a for a in annotations_data.get("annotations", []) if int(a.get("pageNumber", -1)) == page_number]
    summary_map = summaries_data.get("summaries", {})
    summary = summary_map.get(str(page_number)) or summary_map.get(page_number)

    return {
        "docId": doc_id,
        "pageNumber": page_number,
        "entities": {
            "annotations": annotations,
            "symbols": entities_file_data.get("symbols", []),
            "notes": entities_file_data.get("notes", []),
            "scopes": entities_file_data.get("scopes", []),
            "summary": summary,
        },
    }


