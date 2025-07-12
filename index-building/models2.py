"""Data models for the JSON PDF processing system."""

from typing import List
from pydantic import BaseModel


class Subsection(BaseModel):
    """Model for a document subsection with text content and page number."""
    
    text: str
    page_number: int


class Section(BaseModel):
    """Model for a document section containing multiple subsections."""
    
    name: str
    subsections: List[Subsection]


class StructuredDocument(BaseModel):
    """Model for the complete structured document."""
    
    title: str
    summary: str
    sections: List[Section]