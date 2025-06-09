"""
Test cases for the process_pdf_to_csv function.

This module contains unit and integration tests for the PDF to CSV processing functionality.
"""

import csv
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from dotenv import load_dotenv

from generate_chunks import process_pdf_to_csv
from models import DocumentQueries, QuerySection, GeneratedQuery
from .test_utils import create_mock_gemini_client, create_sample_document_queries


class TestProcessPdfToCsv:
    """Test cases for process_pdf_to_csv function."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and cleanup for tests."""
        # Setup: Remove test CSV file if it exists (in main directory)
        test_csv = Path(__file__).parent.parent / "test_output.csv"
        if test_csv.exists():
            test_csv.unlink()

        yield

        # Teardown: Remove test CSV file after test
        if test_csv.exists():
            test_csv.unlink()

    def test_process_pdf_creates_csv_with_headers(self):
        """Test that processing a PDF creates a CSV file with correct headers."""
        # Use utility functions for mock setup
        mock_client, mock_uploaded_file = create_mock_gemini_client()
        mock_response = Mock()
        mock_document_queries = create_sample_document_queries()
        mock_response.parsed = mock_document_queries
        mock_client.models.generate_content.return_value = mock_response

        # Create a temporary test PDF file
        test_pdf_path = Path(__file__).parent / "resources" / "test.pdf"
        test_pdf_path.parent.mkdir(exist_ok=True)
        test_pdf_path.write_bytes(b"dummy pdf content")

        try:
            # Patch the functions
            with patch("generate_chunks.create_gemini_client", return_value=mock_client):
                with patch("generate_chunks.upload_pdf", return_value=mock_uploaded_file):
                    with patch(
                        "generate_chunks.generate_with_fallback", return_value=mock_response
                    ):
                        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                            # Call the function
                            result = process_pdf_to_csv("test.pdf", "test_output.csv")
        finally:
            # Cleanup test PDF
            if test_pdf_path.exists():
                test_pdf_path.unlink()

        # Verify the result
        assert result == mock_document_queries

        # Verify CSV file was created with correct content (in main directory)
        csv_path = Path(__file__).parent.parent / "test_output.csv"
        assert csv_path.exists()

        # Read and verify CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Check headers
        assert reader.fieldnames == ["description", "section_name", "subsection_name", "subsection_pdf_page_number", "query"]

        # Check data
        assert len(rows) == 3
        assert rows[0]["description"] == "Test document description"
        assert rows[0]["section_name"] == "Section 1"
        assert rows[0]["query"] == "テストクエリ1"

    def test_process_pdf_appends_to_existing_csv(self):
        """Test that processing a PDF appends to an existing CSV file."""
        # Create initial CSV file (in main directory)
        csv_path = Path(__file__).parent.parent / "test_output.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["description", "section_name", "subsection_name", "subsection_pdf_page_number", "query"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "description": "Existing doc",
                    "section_name": "Existing section",
                    "subsection_name": "Existing subsection",
                    "subsection_pdf_page_number": 1,
                    "query": "既存のクエリ",
                }
            )

        # Use utility functions for mock setup
        mock_client, mock_uploaded_file = create_mock_gemini_client()
        mock_response = Mock()

        # Create mock structured response
        mock_document_queries = DocumentQueries(
            description="New document",
            sections=[
                QuerySection(
                    section_name="New Section",
                    subsection_name="New Subsection",
                    subsection_pdf_page_number=1,
                    queries=[GeneratedQuery(query="新しいクエリ")],
                )
            ],
        )

        mock_response.parsed = mock_document_queries
        mock_client.models.generate_content.return_value = mock_response

        # Create a temporary test PDF file
        test_pdf_path = Path(__file__).parent / "resources" / "test.pdf"
        test_pdf_path.parent.mkdir(exist_ok=True)
        test_pdf_path.write_bytes(b"dummy pdf content")

        try:
            # Patch and call
            with patch("generate_chunks.create_gemini_client", return_value=mock_client):
                with patch("generate_chunks.upload_pdf", return_value=mock_uploaded_file):
                    with patch(
                        "generate_chunks.generate_with_fallback", return_value=mock_response
                    ):
                        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                            process_pdf_to_csv("test.pdf", "test_output.csv")
        finally:
            # Cleanup test PDF
            if test_pdf_path.exists():
                test_pdf_path.unlink()

        # Verify CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["description"] == "Existing doc"
        assert rows[1]["description"] == "New document"
        assert rows[1]["query"] == "新しいクエリ"

    def test_process_pdf_missing_api_key(self):
        """Test that function raises ValueError when API key is missing."""
        # Mock create_gemini_client to raise ValueError
        with patch(
            "generate_chunks.create_gemini_client",
            side_effect=ValueError("GOOGLE_API_KEY not found in environment variables"),
        ):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
                process_pdf_to_csv("test.pdf")

    def test_process_pdf_file_not_found(self):
        """Test that function raises FileNotFoundError for non-existent PDF."""
        mock_client, _ = create_mock_gemini_client()
        with patch("generate_chunks.create_gemini_client", return_value=mock_client):
            with patch(
                "generate_chunks.upload_pdf", side_effect=FileNotFoundError("PDF file not found")
            ):
                with pytest.raises(FileNotFoundError, match="PDF file not found"):
                    process_pdf_to_csv("non_existent.pdf")

    def test_process_pdf_all_models_fail(self):
        """Test that function raises RuntimeError when all models fail."""
        mock_client, mock_uploaded_file = create_mock_gemini_client()

        with patch("generate_chunks.create_gemini_client", return_value=mock_client):
            with patch("generate_chunks.upload_pdf", return_value=mock_uploaded_file):
                with patch(
                    "generate_chunks.generate_with_fallback",
                    side_effect=RuntimeError("All models failed"),
                ):
                    with pytest.raises(RuntimeError, match="All models failed"):
                        process_pdf_to_csv("test.pdf")

    @pytest.mark.integration
    def test_process_pdf_integration(self):
        """Integration test with real API call (skip if no API key)."""
        # Load environment variables from current directory
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)

        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not found in environment")

        # Use smallest PDF file for faster testing
        test_pdf = "register_life_app.pdf"
        pdf_path = Path(__file__).parent.parent / "resources" / test_pdf
        if not pdf_path.exists():
            pytest.skip(f"PDF file not found: {pdf_path}")

        # Process the PDF with test integration - create a custom version with test prompt
        from gemini_utils import (
            create_gemini_client,
            upload_pdf,
            get_rag_prompt,
            generate_with_fallback,
        )
        from csv_utils import write_queries_to_csv

        client = create_gemini_client()
        uploaded_file = upload_pdf(client, test_pdf)
        prompt = get_rag_prompt(10)  # Use 10 queries per section for tests
        response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)

        result = response.parsed
        if not result:
            raise RuntimeError("Failed to parse response from Gemini")

        write_queries_to_csv(result, "test_integration_output.csv")

        # Verify result structure
        assert isinstance(result, DocumentQueries)
        assert result.description
        assert len(result.sections) > 0

        # Verify CSV was created (in main directory)
        csv_path = Path(__file__).parent.parent / "test_integration_output.csv"
        assert csv_path.exists()

        # Read and verify CSV has content
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) > 0
        assert all(row["description"] for row in rows)
        assert all(row["section_name"] for row in rows)
        assert all(row["subsection_name"] for row in rows)
        assert all(row["subsection_pdf_page_number"] for row in rows)
        assert all(row["query"] for row in rows)

        # Cleanup
        csv_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
