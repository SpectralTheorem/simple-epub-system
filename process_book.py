import asyncio
import argparse
from pathlib import Path
from app.core.pdf_processor import PdfProcessor
from app.core.epub_processor import EpubProcessor
from app.storage.database import DatabaseManager
from app.models.document import DocumentFormat


async def process_book(file_path: str):
    """Process a book file and store its contents in the database."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File {file_path} does not exist")
        return

    # Initialize database
    db = DatabaseManager("sqlite:///books.db")
    
    # Choose processor based on file extension
    if path.suffix.lower() == '.pdf':
        processor = PdfProcessor()
        doc_format = DocumentFormat.PDF
    elif path.suffix.lower() == '.epub':
        processor = EpubProcessor()
        doc_format = DocumentFormat.EPUB
    else:
        print(f"Error: Unsupported file format {path.suffix}")
        return

    try:
        # Process the document
        print(f"Processing {path.name}...")
        document = await processor.process_document(path)
        
        # Store document in database
        doc_id = await db.store_document({
            'id': document.id,
            'title': document.title,
            'author': document.author,
            'format': doc_format.value,
            'doc_metadata': document.metadata,
            'processing_status': document.processing_status.value
        })
        
        # Store chapters
        for chapter in document.chapters:
            await db.store_chapter({
                'id': chapter.id,
                'document_id': doc_id,
                'title': chapter.title,
                'content': chapter.content,
                'order': chapter.order,
                'chapter_metadata': chapter.metadata
            })
        
        print(f"Successfully processed {path.name}")
        print(f"Document ID: {doc_id}")
        print(f"Number of chapters: {len(document.chapters)}")
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        if document:
            await db.update_document_status(document.id, 'failed', str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a book file (PDF or EPUB)")
    parser.add_argument("file_path", help="Path to the book file")
    args = parser.parse_args()
    
    asyncio.run(process_book(args.file_path))
