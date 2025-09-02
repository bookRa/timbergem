from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from neo4j import GraphDatabase
import os


router = APIRouter(prefix="/api", tags=["symbols"])


# Neo4j connection config via env vars
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


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


def _neo4j_driver():
    try:
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j connection failed: {e}")


@router.post("/symbol_definitions")
def create_symbol_definition(payload: SymbolDefinitionCreate) -> Dict[str, Any]:
    driver = _neo4j_driver()

    bbox = payload.bounding_box.dict() if payload.bounding_box else None

    cypher = (
        "CREATE (s:SymbolDefinition {"
        "name: $name, "
        "description: $description, "
        "source_sheet_number: $source_sheet_number, "
        "scope: $scope, "
        "bounding_box: $bounding_box"
        "}) RETURN s"
    )

    params = {
        "name": payload.name,
        "description": payload.description,
        "source_sheet_number": payload.source_sheet_number,
        "scope": payload.scope,
        "bounding_box": bbox,
    }

    try:
        with driver.session() as session:
            result = session.run(cypher, **params)
            record = result.single()
            if not record:
                raise HTTPException(status_code=500, detail="Failed to create symbol definition")
            node = record["s"]
            return {
                "id": node.element_id if hasattr(node, "element_id") else node.id,
                **node._properties,  # type: ignore[attr-defined]
            }
    finally:
        driver.close()


