from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio
from pathlib import Path

from ..models.document import Document, Chapter, ProcessingStatus, DocumentFormat


class BaseDocumentProcessor(ABC):
    """Abstract base class for document processors."""

    def __init__(self):
        self.supported_formats = []

    @abstractmethod
    async def load_document(self, file_path: Path) -> Document:
        """Load document from file path and create initial Document object."""
        pass

    @abstractmethod
    async def extract_metadata(self, document: Document) -> Dict[str, Any]:
        """Extract metadata from the document."""
        pass

    @abstractmethod
    async def segment_chapters(self, document: Document) -> List[Chapter]:
        """Segment document into chapters."""
        pass

    @abstractmethod
    async def extract_images(self, document: Document) -> Dict[str, bytes]:
        """Extract images from the document."""
        pass

    @abstractmethod
    async def extract_tables(self, document: Document) -> List[Dict[str, Any]]:
        """Extract tables from the document."""
        pass

    async def process_document(self, file_path: Path) -> Document:
        """Process a document file and return a Document object."""
        try:
            # Load initial document
            document = await self.load_document(file_path)
            document.processing_status = ProcessingStatus.PROCESSING

            # Process document components concurrently
            metadata_task = asyncio.create_task(self.extract_metadata(document))
            chapters_task = asyncio.create_task(self.segment_chapters(document))
            images_task = asyncio.create_task(self.extract_images(document))
            tables_task = asyncio.create_task(self.extract_tables(document))

            # Wait for all tasks to complete
            try:
                metadata = await metadata_task
                if not isinstance(metadata, dict):
                    raise ValueError("Metadata must be a dictionary")
                document.doc_info = metadata
                document.chapters = await chapters_task
                document.images = await images_task
                document.tables = await tables_task
            except Exception as task_error:
                document.processing_status = ProcessingStatus.FAILED
                raise Exception(f"Processing failed during task execution: {str(task_error)}")

            document.processing_status = ProcessingStatus.COMPLETED
            return document

        except Exception as e:
            if 'document' in locals():
                document.processing_status = ProcessingStatus.FAILED
            raise Exception(f"Failed to process document: {str(e)}")

    def _assign_content_to_chapters(
        self,
        chapters: List[Chapter],
        images: Dict[str, bytes],
        tables: List[Dict[str, Any]]
    ) -> None:
        """Assign extracted images and tables to their respective chapters."""
        # Implementation depends on specific document format
        pass
