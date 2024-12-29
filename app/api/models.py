from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ChapterResponse(BaseModel):
    id: str
    title: str
    content: str
    order: int
    chapter_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class DocumentResponse(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    format: str
    doc_metadata: Optional[Dict[str, Any]] = None
    processing_status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    chapter_count: int

class ChapterPreview(BaseModel):
    id: str
    title: str
    order: int
    preview: str
    content_length: int

class DocumentList(BaseModel):
    total: int
    documents: List[DocumentResponse]

class SearchResult(BaseModel):
    chapter_id: str
    document_id: str
    document_title: str
    chapter_title: str
    chapter_order: int
    snippet: str
    
class ProcessingStatus(BaseModel):
    status: str
    progress: float
    message: Optional[str] = None
    
class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
