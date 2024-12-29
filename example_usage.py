import asyncio
from pathlib import Path
from app.core.pdf_processor import PdfProcessor
from app.core.epub_processor import EpubProcessor
from app.storage.database import DatabaseManager


async def main():
    try:
        # Initialize database
        db = DatabaseManager("sqlite:///books.db")
        
        # Example: Process an EPUB book
        book_path = Path("Dopamine Nation - Anna Lembke.epub")
        if book_path.exists():
            # Use EpubProcessor for EPUB files
            processor = EpubProcessor()
            try:
                document = await processor.process_document(book_path)
                
                # Print document information
                print(f"Title: {document.title}")
                print(f"Author: {document.author}")
                print(f"Status: {document.processing_status}")
                if document.error_message:
                    print(f"Error: {document.error_message}")
                else:
                    print(f"Number of chapters: {len(document.chapters)}")
                    
                    # Print first chapter preview
                    if document.chapters:
                        chapter = document.chapters[0]
                        print(f"\nFirst chapter: {chapter.title}")
                        print(f"Preview: {chapter.content[:200]}...")
            except Exception as e:
                print(f"Error processing document: {str(e)}")
        else:
            print(f"File not found: {book_path}")
    except Exception as e:
        print(f"Application error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
