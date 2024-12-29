import re
from typing import Optional
import nltk
from nltk.tokenize import sent_tokenize

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not isinstance(text, str):
        return ""
    
    try:
        # Remove multiple whitespace
        text = ' '.join(text.split())
        
        # Remove control characters while preserving essential punctuation
        cleaned = ''
        for char in text:
            if char.isprintable() or char in ['\n', '\t']:
                cleaned += char
        text = cleaned
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    except Exception as e:
        print(f"Warning: Error cleaning text: {str(e)}")
        return text if isinstance(text, str) else ""

def extract_chapter_title(text: str, max_words: int = 15) -> str:
    """Extract chapter title from the beginning of text content."""
    # Common chapter header patterns
    patterns = [
        r'^Chapter\s+\d+[:\s]*(.*?)(?=\n|$)',
        r'^\d+\.\s*(.*?)(?=\n|$)',
        r'^CHAPTER\s+\d+[:\s]*(.*?)(?=\n|$)',
    ]
    
    # Try to match common chapter patterns
    for pattern in patterns:
        match = re.match(pattern, text.strip(), re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            if title:
                words = title.split()
                return ' '.join(words[:max_words])
    
    # If no pattern matches, take the first sentence
    sentences = sent_tokenize(text.strip())
    if sentences:
        words = sentences[0].split()
        return ' '.join(words[:max_words])
    
    return "Untitled Chapter"

def get_chapter_number(text: str) -> Optional[int]:
    """Extract chapter number from text if present."""
    patterns = [
        r'^Chapter\s+(\d+)',
        r'^(\d+)\.',
        r'^CHAPTER\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text.strip(), re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None

def is_likely_chapter_boundary(text: str) -> bool:
    """Determine if text likely represents a chapter boundary."""
    # Common chapter boundary indicators
    indicators = [
        r'^Chapter\s+\d+',
        r'^\d+\.',
        r'^CHAPTER\s+\d+',
        r'^\s*\*\s*\*\s*\*\s*$',  # Scene breaks
        r'^\s*#\s*$',             # Scene breaks
        r'^\s*$'                  # Blank lines
    ]
    
    return any(re.match(pattern, text.strip(), re.IGNORECASE) for pattern in indicators)

def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using NLTK."""
    return sent_tokenize(text)
