"""Tests for parse_doc.py module."""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# pylint: disable=wrong-import-position
from parse_doc import parse_pdf_to_json, _create_gemini_client
from models import DocumentStructure


class TestParsePDFToJSON:
    """Test cases for PDF parsing functionality."""

    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Set up mock environment variables."""
        monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "test-credentials.json")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-east5")

    @pytest.fixture
    def mock_pdf_content(self):
        """Mock PDF content for testing."""
        return b"Mock PDF content"

    @pytest.fixture
    def mock_gemini_response_japanese(self):
        """Mock Gemini response for Japanese document."""
        return {
            "title": "アウトドア シェアグッズ ガイド",
            "summary": "パークタワー晴海のアウトドアグッズレンタルガイドです。",
            "sections": [
                {
                    "name": "バーベキューグッズ",
                    "subsections": [
                        {
                            "name": "IGTキッチンセット",
                            "text": "IGTフレーム、テーブル、チェアセット",
                            "page_number": 2
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def mock_gemini_response_english(self):
        """Mock Gemini response for English document."""
        return {
            "title": "User Manual",
            "summary": "This is a user manual for the product.",
            "sections": [
                {
                    "name": "Introduction",
                    "subsections": [
                        {
                            "name": "Getting Started",
                            "text": "Welcome to the product guide.",
                            "page_number": 1
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def mock_gemini_response_mixed(self):
        """Mock Gemini response for mixed language document."""
        return {
            "title": "OUTDOOR & ACTIVE PARK SHARE THE GOODS GUIDE",
            "summary": "このドキュメントは、パークタワー晴海のアウトドア＆アクティブパークで"
                      "利用できるシェアグッズに関するガイドです。",
            "sections": [
                {
                    "name": "アウトドア シェアグッズ",
                    "subsections": [
                        {
                            "name": "暖憩テラス内 バーベキューグッズ",
                            "text": "A IGTキッチンセット\nB テーブルウェアセット",
                            "page_number": 2
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def setup_mocks(self, mock_pdf_content):
        """Common mock setup for tests."""
        with patch('parse_doc.genai.Client') as mock_client_class, \
             patch('builtins.open', create=True) as mock_open, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.mkdir') as mock_mkdir:

            mock_exists.return_value = True
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock file operations
            mock_file = MagicMock()
            mock_file.read.return_value = mock_pdf_content
            mock_open.return_value.__enter__.return_value = mock_file

            yield {
                'client': mock_client,
                'open': mock_open,
                'exists': mock_exists,
                'mkdir': mock_mkdir
            }

    def test_successful_pdf_parsing_japanese(
        self, mock_env_vars, mock_gemini_response_japanese, setup_mocks
    ):  # pylint: disable=unused-argument
        """Test successful parsing of Japanese PDF."""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps(mock_gemini_response_japanese)
        mock_response.parsed = DocumentStructure.model_validate(mock_gemini_response_japanese)
        setup_mocks['client'].models.generate_content.return_value = mock_response

        # Test parsing
        result = parse_pdf_to_json("001.pdf", "test_output")

        # Assertions
        assert result["status"] == "success"
        assert "output_file" in result
        assert result["model_used"] in [
            "gemini-2.5-pro-preview-06-05", "gemini-2.0-flash", "gemini-1.5-flash"
        ]

        # Verify JSON structure
        doc_data = result["document_data"]
        assert doc_data["title"] == "アウトドア シェアグッズ ガイド"
        assert doc_data["summary"] == "パークタワー晴海のアウトドアグッズレンタルガイドです。"
        assert len(doc_data["sections"]) == 1
        assert doc_data["sections"][0]["name"] == "バーベキューグッズ"

    def test_language_preservation_mixed(
        self, mock_env_vars, mock_gemini_response_mixed, setup_mocks
    ):  # pylint: disable=unused-argument
        """Test that mixed language documents preserve original text."""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps(mock_gemini_response_mixed)
        mock_response.parsed = DocumentStructure.model_validate(mock_gemini_response_mixed)
        setup_mocks['client'].models.generate_content.return_value = mock_response

        # Test parsing
        result = parse_pdf_to_json("001.pdf", "test_output")

        # Assertions for language preservation
        doc_data = result["document_data"]
        # English title preserved
        assert doc_data["title"] == "OUTDOOR & ACTIVE PARK SHARE THE GOODS GUIDE"
        # Japanese summary for Japanese content
        assert "このドキュメントは" in doc_data["summary"]
        # Japanese section name
        assert doc_data["sections"][0]["name"] == "アウトドア シェアグッズ"
        assert "IGTキッチンセット" in doc_data["sections"][0]["subsections"][0]["text"]

    def test_missing_pdf_file(self, mock_env_vars):  # pylint: disable=unused-argument
        """Test handling of missing PDF file."""
        result = parse_pdf_to_json("nonexistent.pdf")

        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_empty_pdf_filename(self, mock_env_vars):  # pylint: disable=unused-argument
        """Test handling of empty PDF filename."""
        result = parse_pdf_to_json("")

        assert result["status"] == "error"
        assert "No PDF filename provided" in result["message"]

    def test_gemini_api_failure(self, mock_env_vars, setup_mocks):  # pylint: disable=unused-argument
        """Test handling of Gemini API failures."""
        # Mock API failure for all models
        setup_mocks['client'].models.generate_content.side_effect = Exception("API Error")

        # Test parsing
        result = parse_pdf_to_json("001.pdf")

        # Assertions
        assert result["status"] == "error"
        assert "All models failed" in result["message"]

    def test_json_structure_validation(self, mock_env_vars, setup_mocks):  # pylint: disable=unused-argument
        """Test that generated JSON matches the expected structure."""
        # Create a complete response
        complete_response = {
            "title": "Test Document",
            "summary": "Test summary",
            "sections": [
                {
                    "name": "Section 1",
                    "subsections": [
                        {
                            "name": "Subsection 1.1",
                            "text": "Content of subsection 1.1",
                            "page_number": 1
                        },
                        {
                            "name": "Subsection 1.2",
                            "text": "Content of subsection 1.2",
                            "page_number": 2
                        }
                    ]
                },
                {
                    "name": "Section 2",
                    "subsections": [
                        {
                            "name": "Subsection 2.1",
                            "text": "Content of subsection 2.1",
                            "page_number": 3
                        }
                    ]
                }
            ]
        }

        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps(complete_response)
        mock_response.parsed = DocumentStructure.model_validate(complete_response)
        setup_mocks['client'].models.generate_content.return_value = mock_response

        # Test parsing
        result = parse_pdf_to_json("test.pdf", "test_output")

        # Validate structure
        assert result["status"] == "success"
        doc_data = result["document_data"]

        # Validate required fields
        assert "title" in doc_data
        assert "summary" in doc_data
        assert "sections" in doc_data

        # Validate sections structure
        assert isinstance(doc_data["sections"], list)
        assert len(doc_data["sections"]) == 2

        for section in doc_data["sections"]:
            assert "name" in section
            assert "subsections" in section
            assert isinstance(section["subsections"], list)

            for subsection in section["subsections"]:
                assert "name" in subsection
                assert "text" in subsection
                assert "page_number" in subsection
                assert isinstance(subsection["page_number"], int)

    def test_model_fallback(self, mock_env_vars, mock_gemini_response_english, setup_mocks):  # pylint: disable=unused-argument
        """Test that model fallback works when primary model fails."""
        # Mock first model failure, second model success
        mock_response = Mock()
        mock_response.text = json.dumps(mock_gemini_response_english)
        mock_response.parsed = DocumentStructure.model_validate(mock_gemini_response_english)

        setup_mocks['client'].models.generate_content.side_effect = [
            Exception("Model not found"),  # First model fails
            mock_response  # Second model succeeds
        ]

        # Test parsing
        result = parse_pdf_to_json("test.pdf")

        # Assertions
        assert result["status"] == "success"
        assert result["model_used"] == "gemini-2.0-flash"  # Second model in the list

    def test_create_gemini_client_vertex_ai(self, mock_env_vars):  # pylint: disable=unused-argument
        """Test Gemini client creation with Vertex AI."""
        with patch('parse_doc.genai.Client') as mock_client_class:
            with patch('pathlib.Path.exists', return_value=True):
                _create_gemini_client()

                # Verify Vertex AI client was created
                mock_client_class.assert_called_once_with(vertexai=True)

    def test_create_gemini_client_direct_api(self, monkeypatch):
        """Test Gemini client creation with direct API."""
        monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")

        with patch('parse_doc.genai.Client') as mock_client_class:
            with patch('pathlib.Path.exists', return_value=True):
                _create_gemini_client()

                # Verify direct API client was created
                mock_client_class.assert_called_once_with(api_key="test-api-key")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
