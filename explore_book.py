import asyncio
from pathlib import Path
from typing import Optional
from app.core.epub_processor import EpubProcessor
from app.storage.database import DatabaseManager
from app.models.document import ProcessingStatus


async def display_chapter_info(db: DatabaseManager, doc_id: str, chapter_number: Optional[int] = None):
    """Display information about specific chapters or all chapters."""
    chapters = await db.get_document_chapters(doc_id)
    
    if chapter_number is not None:
        if 0 <= chapter_number < len(chapters):
            chapter = chapters[chapter_number]
            print(f"\nChapter {chapter_number + 1}: {chapter['title']}")
            print("-" * 50)
            print(f"Content preview: {chapter['content'][:200]}...")
            print(f"Content length: {len(chapter['content'])} characters")
            print(f"Metadata: {chapter['chapter_metadata']}")
        else:
            print(f"Chapter {chapter_number + 1} not found")
    else:
        print("\nAll Chapters:")
        print("-" * 50)
        for idx, chapter in enumerate(chapters):
            print(f"{idx + 1}. {chapter['title']} ({len(chapter['content'])} chars)")


async def explore_book(file_path: str):
    """Process and explore a book file."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File {file_path} does not exist")
        return

    # Initialize database and processor
    db = DatabaseManager("sqlite:///books.db")
    processor = EpubProcessor()
    
    try:
        # Process the document
        print(f"Processing {path.name}...")
        document = await processor.process_document(path)
        
        # Display basic information
        print("\nBook Information:")
        print("-" * 50)
        print(f"Title: {document.title}")
        print(f"Author: {document.author}")
        print(f"Processing Status: {document.processing_status}")
        print(f"Number of Chapters: {len(document.chapters)}")
        
        if document.metadata:
            print("\nMetadata:")
            print("-" * 50)
            for key, value in document.metadata.items():
                print(f"{key}: {value}")
        
        # Store in database
        doc_id = await db.store_document({
            'id': document.id,
            'title': document.title,
            'author': document.author,
            'format': document.format.value,
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
        
        # Interactive exploration
        while True:
            print("\nExplore Options:")
            print("1. List all chapters")
            print("2. View specific chapter")
            print("3. Search in chapters")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ")
            
            if choice == "1":
                await display_chapter_info(db, doc_id)
            
            elif choice == "2":
                chapter_num = input("Enter chapter number: ")
                try:
                    await display_chapter_info(db, doc_id, int(chapter_num) - 1)
                except ValueError:
                    print("Please enter a valid chapter number")
            
            elif choice == "3":
                search_term = input("Enter search term: ")
                chapters = await db.get_document_chapters(doc_id)
                print(f"\nSearching for '{search_term}':")
                print("-" * 50)
                for chapter in chapters:
                    if search_term.lower() in chapter['content'].lower():
                        print(f"Found in Chapter {chapter['order']}: {chapter['title']}")
            
            elif choice == "4":
                break
            
            else:
                print("Invalid choice. Please try again.")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python explore_book.py <path_to_book>")
        sys.exit(1)
    
    asyncio.run(explore_book(sys.argv[1]))
