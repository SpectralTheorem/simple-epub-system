from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Enum, ForeignKey, text, select, Index, LargeBinary, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

from ..models.document import DocumentFormat, ProcessingStatus

Base = declarative_base()


class DocumentModel(Base):
    """SQLAlchemy model for documents.
    
    As per DESIGN.md, this model stores document metadata and a dictionary of images.
    Images are stored directly in the document model rather than in a separate table.
    """
    __tablename__ = 'documents'

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String)
    format = Column(Enum(DocumentFormat), nullable=False)
    doc_info = Column(JSON)  # Stores document metadata as specified in DESIGN.md
    processing_status = Column(Enum(ProcessingStatus), nullable=False)
    images = relationship("ImageModel", back_populates="document", cascade="all, delete-orphan")
    
    chapters = relationship("ChapterModel", back_populates="document", cascade="all, delete-orphan")


chapter_images = Table(
    'chapter_images',
    Base.metadata,
    Column('chapter_id', String, ForeignKey('chapters.id', ondelete='CASCADE')),
    Column('image_id', String, ForeignKey('images.id', ondelete='CASCADE')),
    Index('idx_chapter_images', 'chapter_id', 'image_id')
)


class ImageModel(Base):
    """SQLAlchemy model for images.
    
    As per DESIGN.md, this model stores binary image data and metadata.
    """
    __tablename__ = 'images'

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    content = Column(LargeBinary, nullable=False)
    media_type = Column(String, nullable=False)

    document = relationship("DocumentModel", back_populates="images")
    chapters = relationship("ChapterModel", secondary=chapter_images, back_populates="images")


class ChapterModel(Base):
    """SQLAlchemy model for chapters.
    
    As per DESIGN.md, chapter content is stored as a nested JSON structure:
    {
        "html": str,          # Original HTML content
        "text": str,          # Plain text content
        "footnotes": List,    # Extracted footnotes
        "images": List,       # Image references
        "tables": List        # Table data
    }
    """
    __tablename__ = 'chapters'

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    title = Column(String, nullable=False)
    content = Column(JSON, nullable=False)  # Stores the entire content structure as JSON
    order = Column(Integer, nullable=False)
    level = Column(Integer, nullable=False, default=0)
    parent_id = Column(String, ForeignKey('chapters.id'), nullable=True)

    document = relationship("DocumentModel", back_populates="chapters")
    parent = relationship("ChapterModel", remote_side=[id], backref="children")
    images = relationship("ImageModel", secondary=chapter_images, back_populates="chapters")

    __table_args__ = (
        Index('idx_document_order', document_id, order),
        Index('idx_parent_id', parent_id),
    )


