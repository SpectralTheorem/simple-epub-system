# Book Reader and Analysis System

A modular system for processing and analyzing EPUB books, with independent components that can be used standalone or together.

## Core Components

### EPUB Processing Module
- Standalone chapter extraction and processing
- Content analysis and structuring
- Can be used independently for any EPUB processing needs

### FastAPI Backend
- RESTful API for book management
- Upload and process new books
- Query and retrieve book content
- Manage book metadata

### Storage Layer
- SQLite database backend
- Flexible storage interfaces
- Independent from processing logic

## Project Structure

```
.
├── app/
│   ├── api/                 # FastAPI endpoints
│   │   └── routes/         # API route definitions
│   ├── core/               # Independent processing modules
│   │   └── epub_processor/ # Standalone EPUB processing
│   ├── models/             # Data models and schemas
│   ├── storage/            # Database interfaces
│   └── utils/              # Shared utilities
├── books.db               # SQLite database
├── requirements.txt       # Project dependencies
└── temp_uploads/         # Temporary storage for uploads
```

## Usage

### As a Web Service

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

API endpoints will be available at `http://localhost:8000`:
- `POST /books/upload` - Upload new books
- `GET /books/{id}` - Retrieve book details
- `GET /books/{id}/chapters` - Get book chapters
- More endpoints documented in the API docs at `/docs`

### As Independent Modules

The EPUB processor can be used standalone:

```python
from app.core.epub_processor import EpubProcessor

processor = EpubProcessor()
chapters = processor.process_document("path/to/book.epub")
```

Similarly, the storage layer can be used independently:

```python
from app.storage.database import DatabaseManager

db = DatabaseManager("sqlite:///your_database.db")
```

## API Documentation

Full API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Module Independence
Each component is designed to work independently:
- Core processing modules can be used without the API layer
- Storage interfaces can be swapped out
- API layer can be extended without modifying core logic

### Adding New Features
1. Core Processing: Add new processors in `app/core/`
2. API Endpoints: Define new routes in `app/api/routes/`
3. Storage: Implement new storage interfaces in `app/storage/`

## Error Handling

Each module implements its own error handling:
- Processing errors in core modules
- API-level error responses
- Database transaction handling
- Input validation at multiple levels
