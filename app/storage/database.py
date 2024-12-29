from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Enum, ForeignKey, text, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = 'documents'

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String)
    format = Column(String, nullable=False)  # 'pdf' or 'epub'
    doc_metadata = Column(JSON)
    processing_status = Column(String, nullable=False)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chapters = relationship("ChapterModel", back_populates="document", cascade="all, delete-orphan")


class ChapterModel(Base):
    __tablename__ = 'chapters'

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey('documents.id'), nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    chapter_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("DocumentModel", back_populates="chapters")
    images = relationship("ImageModel", back_populates="chapter", cascade="all, delete-orphan")
    tables = relationship("TableModel", back_populates="chapter", cascade="all, delete-orphan")


class ImageModel(Base):
    __tablename__ = 'images'

    id = Column(String, primary_key=True)
    chapter_id = Column(String, ForeignKey('chapters.id'), nullable=False)
    file_path = Column(String, nullable=False)
    image_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("ChapterModel", back_populates="images")


class TableModel(Base):
    __tablename__ = 'tables'

    id = Column(String, primary_key=True)
    chapter_id = Column(String, ForeignKey('chapters.id'), nullable=False)
    content = Column(JSON, nullable=False)
    table_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("ChapterModel", back_populates="tables")


class DatabaseManager:
    def __init__(self, database_url: str):
        if database_url.startswith('sqlite'):
            database_url = database_url.replace('sqlite:', 'sqlite+aiosqlite:')
        self.engine = create_async_engine(database_url, echo=True)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def store_document(self, document: Dict[str, Any]) -> str:
        """Store or update a document."""
        async with self.async_session() as session:
            async with session.begin():
                # Check if document exists
                existing_doc = await session.get(DocumentModel, document['id'])
                if existing_doc:
                    # Update existing document
                    for key, value in document.items():
                        setattr(existing_doc, key, value)
                else:
                    # Create new document
                    existing_doc = DocumentModel(**document)
                    session.add(existing_doc)
                await session.commit()
                return existing_doc.id

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        async with self.async_session() as session:
            async with session.begin():
                stmt = select(DocumentModel).options(selectinload(DocumentModel.chapters)).where(DocumentModel.id == document_id)
                result = await session.execute(stmt)
                document_model = result.scalar_one_or_none()
                
                if document_model:
                    # Count the number of chapters
                    chapter_count = len(document_model.chapters)
                    return {
                        'id': document_model.id,
                        'title': document_model.title,
                        'author': document_model.author,
                        'format': document_model.format,
                        'doc_metadata': document_model.doc_metadata,
                        'processing_status': document_model.processing_status,
                        'error_message': document_model.error_message,
                        'created_at': document_model.created_at,
                        'updated_at': document_model.updated_at,
                        'chapter_count': chapter_count
                    }
                return None

    async def update_document_status(self, document_id: str, status: str, error_message: Optional[str] = None):
        """Update document processing status."""
        async with self.async_session() as session:
            async with session.begin():
                document_model = await session.get(DocumentModel, document_id)
                if document_model:
                    document_model.processing_status = status
                    document_model.error_message = error_message
                    await session.commit()

    async def store_chapter(self, chapter: Dict[str, Any]) -> str:
        """Store a new chapter and return its ID."""
        async with self.async_session() as session:
            async with session.begin():
                chapter_model = ChapterModel(**chapter)
                session.add(chapter_model)
                await session.commit()
                return chapter_model.id

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
                        'chapter_metadata': chapter['chapter_metadata'],
                        'created_at': chapter['created_at'],
                        'updated_at': chapter['updated_at']
                    }
                    for chapter in chapters
                ]

    async def clear_database(self) -> Dict[str, int]:
        """Clear all entries from the database and return count of deleted items."""
        async with self.async_session() as session:
            async with session.begin():
                # Delete from chapters first due to foreign key constraint
                chapters_result = await session.execute(text("DELETE FROM chapters"))
                documents_result = await session.execute(text("DELETE FROM documents"))
                
                return {
                    'documents_deleted': documents_result.rowcount,
                    'chapters_deleted': chapters_result.rowcount
                }

    async def get_documents(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of documents with pagination."""
        async with self.async_session() as session:
            async with session.begin():
                # Query documents with chapter counts
                stmt = text("""
                    SELECT 
                        d.id,
                        d.title,
                        d.author,
                        d.format,
                        d.doc_metadata as doc_metadata,
                        d.processing_status,
                        d.error_message,
                        d.created_at,
                        d.updated_at,
                        COUNT(c.id) as chapter_count
                    FROM documents d
                    LEFT JOIN chapters c ON d.id = c.document_id
                    GROUP BY d.id, d.title, d.author, d.format, d.doc_metadata, d.processing_status, d.error_message, d.created_at, d.updated_at
                    ORDER BY d.created_at DESC 
                    LIMIT :limit OFFSET :skip
                """)
                result = await session.execute(stmt, {"limit": limit, "skip": skip})
                documents = result.mappings().all()
                # Parse the JSON string back into a dictionary if needed
                return [{
                    **dict(doc),
                    'doc_metadata': json.loads(doc['doc_metadata']) if isinstance(doc['doc_metadata'], str) else (doc['doc_metadata'] or {})
                } for doc in documents]

    async def get_document_count(self) -> int:
        """Get total number of documents."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(text("SELECT COUNT(*) FROM documents"))
                return result.scalar()

    async def get_chapter(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chapter by ID."""
        async with self.async_session() as session:
            async with session.begin():
                stmt = text("SELECT * FROM chapters WHERE id = :chapter_id")
                result = await session.execute(stmt, {"chapter_id": chapter_id})
                chapter = result.mappings().first()
                return dict(chapter) if chapter else None

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
                if doc_id:
                    stmt = text("""
                        SELECT c.*, d.title as document_title
                        FROM chapters c
                        JOIN documents d ON c.document_id = d.id
                        WHERE c.document_id = :doc_id
                        AND (c.content LIKE :query OR c.title LIKE :query)
                        ORDER BY c.order
                        LIMIT :limit OFFSET :skip
                    """)
                    params = {
                        "doc_id": doc_id,
                        "query": f"%{query}%",
                        "limit": limit,
                        "skip": skip
                    }
                else:
                    stmt = text("""
                        SELECT c.*, d.title as document_title
                        FROM chapters c
                        JOIN documents d ON c.document_id = d.id
                        WHERE c.content LIKE :query OR c.title LIKE :query
                        ORDER BY d.title, c.order
                        LIMIT :limit OFFSET :skip
                    """)
                    params = {
                        "query": f"%{query}%",
                        "limit": limit,
                        "skip": skip
                    }

                result = await session.execute(stmt, params)
                chapters = result.mappings().all()
                
                return [
                    {
                        'chapter_id': chapter['id'],
                        'document_id': chapter['document_id'],
                        'document_title': chapter['document_title'],
                        'chapter_title': chapter['title'],
                        'chapter_order': chapter['order'],
                        'snippet': chapter['content'][:200] + '...' if len(chapter['content']) > 200 else chapter['content']
                    }
                    for chapter in chapters
                ]
