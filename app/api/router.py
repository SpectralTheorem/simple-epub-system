from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import asyncio
from pathlib import Path
import tempfile
import os
import shutil
import logging
import base64

from ..core.epub_processor import EpubProcessor
from ..core.pdf_processor import PdfProcessor
from ..storage.database import DatabaseManager
from ..utils.id_generator import generate_document_id, generate_chapter_id, generate_image_id
from ..models.document import (
    Document, DocumentFormat, ProcessingStatus, Chapter,
    ChapterHierarchy, ChapterContent
)
from .models import (
    DocumentResponse, ChapterResponse, ChapterPreview,
    DocumentList, SearchResult, ProcessingStatus as APIProcessingStatus, ErrorResponse
)

router = APIRouter()
# Initialize database manager with aiosqlite URL
db = DatabaseManager("sqlite+aiosqlite:///books.db")

# Track background processing tasks
processing_tasks = {}

# Create a directory for temporary files
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

async def process_document_background(file_path: str, doc_id: str):
    """Background task for processing documents."""
    try:
        logging.info(f"Starting processing of document {doc_id}")
        # Choose processor based on file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.epub':
            processor = EpubProcessor()
            doc_format = DocumentFormat.EPUB
        elif file_ext == '.pdf':
            processor = PdfProcessor()
            doc_format = DocumentFormat.PDF
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        try:
            # Load document
            document = await processor.load_document(Path(file_path))
            document.id = doc_id
            
            # Extract metadata
            doc_info = await processor.extract_metadata(document)
            document.doc_info = doc_info
            
            # Process chapters
            chapters = await processor.segment_chapters(document)
            
            # Extract images
            images = await processor.extract_images(document)
            
            # Store images
            for img_id, img_data in images.items():
                try:
                    await db.store_image({
                        'id': generate_image_id(img_id),
                        'document_id': document.id,
                        'content': img_data,
                        'media_type': 'image/jpeg'  # TODO: Detect proper media type
                    })
                except Exception as img_error:
                    logging.error(f"Error storing image {img_id}: {str(img_error)}")
                    # Continue processing other images
            
            # Update document with processed data
            await db.store_document({
                'id': document.id,
                'title': document.title,
                'author': document.author,
                'format': document.format.value,
                'doc_info': document.doc_info,
                'processing_status': ProcessingStatus.COMPLETED.value
            })
            
            # Store chapters
            for chapter in chapters:
                try:
                    # Convert Chapter object to dict
                    chapter_dict = {
                        'id': chapter.id,
                        'document_id': chapter.document_id,
                        'title': chapter.title,
                        'content': {
                            'html': chapter.content.html,
                            'text': chapter.content.text,
                            'footnotes': chapter.content.footnotes,
                            'images': chapter.content.images,
                            'tables': chapter.content.tables
                        },
                        'order': chapter.order,
                        'level': chapter.level,
                        'parent_id': chapter.parent_id if hasattr(chapter, 'parent_id') else None
                    }
                    await db.store_chapter(chapter_dict)
                except Exception as ch_error:
                    logging.error(f"Error storing chapter {chapter.id}: {str(ch_error)}")
                    # Continue processing other chapters
            
            processing_tasks[doc_id] = {
                'status': 'completed',
                'progress': 1.0
            }
            
            logging.info(f"Completed processing document {doc_id}")
            
        except Exception as proc_error:
            error_msg = f"Error during document processing: {str(proc_error)}"
            logging.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from proc_error
            
    except Exception as e:
        error_msg = f"Error processing document {doc_id}: {str(e)}"
        logging.error(error_msg, exc_info=True)
        processing_tasks[doc_id] = {
            'status': 'failed',
            'progress': 0,
            'error': error_msg
        }
        try:
            await db.store_document({
                'id': doc_id,
                'processing_status': ProcessingStatus.FAILED.value,
                'doc_info': {'error': error_msg}
            })
        except Exception as db_error:
            logging.error(f"Error updating document status: {str(db_error)}")
    finally:
        # Clean up temp file
        try:
            os.remove(file_path)
            logging.info(f"Cleaned up temp file {file_path}")
        except Exception as cleanup_error:
            logging.error(f"Error cleaning up temp file: {cleanup_error}")


def _build_chapter_hierarchy(chapters: List[Any]) -> List[ChapterHierarchy]:
    """Build chapter hierarchy from flat chapter list."""
    # Convert SQLAlchemy models to dicts for easier processing
    chapter_dicts = [
        {
            'id': ch.id,
            'title': ch.title,
            'level': ch.level,
            'order': ch.order,
            'parent_id': ch.parent_id
        }
        for ch in chapters
    ]
    
    # Create a map of all chapters
    chapter_map = {ch['id']: ch for ch in chapter_dicts}
    
    # Initialize children lists
    for ch in chapter_dicts:
        ch['children'] = []
    
    # Build hierarchy
    roots = []
    for ch in chapter_dicts:
        if not ch['parent_id']:
            roots.append(ch)
        else:
            parent = chapter_map.get(ch['parent_id'])
            if parent:
                parent['children'].append(ch)
    
    # Sort by order
    roots.sort(key=lambda x: x['order'])
    for ch in chapter_dicts:
        ch['children'].sort(key=lambda x: x['order'])
    
    # Convert to ChapterHierarchy models
    def convert_to_hierarchy(chapter_dict: Dict[str, Any]) -> ChapterHierarchy:
        return ChapterHierarchy(
            id=chapter_dict['id'],
            title=chapter_dict['title'],
            level=chapter_dict['level'],
            order=chapter_dict['order'],
            children=[convert_to_hierarchy(child) for child in chapter_dict['children']]
        )
    
    return [convert_to_hierarchy(root) for root in roots]


