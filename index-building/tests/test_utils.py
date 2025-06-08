"""Common utilities for testing."""
from unittest.mock import Mock
from models import DocumentQueries, QuerySection, GeneratedQuery


def create_mock_gemini_client():
    """Create a mock Gemini client for testing."""
    mock_client = Mock()
    mock_uploaded_file = Mock()
    mock_client.files.upload.return_value = mock_uploaded_file
    return mock_client, mock_uploaded_file


def create_mock_response(document_queries: DocumentQueries):
    """Create a mock Gemini response with specified content."""
    mock_response = Mock()
    mock_response.text = document_queries.model_dump_json()
    return mock_response


def create_sample_document_queries():
    """Create sample DocumentQueries for testing."""
    return DocumentQueries(
        description="Test document description",
        sections=[
            QuerySection(
                section_name="Section 1",
                queries=[
                    GeneratedQuery(query="テストクエリ1"),
                    GeneratedQuery(query="テストクエリ2")
                ]
            ),
            QuerySection(
                section_name="Section 2", 
                queries=[GeneratedQuery(query="テストクエリ3")]
            )
        ]
    )


def create_large_sample_document_queries():
    """Create a larger sample DocumentQueries for testing."""
    sections = []
    for i in range(3):
        queries = [GeneratedQuery(query=f"テストクエリ{j}") for j in range(5)]
        sections.append(QuerySection(
            section_name=f"Section {i+1}",
            queries=queries
        ))
    
    return DocumentQueries(
        description="Large test document",
        sections=sections
    )


def create_mock_pdf_path():
    """Create a mock PDF path for testing."""
    return "test_document.pdf"