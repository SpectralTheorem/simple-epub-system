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


class Chapter(BaseModel):
    id: str
    document_id: str
    title: str
    content: str
    order: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    images: List[str] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)


class Image(BaseModel):
    """Model for storing image data from documents."""
    id: str
    content: bytes
    media_type: str


class Document(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    format: DocumentFormat
    file_path: Optional[Path] = None
    chapters: List[Chapter] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    images: Dict[str, bytes] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
