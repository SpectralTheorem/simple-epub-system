# AI Assistant Guide - Book Reader API

This guide helps AI assistants understand and interact with the Book Reader API, a service for processing and analyzing EPUB/PDF books.

## Service Overview

This service processes books and provides structured access to their content through a RESTful API. It handles:
- Book upload and processing
- Chapter extraction and management
- Content search and retrieval
- Document metadata management

## API Endpoints

### Document Management

1. **Upload Document**
   ```
   POST /upload
   Content-Type: multipart/form-data
   Body: file (EPUB/PDF)
   ```
   - Initiates asynchronous document processing
   - Returns document ID for status tracking

2. **Check Processing Status**
   ```
   GET /status/{doc_id}
   ```
   - Returns processing status and progress
   - Status values: "PENDING", "PROCESSING", "COMPLETED", "FAILED"

3. **List Documents**
   ```
   GET /documents?skip={skip}&limit={limit}
   ```
   - Retrieves paginated list of processed documents
   - Returns document metadata and chapter counts

4. **Get Document Details**
   ```
   GET /document/{doc_id}
   ```
   - Returns complete document metadata

### Chapter Management

1. **List Chapters (Paginated)**
   ```
   GET /document/{doc_id}/chapters?skip={skip}&limit={limit}
   ```
   - Returns paginated list of chapters for a document
   - Includes chapter previews and metadata

2. **Get All Chapters**
   ```
   GET /document/{doc_id}/all-chapters
   ```
   - Returns complete list of chapters for a document
   - Includes full chapter content and metadata
   - No pagination
   - Useful for bulk processing or analysis

3. **Get Chapter Content**
   ```
   GET /document/{doc_id}/chapter/{chapter_id}
   ```
   - Returns full chapter content and metadata

### Content Search

1. **Search Content**
   ```
   GET /search?query={query}&doc_id={doc_id}&skip={skip}&limit={limit}
   ```
   - Searches through chapter content
   - Optional doc_id parameter to search specific document
   - Returns matching snippets with context

## Data Models

### DocumentResponse
```python
{
    "id": str,
    "title": str,
    "author": Optional[str],
    "format": str,
    "doc_metadata": Optional[Dict],
    "processing_status": str,
    "error_message": Optional[str],
    "created_at": datetime,
    "updated_at": datetime,
    "chapter_count": int
}
```

### ChapterResponse
```python
{
    "id": str,
    "title": str,
    "content": str,
    "order": int,
    "chapter_metadata": Optional[Dict],
    "created_at": datetime,
    "updated_at": datetime
}
```

### SearchResult
```python
{
    "chapter_id": str,
    "document_id": str,
    "document_title": str,
    "chapter_title": str,
    "chapter_order": int,
    "snippet": str
}
```

## Best Practices for AI Assistants

1. **Document Processing**
   - Always check processing status after upload
   - Wait for "COMPLETED" status before accessing content

2. **Content Retrieval**
   - Use pagination for large documents
   - Cache frequently accessed content
   - Handle potential missing chapters or documents

3. **Search Operations**
   - Use specific document IDs when possible
   - Implement retry logic for timeouts
   - Handle empty search results gracefully

4. **Error Handling**
   - Check for error_message in document status
   - Implement appropriate retry logic
   - Handle 404 errors for missing resources

## Common Use Cases

1. **Book Analysis**
   - Upload book
   - Wait for processing
   - Retrieve chapters sequentially
   - Process content as needed

2. **Content Search**
   - Search across all documents or specific book
   - Use pagination for large result sets
   - Extract relevant snippets

3. **Document Management**
   - List available documents
   - Get specific document details
   - Monitor processing status

## Rate Limiting and Performance

- Implement appropriate delays between requests
- Use pagination parameters appropriately
- Cache frequently accessed content
- Monitor response times and adjust accordingly

## Security Notes

- Don't expose internal document IDs
- Validate all input parameters
- Handle sensitive content appropriately
- Follow API authentication requirements
