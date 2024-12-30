# Book Reader and Analysis System

A FastAPI-based application for processing and analyzing EPUB and PDF documents, with a focus on rich content preservation and efficient content retrieval.

## Features

- Process EPUB and PDF documents
- Extract and preserve rich content (HTML, text, images, tables)
- Hierarchical chapter organization
- Full-text search with context
- RESTful API interface

## Architecture

### Core Components

#### Document Processing
- Independent processors for EPUB and PDF formats
- Rich content extraction and structuring
- Image extraction and storage
- Table detection and processing

#### FastAPI Backend
- RESTful API for document management
- Asynchronous document processing
- Content search and retrieval
- Progress tracking and status updates

#### Storage Layer
- SQLite database with async support
- JSON-based content storage
- Efficient binary image storage
- Hierarchical chapter relationships

## Project Structure

```
.
├── app/
│   ├── api/              # FastAPI endpoints and models
│   ├── core/             # Document processors
│   │   ├── epub_processor.py
│   │   ├── pdf_processor.py
│   │   └── base_processor.py
│   ├── models/          # Data models
│   ├── storage/         # Database layer
│   └── utils/           # Shared utilities
├── DESIGN.md           # Detailed design specification
├── books.db           # SQLite database
├── requirements.txt   # Project dependencies
└── temp_uploads/     # Temporary storage for uploads
```

## API Endpoints

### Document Management
- `POST /documents/upload` - Upload new document
- `GET /documents/{id}` - Get document details
- `GET /documents/{id}/status` - Check processing status
- `GET /documents` - List all documents

### Chapter Access
- `GET /documents/{id}/chapters` - List chapters (preview)
- `GET /documents/{id}/chapters/{chapter_id}` - Get chapter details
- `GET /documents/{id}/chapters/hierarchy` - Get chapter hierarchy

### Search
- `GET /search` - Search through document content

## Data Models

### Document
```python
{
    "id": str,
    "title": str,
    "author": str,
    "format": str,
    "doc_info": dict,
    "processing_status": str,
    "images": dict  # Binary image data
}
```

### Chapter
```python
{
    "id": str,
    "document_id": str,
    "title": str,
    "content": {
        "html": str,
        "text": str,
        "footnotes": list,
        "images": list,
        "tables": list
    },
    "order": int,
    "level": int,
    "parent_id": str,
    "children": list
}
```

## Setup and Usage

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

3. Access the API at `http://localhost:8000`
   - API documentation available at `/docs`
   - OpenAPI spec at `/openapi.json`

## Development

- Follow DESIGN.md for implementation details
- Run tests with pytest
- Use async/await for database operations
- Handle binary data appropriately for images

## Error Handling

- Processing status tracked via ProcessingStatus enum
- Errors stored in document's doc_info
- Proper HTTP status codes for API responses
- Async task tracking for long operations