class DatabaseManager:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///books.db"):
        """Initialize the database manager.
        
        Args:
            database_url: Database URL. For SQLite, must use format 'sqlite+aiosqlite:///path/to/db'
        """
        if database_url.startswith('sqlite:///'):
            database_url = database_url.replace('sqlite:', 'sqlite+aiosqlite:')
            
        self.engine = create_async_engine(database_url, echo=True)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize the database, creating tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def store_document(self, document: Dict[str, Any]) -> str:
        """Store or update a document."""
        async with self.async_session() as session:
            async with session.begin():
                # Check if document exists
                existing_doc = await session.get(DocumentModel, document['id'])
                
                # Convert enum values to proper format
                if 'format' in document and isinstance(document['format'], str):
                    document['format'] = DocumentFormat(document['format'])
                if 'processing_status' in document and isinstance(document['processing_status'], str):
                    document['processing_status'] = ProcessingStatus(document['processing_status'])
                
                # Remove any fields that don't exist in DocumentModel
                doc_data = {k: v for k, v in document.items() 
                          if hasattr(DocumentModel, k)}
                
                if existing_doc:
                    # Update existing document
                    for key, value in doc_data.items():
                        if hasattr(existing_doc, key):
                            setattr(existing_doc, key, value)
                else:
                    # Create new document
                    existing_doc = DocumentModel(**doc_data)
                    session.add(existing_doc)
                await session.commit()
                return existing_doc.id

    async def store_chapter(self, chapter: Dict[str, Any]) -> str:
        """Store or update a chapter."""
        async with self.async_session() as session:
            async with session.begin():
                # Check if chapter exists
                existing_chapter = await session.get(ChapterModel, chapter['id'])
                
                # Prepare chapter data according to DESIGN.md spec
                chapter_data = {
                    'id': chapter['id'],
                    'document_id': chapter['document_id'],
                    'title': chapter['title'],
                    'content': chapter['content'],
                    'order': chapter['order'],
                    'level': chapter['level'],
                    'parent_id': chapter.get('parent_id')
                }
                
                if existing_chapter:
                    # Update existing chapter
                    for key, value in chapter_data.items():
                        setattr(existing_chapter, key, value)
                else:
                    # Create new chapter
                    existing_chapter = ChapterModel(**chapter_data)
                    session.add(existing_chapter)
                
                await session.commit()
                return existing_chapter.id

    async def store_image(self, image: Dict[str, Any]) -> str:
        """Store or update an image."""
        async with self.async_session() as session:
            async with session.begin():
                # Check if image exists
                existing_image = await session.get(ImageModel, image['id'])
                
                if existing_image:
                    # Update existing image
                    for key, value in image.items():
                        if hasattr(existing_image, key):
                            setattr(existing_image, key, value)
                else:
                    # Create new image
                    existing_image = ImageModel(**image)
                    session.add(existing_image)
                
                await session.commit()
                return existing_image.id

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        async with self.async_session() as session:
            async with session.begin():
                stmt = (
                    select(DocumentModel)
                    .options(selectinload(DocumentModel.images))
                    .where(DocumentModel.id == document_id)
                )
                result = await session.execute(stmt)
                doc = result.scalar_one_or_none()
                if doc:
                    return {
                        'id': doc.id,
                        'title': doc.title,
                        'author': doc.author,
                        'format': doc.format.value,
                        'doc_info': doc.doc_info,
                        'processing_status': doc.processing_status.value,
                        'images': [
                            {
                                'id': image.id,
                                'media_type': image.media_type
                            }
                            for image in doc.images
                        ]
                    }
                return None

    async def get_chapter(self, doc_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a chapter by ID."""
        async with self.async_session() as session:
            async with session.begin():
                stmt = select(ChapterModel).where(
                    ChapterModel.id == chapter_id,
                    ChapterModel.document_id == doc_id
                )
                result = await session.execute(stmt)
                chapter = result.scalar_one_or_none()
                
                if chapter:
                    return {
                        'id': chapter.id,
                        'document_id': chapter.document_id,
                        'title': chapter.title,
                        'content': chapter.content,
                        'order': chapter.order,
                        'level': chapter.level,
                        'parent_id': chapter.parent_id,
                        'children': [child.id for child in chapter.children],
                        'images': [{'id': image.id, 'media_type': image.media_type} for image in chapter.images]
                    }
                return None

    async def get_chapters(self, doc_id: str, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get chapters for a document with pagination."""
        async with self.async_session() as session:
            async with session.begin():
                stmt = (
                    select(ChapterModel)
                    .options(selectinload(ChapterModel.images))
                    .where(ChapterModel.document_id == doc_id)
                    .order_by(ChapterModel.order)
                    .offset(skip)
                    .limit(limit)
                )
                result = await session.execute(stmt)
                chapters = result.scalars().all()
                
                return [
                    {
                        'id': ch.id,
                        'document_id': ch.document_id,
                        'title': ch.title,
                        'content': ch.content,
                        'order': ch.order,
                        'level': ch.level,
                        'parent_id': ch.parent_id,
                        'images': [
                            {
                                'id': image.id,
                                'media_type': image.media_type
                            }
                            for image in ch.images
                        ]
                    }
                    for ch in chapters
                ]

    async def get_all_chapters(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chapters for a document."""
        return await self.get_chapters(doc_id, skip=0, limit=1000)

    async def search_content(
        self, 
        query: str, 
        doc_id: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search through chapter content."""
        async with self.async_session() as session:
            async with session.begin():
                # Build base query
                stmt = select(ChapterModel, DocumentModel).join(
                    DocumentModel,
                    ChapterModel.document_id == DocumentModel.id
                ).where(
                    ChapterModel.content['text'].as_string().ilike(f"%{query}%")
                )
                
                # Add document filter if specified
                if doc_id:
                    stmt = stmt.where(ChapterModel.document_id == doc_id)
                
                # Add pagination
                stmt = stmt.offset(skip).limit(limit)
                
                result = await session.execute(stmt)
                matches = result.all()
                
                search_results = []
                for chapter, document in matches:
                    # Find the query in the text content
                    text_content = chapter.content['text'].lower()
                    query_lower = query.lower()
                    start_idx = text_content.find(query_lower)
                    
                    if start_idx >= 0:
                        # Get surrounding context
                        context_start = max(0, start_idx - 50)
                        context_end = min(len(text_content), start_idx + len(query) + 50)
                        snippet = chapter.content['text'][context_start:context_end]
                        
                        search_results.append({
                            'chapter_id': chapter.id,
                            'document_id': document.id,
                            'document_title': document.title,
                            'chapter_title': chapter.title,
                            'chapter_order': chapter.order,
                            'chapter_level': chapter.level,
                            'snippet': snippet
                        })
                
                return search_results

    async def update_document_status(self, document_id: str, status: str):
        """Update document processing status."""
        async with self.async_session() as session:
            async with session.begin():
                document_model = await session.get(DocumentModel, document_id)
                if document_model:
                    document_model.processing_status = status
                    await session.commit()

    async def get_document_chapters(self, document_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chapters for a document."""
        async with self.async_session() as session:
            async with session.begin():
                chapters = await session.execute(
                    text("SELECT * FROM chapters WHERE document_id = :document_id ORDER BY \"order\""),
                    {'document_id': document_id}
                )
                chapters = chapters.mappings().all()
                return [
                    {
                        'id': chapter['id'],
                        'title': chapter['title'],
                        'content': chapter['content'],
                        'order': chapter['order'],
                        'level': chapter['level'],
                        'parent_id': chapter['parent_id']
                    }
                    for chapter in chapters
                ]

    async def clear_database(self) -> Dict[str, int]:
        """Clear all entries from the database and return count of deleted items."""
        async with self.async_session() as session:
            async with session.begin():
                # Delete in correct order to respect foreign key constraints
                assoc_count = await session.execute(text("DELETE FROM chapter_images"))
                chapter_count = await session.execute(text("DELETE FROM chapters"))
                image_count = await session.execute(text("DELETE FROM images"))
                doc_count = await session.execute(text("DELETE FROM documents"))
                await session.commit()
                
                return {
                    'documents': doc_count.rowcount,
                    'chapters': chapter_count.rowcount,
                    'images': image_count.rowcount,
                    'chapter_images': assoc_count.rowcount
                }

    async def get_documents(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of all documents."""
        async with self.async_session() as session:
            async with session.begin():
                stmt = (
                    select(DocumentModel)
                    .options(selectinload(DocumentModel.images))
                    .order_by(DocumentModel.title)
                    .offset(skip)
                    .limit(limit)
                )
                result = await session.execute(stmt)
                docs = result.scalars().all()
                
                return [
                    {
                        'id': doc.id,
                        'title': doc.title,
                        'author': doc.author,
                        'format': doc.format.value,
                        'doc_info': doc.doc_info,
                        'processing_status': doc.processing_status.value,
                        'images': [
                            {
                                'id': image.id,
                                'media_type': image.media_type
                            }
                            for image in doc.images
                        ]
                    }
                    for doc in docs
                ]

    async def get_document_count(self) -> int:
        """Get total number of documents."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(text("SELECT COUNT(*) FROM documents"))
                return result.scalar_one()

    async def get_chapter_count(self, doc_id: str) -> int:
        """Get total number of chapters for a document."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    text("SELECT COUNT(*) FROM chapters WHERE document_id = :doc_id"),
                    {'doc_id': doc_id}
                )
                return result.scalar_one()
