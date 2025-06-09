"""Common utilities for testing."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from dotenv import load_dotenv

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
                pdf_page_number=1,
                queries=[
                    GeneratedQuery(query="テストクエリ1"),
                    GeneratedQuery(query="テストクエリ2"),
                ],
            ),
            QuerySection(
                section_name="Section 2",
                pdf_page_number=2,
                queries=[GeneratedQuery(query="テストクエリ3")],
            ),
        ],
    )


def create_large_sample_document_queries():
    """Create a larger sample DocumentQueries for testing."""
    sections = []
    for i in range(3):
        queries = [GeneratedQuery(query=f"テストクエリ{j}") for j in range(5)]
        sections.append(
            QuerySection(section_name=f"Section {i+1}", pdf_page_number=i + 1, queries=queries)
        )

    return DocumentQueries(description="Large test document", sections=sections)


def create_mock_pdf_path():
    """Create a mock PDF path for testing."""
    return "test_document.pdf"


def setup_integration_test_environment():
    """Common setup for integration tests that need API key and PDF file."""
    # Load environment variables from current directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Check if API key exists
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not found in environment")

    # Use smallest PDF file for faster testing
    test_pdf = "register_life_app.pdf"
    pdf_path = Path(__file__).parent.parent / "resources" / test_pdf
    if not pdf_path.exists():
        pytest.skip(f"PDF file not found: {pdf_path}")

    return test_pdf, pdf_path


def run_gemini_test_with_pdf(test_pdf):
    """Common pattern for running Gemini API tests with a PDF."""
    from gemini_utils import (  # pylint: disable=import-outside-toplevel
        create_gemini_client,
        upload_pdf,
        get_test_rag_prompt,
        generate_with_fallback,
    )

    client = create_gemini_client()
    uploaded_file = upload_pdf(client, test_pdf)
    prompt = get_test_rag_prompt()  # Use test prompt with 10 queries per section
    response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)

    return response.parsed
