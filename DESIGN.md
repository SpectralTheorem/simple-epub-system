# Book Reader Application Design

## System Overview

The Book Reader is a FastAPI-based application that processes and serves EPUB and PDF documents, with a focus on rich content preservation and efficient content retrieval.

## Core Components

### 1. Data Models

#### Document Model
- Primary container for book metadata and content
- Relationships:
  - One-to-Many with Chapters
  - One-to-Many with Images
- Key Fields:
  ```python
  {
    "id": str,              # Unique identifier
    "title": str,           # Book title
    "author": str,          # Book author
    "format": Enum,         # "epub" or "pdf"
    "doc_info": dict,       # Format-specific metadata
    "processing_status": Enum,
    "chapters": List[Chapter],
    "images": Dict[str, bytes]
  }
  ```

#### Chapter Model
- Represents a logical section of content
- Supports hierarchical structure
- Relationships:
  - Many-to-One with Document
  - Many-to-One with Parent Chapter (self-referential)
  - Many-to-Many with Images
- Key Fields:
  ```python
  {
    "id": str,              # Unique identifier
    "document_id": str,     # Reference to parent document
    "title": str,          
    "content": {
      "html": str,          # Original HTML content
      "text": str,          # Plain text content
      "footnotes": List,    # Extracted footnotes
      "images": List,       # Image references
      "tables": List        # Table data
    },
    "order": int,           # Position in document
    "level": int,           # Hierarchy level
    "parent_id": Optional[str],
    "children": List[str]
  }
  ```

#### Image Model
- Stores binary image data and metadata
- Relationships:
  - Many-to-One with Document
  - Many-to-Many with Chapters
- Key Fields:
  ```python
  {
    "id": str,
    "document_id": str,
    "content": bytes,
    "media_type": str
  }
  ```

### 2. Core Processing Components

#### EPUB Processor
- Handles EPUB2 and EPUB3 formats
- Responsibilities:
  1. Extract and parse navigation (TOC)
  2. Process content files (XHTML/HTML)
  3. Extract and store images
  4. Build chapter hierarchy
  5. Handle rich content (tables, footnotes)

#### PDF Processor
- Handles PDF documents
- Responsibilities:
  1. Extract text content
  2. Identify section breaks
  3. Extract images
  4. Preserve layout information

### 3. Database Layer

#### Storage Strategy
- Uses SQLAlchemy with async support
- Default: SQLite with aiosqlite
- Tables:
  1. documents
  2. chapters
  3. images
  4. chapter_images (association table)
- Database initialization occurs automatically on application startup

#### Key Operations
1. Document Storage
   - Store document metadata
   - Process and store chapters
   - Handle image storage
2. Content Retrieval
   - Get document with chapters
   - Get chapter content
   - Get images
3. Search Operations
   - Full-text search
   - Metadata search

### 4. API Layer

#### Endpoints
1. Document Management
   ```
   POST /documents/upload
   GET /documents/{id}
   GET /documents
   DELETE /database/clear    # Clear all database entries
   ```

2. Chapter Access
   ```
   GET /documents/{id}/chapters
   GET /documents/{id}/chapters/{chapter_id}
   GET /documents/{id}/hierarchy
   ```

3. Search
   ```
   GET /search?q={query}&doc_id={optional_doc_id}
   ```

### 5. Error Handling

#### Error Categories
1. Processing Errors
   - Invalid document format
   - Corrupt content
   - Missing required metadata

2. Storage Errors
   - Database connection issues
   - Constraint violations
   - Storage capacity issues

3. Retrieval Errors
   - Not found errors
   - Permission errors
   - Invalid request errors

## Implementation Guidelines

### 1. Code Organization
```
app/
├── api/
│   ├── router.py      # FastAPI routes
│   └── models.py      # API models (Pydantic)
├── core/
│   ├── epub_processor.py
│   └── pdf_processor.py
├── models/
│   └── document.py    # Core data models
├── storage/
│   └── database.py    # Database operations
└── utils/
    └── id_generator.py
```

### 2. Dependencies
- FastAPI for API layer
- SQLAlchemy for database operations
- EbookLib for EPUB processing
- PyPDF2 for PDF processing
- BeautifulSoup4 for HTML parsing

### 3. Best Practices
1. **Async Operations**
   - Use async/await consistently
   - Handle long-running tasks asynchronously

2. **Error Handling**
   - Use custom exception classes
   - Provide detailed error messages
   - Log errors appropriately

3. **Data Validation**
   - Use Pydantic models
   - Validate input at API boundaries
   - Sanitize HTML content

4. **Performance**
   - Implement pagination
   - Use appropriate indexes
   - Cache frequently accessed data

## Future Considerations

1. **Scalability**
   - Migration to PostgreSQL
   - Implement caching layer
   - Content delivery optimization

2. **Features**
   - Annotation support
   - Collaborative features
   - Export capabilities

3. **Security**
   - Authentication/Authorization
   - Rate limiting
   - Content encryption
