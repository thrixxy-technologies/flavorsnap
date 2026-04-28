from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/annotations", tags=["annotations"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_FILE = DATA_DIR / "annotations.json"


class Annotation(BaseModel):
    id: str
    type: Literal["bbox", "polygon"]
    coordinates: list[float] = Field(default_factory=list)
    label: str = Field(min_length=1, max_length=120)
    confidence: float | None = Field(default=None, ge=0, le=1)
    timestamp: datetime


class AnnotationDocument(BaseModel):
    imageId: str
    imageName: str
    imageWidth: int = Field(gt=0)
    imageHeight: int = Field(gt=0)
    imageUrl: str | None = None
    annotations: list[Annotation] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _read_documents() -> list[AnnotationDocument]:
    _ensure_storage()
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [AnnotationDocument.model_validate(item) for item in payload]


def _write_documents(documents: list[AnnotationDocument]) -> None:
    _ensure_storage()
    DATA_FILE.write_text(
        json.dumps([document.model_dump(mode="json") for document in documents], indent=2),
        encoding="utf-8",
    )


@router.get("", response_model=list[AnnotationDocument])
def list_annotations() -> list[AnnotationDocument]:
    return _read_documents()


@router.get("/{image_id}", response_model=AnnotationDocument)
def get_annotation(image_id: str) -> AnnotationDocument:
    for document in _read_documents():
        if document.imageId == image_id:
            return document
    raise HTTPException(status_code=404, detail="Annotations not found for this image.")


@router.post("", response_model=AnnotationDocument)
def save_annotation(document: AnnotationDocument) -> AnnotationDocument:
    documents = _read_documents()
    now = datetime.now(timezone.utc)
    updated_document = document.model_copy(update={"updatedAt": now})

    for index, existing in enumerate(documents):
        if existing.imageId == document.imageId:
            updated_document = updated_document.model_copy(update={"createdAt": existing.createdAt})
            documents[index] = updated_document
            _write_documents(documents)
            return updated_document

    documents.append(updated_document)
    _write_documents(documents)
    return updated_document
