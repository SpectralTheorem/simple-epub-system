from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ChapterContent(BaseModel):
    """API model for rich chapter content as specified in DESIGN.md."""
    html: str
    text: str
    footnotes: List[Dict[str, str]] = []
    images: List[str] = []
    tables: List[Dict[str, Any]] = []


class ChapterResponse(BaseModel):
    """API model for chapter responses."""
    id: str
    document_id: str
    title: str
    content: ChapterContent
    order: int
    level: int
    parent_id: Optional[str] = None
    children: List[str] = []


class ChapterHierarchy(BaseModel):
    """Model for representing chapter hierarchy."""
    id: str
    title: str
    level: int
    order: int
    children: List['ChapterHierarchy'] = []


class ImageResponse(BaseModel):
    """API model for image responses."""
    id: str
    media_type: str


class DocumentResponse(BaseModel):
    """API model for document responses."""
    id: str
    title: str
    author: Optional[str] = None
    format: str
    doc_info: Optional[Dict[str, Any]] = None
    processing_status: str
    chapter_count: int
    chapter_hierarchy: Optional[List[ChapterHierarchy]] = None
    images: List[ImageResponse] = []


class ChapterPreview(BaseModel):
    """Model for chapter preview in listings."""
    id: str
    title: str
    order: int
    level: int


class DocumentList(BaseModel):
    """Model for document listings."""
    total: int
    documents: List[DocumentResponse]


class SearchResult(BaseModel):
    """Model for search results."""
    chapter_id: str
    document_id: str
    document_title: str
    chapter_title: str
    chapter_order: int
    chapter_level: int
    snippet: str
    context_html: Optional[str] = None


class ProcessingStatus(BaseModel):
    """Model for document processing status updates."""
    status: str
    progress: float
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str
    details: Optional[str] = None


ChapterHierarchy.update_forward_refs()
