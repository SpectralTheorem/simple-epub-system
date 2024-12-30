from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import logging

from .base_processor import BaseDocumentProcessor
from .epub_navigation import EpubNavigator, NavPoint
from ..models.document import Document, Chapter, ChapterContent, DocumentFormat, ProcessingStatus
from ..utils.text_utils import clean_text
from ..utils.id_generator import generate_chapter_id


class EpubProcessor(BaseDocumentProcessor):
    """EPUB document processor implementation."""

    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.EPUB]
        self.logger = logging.getLogger('epub_processor')

    async def load_document(self, file_path: Path) -> Document:
        """Load EPUB document and create initial Document object."""
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"EPUB file not found: {file_path}")
            
            file_size = file_path.stat().st_size
            if file_size == 0:
                raise ValueError(f"EPUB file is empty: {file_path}")

            book = epub.read_epub(str(file_path))
            
            # Extract title and author from metadata
            title = file_path.stem
            author = None
            
            if book.get_metadata('DC', 'title'):
                title = book.get_metadata('DC', 'title')[0][0]
            if book.get_metadata('DC', 'creator'):
                author = book.get_metadata('DC', 'creator')[0][0]
            
            return Document(
                id=str(file_path.stem),
                title=title,
                author=author,
                format=DocumentFormat.EPUB,
                processing_status=ProcessingStatus.PENDING,
                file_path=file_path
            )
        except Exception as e:
            raise Exception(f"Failed to load EPUB document: {str(e)}")

    async def extract_metadata(self, document: Document) -> Dict[str, Any]:
        """Extract metadata from EPUB."""
        try:
            book = epub.read_epub(str(document.file_path))
            
            doc_info = {}
            
            # Define metadata fields to extract
            dc_fields = ['title', 'creator', 'description', 'publisher', 'identifier', 'language', 'rights', 'date']
            
            # Extract Dublin Core metadata
            for field in dc_fields:
                values = book.get_metadata('DC', field)
                if values:
                    doc_info[field] = str(values[0][0])
            
            return doc_info
        except Exception as e:
            raise Exception(f"Error extracting metadata: {str(e)}")

    async def segment_chapters(self, document: Document) -> List[Chapter]:
        """Segment EPUB into chapters using document structure and navigation."""
        try:
            # Initialize navigation
            navigator = EpubNavigator(document.file_path)
            ordered_nav_points = navigator.get_ordered_nav_points()
            
            chapters = []
            processed_files = set()
            
            # Process chapters based on navigation
            for nav_point in ordered_nav_points:
                item = navigator.get_item_by_path(nav_point.path)
                if not item:
                    continue
                    
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # If there's a fragment, find the specific section
                if nav_point.fragment:
                    section = soup.find(id=nav_point.fragment)
                    if section:
                        # Create new soup with just this section
                        new_soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
                        new_soup.body.append(section)
                        soup = new_soup
                
                # Clean and extract content
                text_content = clean_text(soup.get_text())
                
                # Create chapter content
                chapter_content = ChapterContent(
                    html=str(soup.body) if soup.body else str(soup),
                    text=text_content,
                    footnotes=self._extract_footnotes(soup),
                    images=self._extract_image_refs(soup),
                    tables=self._extract_tables(soup)
                )
                
                chapter = Chapter(
                    id=generate_chapter_id(document.id, nav_point.order),
                    document_id=document.id,
                    title=nav_point.title,
                    content=chapter_content,
                    order=nav_point.order,
                    level=nav_point.level
                )
                
                chapters.append(chapter)
                processed_files.add(nav_point.path)
            
            # Process any remaining content not in navigation
            for item in navigator.book.get_items():
                if (item.get_type() == ebooklib.ITEM_DOCUMENT and 
                    item.get_name() not in processed_files):
                    content = item.get_content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract title or generate one
                    title = self._extract_title(soup) or f"Section {len(chapters) + 1}"
                    
                    # Clean and extract content
                    text_content = clean_text(soup.get_text())
                    
                    chapter_content = ChapterContent(
                        html=str(soup.body) if soup.body else str(soup),
                        text=text_content,
                        footnotes=self._extract_footnotes(soup),
                        images=self._extract_image_refs(soup),
                        tables=self._extract_tables(soup)
                    )
                    
                    chapter = Chapter(
                        id=generate_chapter_id(document.id, len(chapters) + 1),
                        document_id=document.id,
                        title=title,
                        content=chapter_content,
                        order=len(chapters) + 1,
                        level=0
                    )
                    
                    chapters.append(chapter)
            
            # Set up parent/child relationships
            chapter_dict = {ch.id: ch for ch in chapters}
            for i, chapter in enumerate(chapters):
                if i > 0:
                    prev_chapter = chapters[i - 1]
                    if chapter.level > prev_chapter.level:
                        chapter.parent_id = prev_chapter.id
                        chapter_dict[prev_chapter.id].children.append(chapter.id)
            
            if not chapters:
                raise ValueError("No valid chapters found in the document")
                
            return chapters
            
        except Exception as e:
            raise Exception(f"Error segmenting chapters: {str(e)}")

    def _extract_footnotes(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract footnotes from HTML content."""
        footnotes = []
        for note in soup.find_all(['aside', 'div', 'section'], 
                                class_=['footnote', 'endnote', 'note']):
            note_id = note.get('id', '')
            note_text = clean_text(note.get_text())
            if note_text:
                footnotes.append({
                    'id': note_id,
                    'text': note_text
                })
        return footnotes

    def _extract_image_refs(self, soup: BeautifulSoup) -> List[str]:
        """Extract image references from HTML content."""
        return [img.get('src', '') for img in soup.find_all('img') if img.get('src')]

    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables from HTML content."""
        tables = []
        for table in soup.find_all('table'):
            table_data = []
            headers = []
            
            # Extract headers
            for th in table.find_all('th'):
                headers.append(clean_text(th.get_text()))
            
            # Extract rows
            for tr in table.find_all('tr'):
                row = []
                for td in tr.find_all('td'):
                    row.append(clean_text(td.get_text()))
                if row:  # Only add non-empty rows
                    table_data.append(row)
            
            if headers or table_data:
                tables.append({
                    'headers': headers,
                    'data': table_data
                })
                
        return tables

    async def extract_images(self, document: Document) -> Dict[str, bytes]:
        """Extract images from EPUB."""
        try:
            book = epub.read_epub(str(document.file_path))
            
            images = {}
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    image_name = item.get_name()
                    image_content = item.get_content()
                    images[image_name] = image_content
            
            return images
            
        except Exception as e:
            raise Exception(f"Error extracting images: {str(e)}")

    async def extract_tables(self, document: Document) -> List[Dict[str, Any]]:
        """Extract tables from EPUB HTML content."""
        try:
            book = epub.read_epub(str(document.file_path))
            tables = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    tables.extend(self._extract_tables(soup))
            
            return tables
        except Exception as e:
            raise Exception(f"Error extracting tables: {str(e)}")

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract chapter title from HTML structure."""
        try:
            # Try different heading levels
            for tag in ['h1', 'h2', 'h3']:
                heading = soup.find(tag)
                if heading:
                    return clean_text(heading.get_text())
            return ""
        except Exception as e:
            return ""