@router.post("/documents/upload", response_model=APIProcessingStatus)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload and process a new document."""
    try:
        logging.info(f"Starting upload for file: {file.filename}")
        
        # Generate document ID and create temp file path
        doc_id = generate_document_id(Path(file.filename).stem)
        temp_file_path = TEMP_DIR / f"{doc_id}{Path(file.filename).suffix}"
        
        # Determine document format
        file_ext = Path(file.filename).suffix.lower()
        if file_ext == '.epub':
            doc_format = DocumentFormat.EPUB
        elif file_ext == '.pdf':
            doc_format = DocumentFormat.PDF
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_ext}. Only .epub and .pdf files are supported."
            )
        
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Initialize processing status
        processing_tasks[doc_id] = {
            'status': 'processing',
            'progress': 0
        }
        
        # Store initial document record
        await db.store_document({
            'id': doc_id,
            'title': Path(file.filename).stem,
            'processing_status': ProcessingStatus.PROCESSING.value,
            'format': doc_format.value,
            'doc_info': {}
        })
        
        # Start background processing
        background_tasks.add_task(
            process_document_background,
            str(temp_file_path),
            doc_id
        )
        
        return APIProcessingStatus(
            status="processing",
            progress=0,
            message=f"Processing started for document {doc_id}"
        )
    except Exception as e:
        logging.error(f"Error during upload: {str(e)}", exc_info=True)
        # Clean up on error
        if 'temp_file_path' in locals():
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents/{doc_id}/status", response_model=APIProcessingStatus)
async def get_processing_status(doc_id: str):
    """Get document processing status."""
    task_status = processing_tasks.get(doc_id)
    if not task_status:
        document = await db.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return APIProcessingStatus(
            status=document['processing_status'],
            progress=1.0 if document['processing_status'] == ProcessingStatus.COMPLETED.value else 0
        )
    return APIProcessingStatus(**task_status)


@router.get("/documents", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List all processed documents with pagination."""
    # Get documents
    docs = await db.get_documents(skip=skip, limit=limit)
    total = await db.get_document_count()
    
    # Convert to response format
    doc_responses = []
    for doc in docs:
        # Get chapter count
        chapter_count = await db.get_chapter_count(doc['id'])
        
        # Create response object
        doc_response = DocumentResponse(
            **doc,
            chapter_count=chapter_count,
            chapter_hierarchy=[]  # Empty hierarchy for list view
        )
        doc_responses.append(doc_response)
    
    return DocumentList(
        total=total,
        documents=doc_responses
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get document details with chapter hierarchy."""
    document = await db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get all chapters to build hierarchy
    chapters = await db.get_all_chapters(doc_id)
    
    return DocumentResponse(
        **document,
        chapter_count=len(chapters),
        chapter_hierarchy=_build_chapter_hierarchy(chapters)
    )


@router.get("/documents/{doc_id}/chapters", response_model=List[ChapterPreview])
async def list_chapters(
    doc_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List chapters for a document with pagination."""
    document = await db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    chapters = await db.get_chapters(doc_id, skip, limit)
    return [
        ChapterPreview(
            id=ch['id'],
            title=ch['title'],
            order=ch['order'],
            level=ch['level']
        )
        for ch in chapters
    ]


@router.get("/documents/{doc_id}/chapters/hierarchy", response_model=List[ChapterHierarchy])
async def get_chapter_hierarchy(doc_id: str):
    """Get the full chapter hierarchy for a document."""
    document = await db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    chapters = await db.get_all_chapters(doc_id)
    return _build_chapter_hierarchy(chapters)


@router.get("/documents/{doc_id}/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(doc_id: str, chapter_id: str):
    """Get chapter details."""
    chapter = await db.get_chapter(doc_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return ChapterResponse(**chapter)


@router.get("/search", response_model=List[SearchResult])
async def search_content(
    query: str = Query(..., min_length=1),
    doc_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Search through document content with context."""
    results = []
    
    # Get documents to search
    if doc_id:
        document = await db.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        documents = [document]
    else:
        documents = await db.get_documents(0, 1000)  # Reasonable limit for search
    
    # Search through each document's chapters
    for document in documents:
        chapters = await db.get_all_chapters(document['id'])
        for chapter in chapters:
            if query.lower() in chapter['content']['text'].lower():
                # Create snippet with context
                text = chapter['content']['text']
                idx = text.lower().find(query.lower())
                start = max(0, idx - 50)
                end = min(len(text), idx + len(query) + 50)
                snippet = f"...{text[start:end]}..."
                
                results.append(SearchResult(
                    chapter_id=chapter['id'],
                    document_id=document['id'],
                    document_title=document['title'],
                    chapter_title=chapter['title'],
                    chapter_order=chapter['order'],
                    chapter_level=chapter['level'],
                    snippet=snippet,
                    context_html=chapter['content']['html']
                ))
    
    # Apply pagination
    return results[skip:skip + limit]


@router.delete("/database/clear", response_model=Dict[str, Any])
async def clear_database():
    """Clear all entries from the database."""
    result = await db.clear_database()
    processing_tasks.clear()
    return {"status": "Database cleared", "deleted": result}
