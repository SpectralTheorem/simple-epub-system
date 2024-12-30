from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from pathlib import Path


class DocumentFormat(str, Enum):
    PDF = "pdf"
    EPUB = "epub"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChapterContent(BaseModel):
    """Model for storing rich chapter content."""
    html: str
    text: str
    footnotes: List[Dict[str, str]] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)


class Chapter(BaseModel):
    """Model for document chapter."""
    id: str
    document_id: str
    title: str
    content: ChapterContent
    order: int
    level: int = 0
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    source_file: Optional[str] = None
    anchor: Optional[str] = None
    chapter_info: Dict[str, Any] = Field(default_factory=dict)  # Renamed from metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChapterHierarchy(BaseModel):
    """Model for chapter hierarchy representation."""
    id: str
    title: str
    level: int
    order: int
    children: List['ChapterHierarchy'] = Field(default_factory=list)


class Image(BaseModel):
    """Model for document image."""
    id: str
    document_id: str
    filename: str  # Source filename in the document
    content: bytes
    media_type: str
    chapters: List[str] = Field(default_factory=list)  # List of chapter IDs where image appears
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    """Model for document."""
    id: str
    title: str
    author: Optional[str] = None
    format: DocumentFormat
    file_path: Optional[Path] = None
    doc_info: Dict[str, Any] = Field(default_factory=dict)
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


# Update forward references for recursive types
ChapterHierarchy.update_forward_refs()
