"""Utilities for generating IDs."""
import re
from datetime import datetime
import base64
import uuid

def generate_document_id(title: str) -> str:
    """Generate a unique, URL-safe document ID.
    
    Format: doc_[timestamp]_[slug]_[short_uuid]
    Example: doc_20241228_nixonland_rise_of_president_abc123
    """
    # Get timestamp in YYYYMMDD format
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    
    # Create URL-safe slug from title
    # Convert to lowercase, replace spaces/special chars with underscores
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '_', slug)
    
    # Take first 30 chars of slug to keep it reasonable
    slug = slug[:30].strip('_')
    
    # Generate short unique identifier (first 6 chars of uuid4)
    short_uuid = str(uuid.uuid4())[:6]
    
    return f"doc_{timestamp}_{slug}_{short_uuid}"

def generate_chapter_id(document_id: str, order: int) -> str:
    """Generate a chapter ID.
    
    Format: [document_id]_ch[order]
    Example: doc_20241228_nixonland_abc123_ch1
    """
    return f"{document_id}_ch{order}"
