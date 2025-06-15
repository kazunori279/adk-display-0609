"""Data models for the PDF processing system."""

from typing import List
from pydantic import BaseModel


class GeneratedQuery(BaseModel):
    """Model for a single generated query."""

    query: str


class QuerySection(BaseModel):
    """Model for a section containing multiple queries."""

    section_name: str
    subsection_name: str
    subsection_pdf_page_number: int
    queries: List[GeneratedQuery]


class DocumentQueries(BaseModel):
    """Model for all queries across all document sections."""

    description: str
    sections: List[QuerySection]


class Subsection(BaseModel):
    """Model for a document subsection."""
    
    name: str
    text: str
    page_number: int


class Section(BaseModel):
    """Model for a document section."""
    
    name: str
    subsections: List[Subsection]


class DocumentStructure(BaseModel):
    """Model for structured document JSON output."""
    
    title: str
    summary: str
    sections: List[Section]
