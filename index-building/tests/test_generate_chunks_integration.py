"""
Integration tests for generate_chunks module.

This module contains integration tests that make real API calls to Gemini.
Run with: pytest index-building/test_generate_chunks_integration.py -v -s
The -s flag shows print output.

WARNING: These tests will consume API quota and may incur costs.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from generate_chunks import main
from models import DocumentQueries, QuerySection, GeneratedQuery
from gemini_utils import create_gemini_client, upload_pdf, get_test_rag_prompt, generate_with_fallback


class TestGenerateChunksIntegration:
    """Integration test cases that make real API calls."""

    @pytest.mark.integration
    def test_main_real_api_call(self, capsys):
        """Test actual API call and examine the output structure."""
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

        # Run a custom test instead of main() to use test prompt
        try:
            client = create_gemini_client()
            uploaded_file = upload_pdf(client, test_pdf)
            prompt = get_test_rag_prompt()  # Use test prompt with 10 queries per section
            response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)
            
            document_queries = response.parsed
            print(f"\nTest completed with PDF: {test_pdf}")
            print(f"Document description: {document_queries.description}")
            print(f"Number of sections: {len(document_queries.sections)}")
            total_queries = sum(len(section.queries) for section in document_queries.sections)
            print(f"Total queries generated: {total_queries}")
        except RuntimeError as e:
            pytest.fail(f"main() raised RuntimeError: {e}")
        except ValueError as e:
            pytest.fail(f"main() raised ValueError: {e}")

        # Capture the output
        captured = capsys.readouterr()
        output = captured.out

        # Basic output checks for our custom test
        assert "Uploading file:" in output
        assert "Successfully used model:" in output
        assert "Test completed with PDF:" in output
        assert "Document description:" in output
        assert "Number of sections:" in output
        assert "Total queries generated:" in output
        
        # Verify the actual response data
        assert isinstance(document_queries, DocumentQueries)
        assert document_queries.description
        assert len(document_queries.sections) > 0
        total_queries = sum(len(section.queries) for section in document_queries.sections)
        assert total_queries > 0
        assert total_queries <= 50  # Should be much less than original 100 per section

    @pytest.mark.integration
    def test_structured_output_validation(self, monkeypatch):
        """Test that the structured output matches our schema."""
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

        # Capture the parsed response
        captured_response = None

        # Import necessary modules
        from google import genai  # pylint: disable=import-outside-toplevel
        from google.genai.models import Models  # pylint: disable=import-outside-toplevel

        # Store the original generate_content method
        original_generate_content = Models.generate_content

        def patched_generate_content(self, **kwargs):
            # Call the original method
            response = original_generate_content(self, **kwargs)
            # Capture the response
            nonlocal captured_response
            if hasattr(response, 'parsed'):
                captured_response = response.parsed
            return response

        # Patch the Models class method
        monkeypatch.setattr(Models, "generate_content", patched_generate_content)

        try:
            # Run custom test with smaller PDF and test prompt
            client = create_gemini_client()
            uploaded_file = upload_pdf(client, test_pdf)
            prompt = get_test_rag_prompt()  # Use test prompt with 10 queries per section
            response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)
            captured_response = response.parsed
        except RuntimeError as e:
            pytest.fail(f"Test raised RuntimeError: {e}")
        except ValueError as e:
            pytest.fail(f"Test raised ValueError: {e}")

        # Validate the captured response
        assert captured_response is not None, "No response was captured"
        assert isinstance(captured_response, DocumentQueries)

        # Check description
        assert hasattr(captured_response, 'description')
        assert isinstance(captured_response.description, str)
        word_count = len(captured_response.description.split())
        assert word_count < 10, \
            f"Description has {word_count} words, should be under 10"

        # Check sections
        assert hasattr(captured_response, 'sections')
        assert isinstance(captured_response.sections, list)
        assert len(captured_response.sections) > 0, "No sections found"

        # Check each section
        for i, section in enumerate(captured_response.sections):
            assert isinstance(section, QuerySection), f"Section {i} is not a QuerySection"
            assert hasattr(section, 'section_name')
            assert isinstance(section.section_name, str)
            assert section.section_name, f"Section {i} has empty name"

            assert hasattr(section, 'queries')
            assert isinstance(section.queries, list)
            assert len(section.queries) > 0, f"Section '{section.section_name}' has no queries"

            # Check each query
            for j, query in enumerate(section.queries):
                assert isinstance(query, GeneratedQuery), \
                    f"Query {j} in section '{section.section_name}' is not a GeneratedQuery"
                assert hasattr(query, 'query')
                assert isinstance(query.query, str)
                assert query.query, f"Query {j} in section '{section.section_name}' is empty"
                # Check if query is in Japanese (contains Japanese characters)
                assert any('\u3040' <= char <= '\u309f' or  # Hiragana
                          '\u30a0' <= char <= '\u30ff' or  # Katakana
                          '\u4e00' <= char <= '\u9fff'     # Kanji
                          for char in query.query), \
                    f"Query '{query.query}' doesn't contain Japanese characters"

        # Print summary
        total_queries = sum(len(section.queries) for section in captured_response.sections)
        print("\n=== Structured Output Summary ===")
        print(f"Document Description: {captured_response.description}")
        print(f"Number of sections: {len(captured_response.sections)}")
        print(f"Total queries: {total_queries}")
        for section in captured_response.sections:
            print(f"  - {section.section_name}: {len(section.queries)} queries")


if __name__ == "__main__":
    # Run only integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
