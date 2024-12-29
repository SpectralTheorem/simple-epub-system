from pathlib import Path
from typing import List, Dict, Any
import asyncio
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import logging

from .base_processor import BaseDocumentProcessor
from ..models.document import Document, Chapter, DocumentFormat, ProcessingStatus, Image
from ..utils.text_utils import clean_text
from ..utils.id_generator import generate_chapter_id

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('epub_processor')

class EpubProcessor(BaseDocumentProcessor):
    """EPUB document processor implementation."""

    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.EPUB]
        self.logger = logging.getLogger('epub_processor')

    async def load_document(self, file_path: Path) -> Document:
        """Load EPUB document and create initial Document object."""
        try:
            self.logger.info(f"Loading EPUB document from {file_path}")
            if not file_path.exists():
                raise FileNotFoundError(f"EPUB file not found: {file_path}")
            
            file_size = file_path.stat().st_size
            self.logger.debug(f"File size: {file_size} bytes")
            if file_size == 0:
                raise ValueError(f"EPUB file is empty: {file_path}")

            self.logger.debug("Attempting to read EPUB file")
            book = epub.read_epub(str(file_path))
            self.logger.debug("Successfully read EPUB file")
            
            # Extract title and author from metadata
            title = file_path.stem
            author = None
            
            if book.get_metadata('DC', 'title'):
                title = book.get_metadata('DC', 'title')[0][0]
                self.logger.debug(f"Found title: {title}")
            if book.get_metadata('DC', 'creator'):
                author = book.get_metadata('DC', 'creator')[0][0]
                self.logger.debug(f"Found author: {author}")
            
            doc_id = file_path.stem
            self.logger.info(f"Created document object with ID: {doc_id}")
            
            return Document(
                id=doc_id,
                title=title,
                author=author,
                format=DocumentFormat.EPUB,
                processing_status=ProcessingStatus.PENDING,
                file_path=file_path
            )
        except Exception as e:
            self.logger.error(f"Failed to load EPUB document: {str(e)}", exc_info=True)
            raise Exception(f"Failed to load EPUB document: {str(e)}")

    async def extract_metadata(self, document: Document) -> Dict[str, Any]:
        """Extract metadata from EPUB."""
        try:
            self.logger.info(f"Extracting metadata from document {document.id}")
            book = epub.read_epub(str(document.file_path))
            
            metadata = {}
            
            # Define metadata fields to extract
            dc_fields = ['title', 'creator', 'description', 'publisher', 'identifier', 'language', 'rights', 'date']
            
            # Extract Dublin Core metadata
            self.logger.debug("Extracting DC metadata")
            for field in dc_fields:
                try:
                    values = book.get_metadata('DC', field)
                    if values:
                        metadata[field] = values[0][0]
                        self.logger.debug(f"Found DC metadata {field}: {values[0][0]}")
                except Exception as e:
                    self.logger.warning(f"Failed to extract DC metadata field {field}: {e}")
            
            return metadata
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}", exc_info=True)
            raise Exception(f"Error extracting metadata: {str(e)}")

    async def segment_chapters(self, document: Document) -> List[Chapter]:
        """Segment EPUB into chapters using document structure."""
        try:
            self.logger.info(f"Segmenting chapters for document {document.id}")
            self.logger.debug(f"Reading EPUB from {document.file_path}")
            book = epub.read_epub(str(document.file_path))
            
            chapters = []
            chapter_id = 1
            
            # Process each item in the book
            items = list(book.get_items())
            self.logger.debug(f"Found {len(items)} items in EPUB")
            
            for item in items:
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    self.logger.debug(f"Processing document item: {item.get_name()}")
                    
                    try:
                        # Parse HTML content
                        content = item.get_content()
                        self.logger.debug(f"Got content for {item.get_name()}, length: {len(content)}")
                        
                        soup = BeautifulSoup(content, 'html.parser')
                        self.logger.debug(f"Parsed HTML for {item.get_name()}")
                        
                        # Extract chapter title
                        title = self._extract_title(soup)
                        if not title:
                            title = f"Chapter {chapter_id}"
                        self.logger.debug(f"Extracted title: {title}")
                        
                        # Clean and extract content
                        text_content = soup.get_text()
                        self.logger.debug(f"Raw text length: {len(text_content)}")
                        content = clean_text(text_content)
                        self.logger.debug(f"Cleaned text length: {len(content)}")
                        
                        # Create chapter object
                        if content.strip():  # Only create chapter if there's content
                            chapter = Chapter(
                                id=generate_chapter_id(document.id, chapter_id),
                                document_id=document.id,
                                title=title,
                                content=content,
                                order=chapter_id,
                                metadata={'source_file': item.get_name()}
                            )
                            chapters.append(chapter)
                            chapter_id += 1
                            self.logger.debug(f"Created chapter: {title}")
                    except Exception as item_error:
                        self.logger.error(f"Error processing item {item.get_name()}: {str(item_error)}", exc_info=True)
                        continue
            
            self.logger.info(f"Segmented {len(chapters)} chapters")
            if not chapters:
                raise ValueError("No valid chapters found in the document")
            return chapters
            
        except Exception as e:
            self.logger.error(f"Error segmenting chapters: {str(e)}", exc_info=True)
            raise Exception(f"Error segmenting chapters: {str(e)}")

    async def extract_images(self, document: Document) -> Dict[str, bytes]:
        """Extract images from EPUB."""
        try:
            self.logger.info(f"Extracting images from document {document.id}")
            book = epub.read_epub(str(document.file_path))
            
            images = {}
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    image_name = item.get_name()
                    image_content = item.get_content()
                    images[image_name] = image_content
                    self.logger.debug(f"Extracted image: {image_name}")
            
            self.logger.info(f"Extracted {len(images)} images")
            return images
            
        except Exception as e:
            self.logger.error(f"Error extracting images: {str(e)}", exc_info=True)
            raise Exception(f"Error extracting images: {str(e)}")

    async def extract_tables(self, document: Document) -> List[Dict[str, Any]]:
        """Extract tables from EPUB HTML content."""
        try:
            self.logger.info(f"Extracting tables from document {document.id}")
            book = epub.read_epub(str(document.file_path))
            tables = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    
                    for table in soup.find_all('table'):
                        table_data = {
                            'source_file': item.get_name(),
                            'headers': [],
                            'rows': []
                        }
                        
                        # Extract headers
                        headers = table.find_all('th')
                        if headers:
                            table_data['headers'] = [header.get_text().strip() for header in headers]
                            self.logger.debug(f"Extracted headers: {table_data['headers']}")
                        
                        # Extract rows
                        for row in table.find_all('tr'):
                            cells = row.find_all(['td', 'th'])
                            if cells:
                                table_data['rows'].append([cell.get_text().strip() for cell in cells])
                                self.logger.debug(f"Extracted row: {table_data['rows'][-1]}")
                        
                        tables.append(table_data)
                        self.logger.debug(f"Extracted table from {item.get_name()}")
            
            self.logger.info(f"Successfully extracted {len(tables)} tables")
            return tables
        except Exception as e:
            self.logger.error(f"Error extracting tables: {str(e)}", exc_info=True)
            return []

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract chapter title from HTML structure."""
        try:
            # Try different heading levels
            for tag in ['h1', 'h2', 'h3']:
                heading = soup.find(tag)
                if heading:
                    title = clean_text(heading.get_text())
                    self.logger.debug(f"Extracted title: {title}")
                    return title
            
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting title: {str(e)}", exc_info=True)
            return ""
