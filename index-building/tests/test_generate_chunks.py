"""
Tests for generate_chunks module.

This module contains unit tests for the generate_chunks.py functionality.
"""

import os
from unittest.mock import Mock, patch, MagicMock

import pytest

from generate_chunks import main
from models import DocumentQueries, QuerySection, GeneratedQuery
from .test_utils import create_mock_gemini_client, create_sample_document_queries, create_mock_response


class TestGenerateChunks:
    """Test cases for generate_chunks module."""

    @patch('generate_chunks.create_gemini_client')
    @patch('generate_chunks.upload_pdf')
    @patch('generate_chunks.generate_with_fallback')
    def test_main_successful_first_model(self, mock_generate, mock_upload, mock_create_client):
        """Test successful execution with first model."""
        # Setup mocks using utilities
        mock_client, mock_uploaded_file = create_mock_gemini_client()
        mock_create_client.return_value = mock_client
        mock_upload.return_value = mock_uploaded_file
        
        sample_queries = create_sample_document_queries()
        mock_response = create_mock_response(sample_queries)
        mock_response.parsed = sample_queries
        mock_generate.return_value = mock_response

        # Execute
        with patch('builtins.print') as mock_print:
            main()

        # Assertions
        mock_create_client.assert_called_once()
        mock_upload.assert_called_once()
        mock_generate.assert_called_once()

        # Verify print calls
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Total sections: 2" in call for call in print_calls)

    @patch('generate_chunks.create_gemini_client')
    @patch('generate_chunks.upload_pdf')
    @patch('generate_chunks.generate_with_fallback')
    def test_main_fallback_to_second_model(self, mock_generate, mock_upload, mock_create_client):
        """Test fallback to second model when first fails."""
        # Setup mocks using utilities
        mock_client, mock_uploaded_file = create_mock_gemini_client()
        mock_create_client.return_value = mock_client
        mock_upload.return_value = mock_uploaded_file
        
        sample_queries = create_sample_document_queries()
        mock_response = create_mock_response(sample_queries)
        mock_response.parsed = sample_queries
        mock_generate.return_value = mock_response

        # Execute
        with patch('builtins.print'):
            main()

        # Assertions
        mock_create_client.assert_called_once()
        mock_upload.assert_called_once()
        mock_generate.assert_called_once()

    @patch('generate_chunks.create_gemini_client')
    @patch('generate_chunks.upload_pdf')
    @patch('generate_chunks.generate_with_fallback')
    def test_main_all_models_fail(self, mock_generate, mock_upload, mock_create_client):
        """Test when all models fail."""
        # Setup mocks using utilities
        mock_client, mock_uploaded_file = create_mock_gemini_client()
        mock_create_client.return_value = mock_client
        mock_upload.return_value = mock_uploaded_file
        
        # Generate fails
        mock_generate.side_effect = RuntimeError("All models failed")

        # Execute and verify exception
        with pytest.raises(RuntimeError, match="All models failed"):
            main()

    @patch('generate_chunks.create_gemini_client')
    def test_main_missing_api_key(self, mock_create_client):
        """Test when GOOGLE_API_KEY is missing."""
        mock_create_client.side_effect = ValueError("GOOGLE_API_KEY not found in environment variables")
        
        with pytest.raises(ValueError, match="GOOGLE_API_KEY not found in environment variables"):
            main()

    @patch('generate_chunks.create_gemini_client')
    @patch('generate_chunks.upload_pdf')
    def test_main_pdf_file_not_found(self, mock_upload, mock_create_client):
        """Test when PDF file doesn't exist."""
        mock_client, _ = create_mock_gemini_client()
        mock_create_client.return_value = mock_client
        mock_upload.side_effect = FileNotFoundError("PDF file not found")

        # Execute and verify exception
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            main()

    @patch('generate_chunks.create_gemini_client')
    @patch('generate_chunks.upload_pdf')
    def test_main_file_upload_failure(self, mock_upload, mock_create_client):
        """Test when file upload fails."""
        mock_client, _ = create_mock_gemini_client()
        mock_create_client.return_value = mock_client
        mock_upload.side_effect = Exception("Upload failed")

        # Execute and verify exception
        with pytest.raises(Exception, match="Upload failed"):
            main()


if __name__ == "__main__":
    pytest.main([__file__])
