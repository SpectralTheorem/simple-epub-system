import asyncio
from pathlib import Path
from typing import List, Dict, Any
import re

from pypdf import PdfReader
import nltk
from nltk.tokenize import sent_tokenize

from .base_processor import BaseDocumentProcessor
from ..models.document import Document, Chapter, ChapterContent, DocumentFormat, ProcessingStatus
from ..utils.text_utils import clean_text, extract_chapter_title


class PdfProcessor(BaseDocumentProcessor):
    """PDF document processor implementation."""

    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.PDF]
        # Download required NLTK data
        nltk.download('punkt', quiet=True)

    async def load_document(self, file_path: Path) -> Document:
        """Load PDF document and create initial Document object."""
        reader = PdfReader(file_path)
        
        # Extract basic metadata
        info = reader.metadata
        
        return Document(
            id=str(file_path.stem),
            title=info.get('/Title', file_path.stem),
            author=info.get('/Author'),
            format=DocumentFormat.PDF,
            doc_info={'page_count': len(reader.pages)},
            processing_status=ProcessingStatus.PENDING,
            file_path=file_path
        )

    async def extract_metadata(self, document: Document) -> Dict[str, Any]:
        """Extract detailed metadata from PDF."""
        reader = PdfReader(document.file_path)
        metadata = reader.metadata
        
        return {
            'title': metadata.get('/Title', document.title),
            'author': metadata.get('/Author'),
            'subject': metadata.get('/Subject'),
            'keywords': metadata.get('/Keywords'),
            'creator': metadata.get('/Creator'),
            'producer': metadata.get('/Producer'),
            'creation_date': metadata.get('/CreationDate'),
            'modification_date': metadata.get('/ModDate'),
            'page_count': len(reader.pages)
        }

    async def segment_chapters(self, document: Document) -> List[Chapter]:
        """Segment PDF into chapters using heuristic approach."""
        reader = PdfReader(document.file_path)
        chapters = []
        current_chapter = []
        chapter_number = 1

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            
            # Look for chapter indicators
            if self._is_chapter_start(text) and current_chapter:
                # Save previous chapter
                chapter_title = extract_chapter_title(current_chapter[0])
                chapter_content = ChapterContent(
                    html="",  # PDF doesn't have HTML
                    text="\n".join(current_chapter),
                    footnotes=[],  # PDF footnote extraction not implemented
                    images=[],  # Image references handled separately
                    tables=[]  # Table extraction handled separately
                )
                
                chapters.append(
                    Chapter(
                        id=f"{document.id}_ch_{chapter_number}",
                        document_id=document.id,
                        title=chapter_title,
                        content=chapter_content,
                        order=chapter_number,
                        level=0  # PDF doesn't have hierarchy information
                    )
                )
                chapter_number += 1
                current_chapter = []
            
            current_chapter.append(clean_text(text))

        # Add the last chapter
        if current_chapter:
            chapter_title = extract_chapter_title(current_chapter[0])
            chapter_content = ChapterContent(
                html="",
                text="\n".join(current_chapter),
                footnotes=[],
                images=[],
                tables=[]
            )
            
            chapters.append(
                Chapter(
                    id=f"{document.id}_ch_{chapter_number}",
                    document_id=document.id,
                    title=chapter_title,
                    content=chapter_content,
                    order=chapter_number,
                    level=0
                )
            )

        return chapters

    async def extract_images(self, document: Document) -> Dict[str, bytes]:
        """Extract images from PDF pages."""
        reader = PdfReader(document.file_path)
        images = {}
        
        for page_num, page in enumerate(reader.pages):
            if '/Resources' in page and '/XObject' in page['/Resources']:
                xObject = page['/Resources']['/XObject'].get_object()

                for obj in xObject:
                    if xObject[obj]['/Subtype'] == '/Image':
                        image = xObject[obj]
                        image_key = f"{document.id}_image_{page_num}_{obj}"
                        # Extract image based on format
                        try:
                            if image['/Filter'] == '/DCTDecode':
                                # JPEG image
                                images[image_key] = image._data
                            elif image['/Filter'] == '/FlateDecode':
                                # PNG image
                                images[image_key] = image._data
                            elif image['/Filter'] == '/JPXDecode':
                                # JPEG2000 image
                                images[image_key] = image._data
                        except Exception:
                            continue
        
        return images

    async def extract_tables(self, document: Document) -> List[Dict[str, Any]]:
        """Extract tables from PDF (placeholder - requires specialized library)."""
        # This is a placeholder. Real implementation would use a library like
        # camelot-py or tabula-py for table extraction
        return []

    def _is_chapter_start(self, text: str) -> bool:
        """Detect if text represents the start of a new chapter."""
        # Simple heuristic - look for common chapter indicators
        chapter_patterns = [
            r'^Chapter\s+\d+',
            r'^\d+\.\s+',
            r'^CHAPTER\s+\d+',
        ]
        
        return any(re.match(pattern, text.strip()) for pattern in chapter_patterns)
