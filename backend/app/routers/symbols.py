from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os
import json


router = APIRouter(prefix="/api", tags=["symbols"])


# Storage roots (repo root)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
UPLOADS_DIR = os.path.join(REPO_ROOT, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


class BoundingBox(BaseModel):
    left: float
    top: float
    width: float
    height: float


class SymbolDefinitionCreate(BaseModel):
    name: str = Field(..., description="Human-readable symbol name")
    description: Optional[str] = Field(None, description="Description of the symbol")
    source_sheet_number: Optional[str] = Field(
        None, description="Sheet number where the definition was captured (e.g., a2.10)"
    )
    bounding_box: Optional[BoundingBox] = Field(
        None, description="Bounding box on the source sheet in canvas or pdf coords"
    )
    scope: str = Field(
        ..., description="'project' for global or a specific sheet number like 'a2.10'"
    )


def _load_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


@router.post("/symbol_definitions")
def create_symbol_definition(payload: SymbolDefinitionCreate) -> Dict[str, Any]:
    # File-based storage (temporary while migrating off Flask)
    # Neo4j implementation intentionally commented out.
    bbox = payload.bounding_box.dict() if payload.bounding_box else None

    # Determine scope doc folder if provided in source_sheet_number; fallback to global
    # Caller should include doc_id in request body in future; for now, store globally if not provided.
    doc_id = os.getenv("TG_ACTIVE_DOC_ID")  # optional override
    target_dir = os.path.join(UPLOADS_DIR, doc_id) if doc_id else UPLOADS_DIR
    os.makedirs(target_dir, exist_ok=True)

    dest = os.path.join(target_dir, "symbol_definitions.json")
    data = _load_json(dest) or {"definitions": []}
    new_def = {
        "name": payload.name,
        "description": payload.description,
        "source_sheet_number": payload.source_sheet_number,
        "scope": payload.scope,
        "bounding_box": bbox,
    }
    data["definitions"].append(new_def)
    with open(dest, "w") as f:
        json.dump(data, f, indent=2)

    return new_def


# Placeholder: Copy over detection logic from Flask (detect_symbols_on_page)
def detect_symbols_on_page(doc_dir: str, page_number: int) -> Dict[str, Any]:
    """
    Placeholder detection function. Replace with the real logic ported from Flask
    when available. For now, returns an empty detection set for the page.
    """
    return {"page": page_number, "detections": []}


@router.post("/documents/{doc_id}/detect_symbols")
def detect_symbols(doc_id: str) -> Dict[str, Any]:
    """
    File-based detection endpoint. Loads symbol definitions and runs detection for pages.
    Saves results into uploads/{doc_id}/detected_symbols.json
    """
    doc_dir = os.path.join(UPLOADS_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    # Load definitions if present
    defs_path = os.path.join(doc_dir, "symbol_definitions.json")
    definitions = _load_json(defs_path) or {"definitions": []}

    # For now, call a simple placeholder that returns empty results for page 1.
    results = {"docId": doc_id, "results": [detect_symbols_on_page(doc_dir, 1)]}

    out_path = os.path.join(doc_dir, "detected_symbols.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


