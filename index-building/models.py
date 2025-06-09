"""Data models for the PDF processing system."""

from typing import List
from pydantic import BaseModel


class GeneratedQuery(BaseModel):
    """Model for a single generated query."""

    query: str


class QuerySection(BaseModel):
    """Model for a section containing multiple queries."""

    section_name: str
    pdf_page_number: int
    queries: List[GeneratedQuery]


class DocumentQueries(BaseModel):
    """Model for all queries across all document sections."""

    description: str
    sections: List[QuerySection]
