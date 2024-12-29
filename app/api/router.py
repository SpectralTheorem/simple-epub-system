from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict
import asyncio
from pathlib import Path
import tempfile
import os
import shutil
import logging

from ..core.epub_processor import EpubProcessor
from ..core.pdf_processor import PdfProcessor
from ..storage.database import DatabaseManager
from ..utils.id_generator import generate_document_id, generate_chapter_id
from ..models.document import Document, DocumentFormat, ProcessingStatus, Chapter
from .models import (
    DocumentResponse, ChapterResponse, ChapterPreview,
    DocumentList, SearchResult, ProcessingStatus as APIProcessingStatus, ErrorResponse
)

router = APIRouter()
db = DatabaseManager("sqlite:///books.db")

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

        logging.info(f"Using {doc_format} processor for document {doc_id}")
        
        # Process document using the actual file path
        file_path = Path(file_path)
        try:
            logging.info(f"Loading document from {file_path}")
            document = await processor.load_document(file_path)
            document.id = doc_id  # Ensure we use the generated doc_id
            
            logging.info(f"Extracting metadata for document {doc_id}")
            metadata = await processor.extract_metadata(document)
            document.metadata = metadata
            processing_tasks[doc_id]['progress'] = 30
            logging.info(f"Metadata extracted: {metadata}")
            
            logging.info(f"Segmenting chapters for document {doc_id}")
            chapters = await processor.segment_chapters(document)
            document.chapters = chapters
            processing_tasks[doc_id]['progress'] = 60
            logging.info(f"Found {len(chapters)} chapters")
            
            logging.info(f"Extracting images for document {doc_id}")
            document.images = await processor.extract_images(document)
            processing_tasks[doc_id]['progress'] = 80
            
            logging.info(f"Extracting tables for document {doc_id}")
            document.tables = await processor.extract_tables(document)
            processing_tasks[doc_id]['progress'] = 90
            
            # Update document status
            document.processing_status = ProcessingStatus.COMPLETED
            processing_tasks[doc_id] = {
                'status': 'completed',
                'progress': 100
            }
            
            logging.info(f"Storing processed document {doc_id}")
            await db.store_document(document.dict(exclude={'file_path', 'chapters', 'images', 'tables'}))
            
            # Store chapters
            logging.info(f"Storing {len(chapters)} chapters for document {doc_id}")
            for chapter in chapters:
                chapter_dict = chapter.dict()
                chapter_dict['document_id'] = doc_id
                await db.store_chapter(chapter_dict)
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            logging.error(f"Error processing document {doc_id}: {error_msg}", exc_info=True)
            document = Document(
                id=doc_id,
                title=Path(file_path).stem,
                processing_status=ProcessingStatus.FAILED,
                error_message=error_msg,
                format=doc_format
            )
            processing_tasks[doc_id] = {
                'status': 'failed',
                'progress': 0,
                'error': error_msg
            }
            await db.store_document(document.dict())
            raise
            
    except Exception as e:
        error_msg = f"Background task error: {str(e)}"
        logging.error(f"Error in background task for document {doc_id}: {error_msg}", exc_info=True)
        processing_tasks[doc_id] = {
            'status': 'failed',
            'progress': 0,
            'error': error_msg
        }
        await db.store_document({
            'id': doc_id,
            'title': Path(file_path).stem,
            'processing_status': ProcessingStatus.FAILED.value,
            'error_message': error_msg,
            'format': doc_format.value if 'doc_format' in locals() else DocumentFormat.EPUB.value
        })
    finally:
        # Clean up temporary file
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
                logging.info(f"Cleaned up temporary file {file_path}")
        except Exception as e:
            logging.error(f"Error cleaning up temporary file: {e}")

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
        logging.info(f"Generated doc_id: {doc_id}, temp path: {temp_file_path}")
        
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
        logging.info(f"Saving uploaded file to {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            logging.info(f"File saved successfully, size: {len(content)} bytes")
        
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
            'format': doc_format.value
        })
        
        # Start background processing
        logging.info(f"Starting background processing for document {doc_id}")
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
                logging.info(f"Cleaned up temp file {temp_file_path}")
            except Exception as cleanup_error:
                logging.error(f"Error cleaning up temp file: {cleanup_error}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/documents/{doc_id}/status", response_model=APIProcessingStatus)
async def get_processing_status(doc_id: str):
    """Get document processing status."""
    if doc_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Document not found")
    
    task = processing_tasks[doc_id]
    return APIProcessingStatus(
        status=task['status'],
        progress=task['progress'],
        message=task.get('error')
    )

@router.get("/documents", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List all processed documents with pagination."""
    try:
        documents = await db.get_documents(skip, limit)
        total = await db.get_document_count()
        
        # Convert raw dictionaries to Pydantic models
        document_responses = [
            DocumentResponse(
                id=doc['id'],
                title=doc['title'],
                author=doc['author'],
                format=doc['format'],
                doc_metadata=doc.get('doc_metadata'),
                processing_status=doc['processing_status'],
                error_message=doc.get('error_message'),
                created_at=doc['created_at'],
                updated_at=doc['updated_at'],
                chapter_count=doc['chapter_count']
            )
            for doc in documents
        ]
        
        return DocumentList(total=total, documents=document_responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get document details."""
    try:
        document = await db.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/chapters", response_model=List[ChapterPreview])
async def list_chapters(
    doc_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List chapters for a document with pagination."""
    try:
        chapters = await db.get_document_chapters(doc_id)
        previews = []
        for chapter in chapters[skip:skip + limit]:
            content = chapter['content']
            previews.append(ChapterPreview(
                id=chapter['id'],
                title=chapter['title'],
                order=chapter['order'],
                preview=content[:200] + "..." if len(content) > 200 else content,
                content_length=len(content)
            ))
        return previews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/all-chapters", response_model=List[ChapterResponse])
async def get_all_chapters(doc_id: str):
    """Get all chapters for a document without pagination."""
    try:
        chapters = await db.get_document_chapters(doc_id)
        if not chapters:
            raise HTTPException(status_code=404, detail="No chapters found for this document")
        return chapters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(doc_id: str, chapter_id: str):
    """Get chapter details."""
    try:
        chapter = await db.get_chapter(chapter_id)
        if not chapter or chapter['document_id'] != doc_id:
            raise HTTPException(status_code=404, detail="Chapter not found")
        return chapter
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=List[SearchResult])
async def search_content(
    query: str = Query(..., min_length=1),
    doc_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Search through document content."""
    try:
        results = await db.search_content(query, doc_id, skip, limit)
        return [
            SearchResult(
                chapter_id=r['chapter_id'],
                document_id=r['document_id'],
                document_title=r['document_title'],
                chapter_title=r['chapter_title'],
                chapter_order=r['chapter_order'],
                snippet=r['snippet']
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/database/clear", response_model=Dict[str, int])
async def clear_database():
    """Clear all entries from the database."""
    try:
        result = await db.clear_database()
        # Also clear processing tasks
        processing_tasks.clear()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
