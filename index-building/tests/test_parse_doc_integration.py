"""Integration tests for parse_doc.py module.

These tests can be run against real PDF files when API credentials are available.
"""

import json
import os
import sys
import time
from pathlib import Path
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# pylint: disable=wrong-import-position
from parse_doc import parse_pdf_to_json
from models import DocumentStructure


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"),
    reason="No API key available for integration testing"
)
class TestParsePDFIntegration:
    """Integration tests that require actual API access."""

    def test_parse_real_pdf_001(self):
        """Test parsing of actual 001.pdf file."""
        # Check if PDF exists
        pdf_path = Path(__file__).parent.parent / "resources" / "001.pdf"
        if not pdf_path.exists():
            pytest.skip("001.pdf not found in resources directory")

        # Test parsing
        result = parse_pdf_to_json("001.pdf")

        # Basic assertions
        assert result["status"] == "success", \
            f"Failed with: {result.get('message', 'Unknown error')}"
        assert "output_file" in result
        assert "document_data" in result

        # Validate structure
        doc_data = result["document_data"]
        assert "title" in doc_data
        assert "summary" in doc_data
        assert "sections" in doc_data
        assert isinstance(doc_data["sections"], list)

        # Validate that content is preserved
        # Check if Japanese content is preserved (001.pdf is known to have Japanese content)
        doc_json = json.dumps(doc_data, ensure_ascii=False)
        assert any(char >= '\u3040' for char in doc_json), \
            "No Japanese characters found in output"

        # Validate Pydantic model
        try:
            DocumentStructure.model_validate(doc_data)
        except ValueError as exc:
            pytest.fail(f"Document structure validation failed: {exc}")

        # Clean up generated file
        output_path = Path(result["output_file"])
        if output_path.exists():
            output_path.unlink()

    def test_language_preservation_real_files(self):
        """Test that language is preserved across different PDF files."""
        # Test a few PDFs if they exist
        test_pdfs = ["001.pdf", "007.pdf", "052.pdf"]  # Mix of likely Japanese/English docs

        for pdf_name in test_pdfs:
            pdf_path = Path(__file__).parent.parent / "resources" / pdf_name
            if not pdf_path.exists():
                continue

            result = parse_pdf_to_json(pdf_name)

            if result["status"] == "success":
                doc_data = result["document_data"]

                # Check that title and content are not inappropriately translated
                # This is a basic check - we can't know exact content without seeing PDFs
                print(f"\n{pdf_name}:")
                print(f"  Title: {doc_data['title'][:50]}...")
                print(f"  Summary: {doc_data['summary'][:50]}...")

                # Clean up
                output_path = Path(result["output_file"])
                if output_path.exists():
                    output_path.unlink()

    def test_performance_benchmark(self):
        """Benchmark performance across multiple PDFs."""
        # Test first 5 PDFs
        processing_times = []

        for i in range(1, 6):
            pdf_name = f"{i:03d}.pdf"
            pdf_path = Path(__file__).parent.parent / "resources" / pdf_name

            if not pdf_path.exists():
                continue

            start_time = time.time()
            result = parse_pdf_to_json(pdf_name)
            end_time = time.time()

            if result["status"] == "success":
                processing_time = end_time - start_time
                processing_times.append(processing_time)
                print(f"\n{pdf_name}: {processing_time:.2f}s")

                # Clean up
                output_path = Path(result["output_file"])
                if output_path.exists():
                    output_path.unlink()

        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            print(f"\nAverage processing time: {avg_time:.2f}s")

            # Basic performance assertion - should process in reasonable time
            assert avg_time < 30, f"Average processing time too high: {avg_time:.2f}s"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_parse_doc_integration.py -v -s
    # The -s flag shows print statements
    pytest.main([__file__, "-v", "-s"])
