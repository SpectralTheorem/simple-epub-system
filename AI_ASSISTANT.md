# AI Assistant Guide for Book Reader Application

This guide helps AI assistants understand the Book Reader application's architecture and implementation details.

## Key Design Principles

1. **Content Preservation**
   - HTML and plain text content stored together
   - Images stored as binary data in document model
   - Tables and footnotes preserved in structured format

2. **Data Structure**
   - Document and Chapter models use JSON for flexible content storage
   - Hierarchical chapter organization with parent-child relationships
   - Binary image data stored efficiently in document model

3. **Processing Flow**
   - Asynchronous document processing
   - Progress tracking and status updates
   - Error handling through doc_info field

## Implementation Details

### Document Processing

1. **Document Upload**
   ```python
   # Initial document creation
   document = {
       'id': generated_id,
       'title': filename,
       'processing_status': 'PROCESSING',
       'format': detected_format,
       'doc_info': {},
       'images': {}  # Initialize empty
   }
   ```

2. **Content Processing**
   ```python
   # Chapter content structure
   content = {
       'html': original_html,
       'text': plain_text,
       'footnotes': extracted_footnotes,
       'images': image_references,
       'tables': extracted_tables
   }
   ```

### Database Structure

1. **Documents Table**
   - Primary storage for document metadata
   - JSON column for doc_info
   - JSON column for images (binary data)

2. **Chapters Table**
   - Hierarchical structure via parent_id
   - JSON column for content
   - Order and level for hierarchy

### Error Handling

1. **Processing Errors**
   - Stored in document's doc_info
   - Status updated to FAILED
   - Error details preserved for debugging

2. **API Errors**
   - Standard HTTP status codes
   - Detailed error messages in response

## Common Tasks

### Adding New Features

1. **New Document Format**
   - Create new processor inheriting from BaseProcessor
   - Implement required methods
   - Update format enum

2. **New Content Type**
   - Add to ChapterContent structure
   - Update processor extraction methods
   - Modify API response models

### Debugging

1. **Processing Issues**
   - Check document status
   - Examine doc_info for errors
   - Review processor logs

2. **Content Problems**
   - Verify JSON content structure
   - Check image references
   - Validate chapter hierarchy

## Best Practices

1. **Content Handling**
   - Always preserve original HTML
   - Clean text content
   - Handle binary data carefully

2. **API Design**
   - Use proper HTTP methods
   - Include error details
   - Maintain backward compatibility

3. **Database Operations**
   - Use async/await consistently
   - Handle JSON data properly
   - Manage binary data efficiently

## Common Pitfalls

1. **Content Processing**
   - Missing content structure fields
   - Incorrect JSON formatting
   - Binary data handling errors

2. **Chapter Organization**
   - Invalid hierarchy relationships
   - Missing parent references
   - Incorrect order values

3. **Error Handling**
   - Incomplete error information
   - Missing status updates
   - Improper cleanup on failure

## Quick Reference

### API Endpoints
```
POST /documents/upload          - Upload new document
GET  /documents/{id}           - Get document details
GET  /documents/{id}/status    - Check processing status
GET  /documents/{id}/chapters  - List chapters
GET  /search                   - Search content
```

### Data Models
```python
# Document
{
    'id': str,
    'title': str,
    'format': str,
    'doc_info': dict,
    'processing_status': str,
    'images': dict
}

# Chapter
{
    'id': str,
    'document_id': str,
    'title': str,
    'content': {
        'html': str,
        'text': str,
        'footnotes': list,
        'images': list,
        'tables': list
    },
    'order': int,
    'level': int
}
```

### Status Values
```python
ProcessingStatus = Enum('ProcessingStatus', [
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED'
])
```
