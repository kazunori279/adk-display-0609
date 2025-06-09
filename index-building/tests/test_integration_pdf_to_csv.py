#!/usr/bin/env python3
"""
Integration test for process_pdf_to_csv function.

This test makes real API calls to Gemini and processes an actual PDF file.
Run with: python test_integration_pdf_to_csv.py

WARNING: This will consume API quota and may incur costs.
"""

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path so we can import generate_chunks
sys.path.insert(0, str(Path(__file__).parent))
from models import DocumentQueries  # pylint: disable=wrong-import-position
from gemini_utils import (  # pylint: disable=wrong-import-position
    create_gemini_client,
    upload_pdf,
    get_rag_prompt,
    generate_with_fallback,
)
from csv_utils import write_queries_to_csv, print_query_summary  # pylint: disable=wrong-import-position


def test_process_pdf_to_csv_integration():
    """Integration test that processes a real PDF with Gemini API."""
    print("Running integration test for process_pdf_to_csv...")
    print("-" * 50)

    # Load environment variables from current directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Check if API key exists
    if not os.environ.get("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY not found in environment")
        print("Please set GOOGLE_API_KEY in your .env file or environment")
        import pytest

        pytest.skip("GOOGLE_API_KEY not found in environment")

    # Choose the smallest PDF for testing
    test_pdf = "register_life_app.pdf"  # Smallest PDF (545KB)
    test_csv = "test_integration_output.csv"

    # Check if PDF exists
    pdf_path = Path(__file__).parent.parent / "resources" / test_pdf
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        import pytest

        pytest.skip(f"PDF file not found: {pdf_path}")

    print(f"📄 Testing with PDF: {test_pdf}")
    print(f"📊 Output CSV: {test_csv}")

    # Clean up any existing test CSV (in data directory)
    data_dir = Path(__file__).parent.parent / "data"
    csv_path = data_dir / test_csv
    if csv_path.exists():
        csv_path.unlink()
        print("🗑️  Removed existing test CSV")

    try:
        # Process the PDF with test prompt (10 queries per section)
        print("\n🚀 Processing PDF with Gemini API using test prompt...")
        client = create_gemini_client()
        uploaded_file = upload_pdf(client, test_pdf)
        prompt = get_rag_prompt(10)  # Use 10 queries per section for tests
        response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)

        document_queries = response.parsed
        if not document_queries:
            raise RuntimeError("Failed to parse response from Gemini")

        # Write to CSV and print summary
        write_queries_to_csv(document_queries, test_csv)
        print(f"Processed {test_pdf} and appended to {test_csv}")
        print_query_summary(document_queries)

        result = document_queries

        # Verify the result
        print("\n✅ Processing completed successfully!")
        print(f"📝 Document Description: {result.description}")
        print(f"📑 Number of sections: {len(result.sections)}")

        # Count total queries
        total_queries = sum(len(section.queries) for section in result.sections)
        print(f"❓ Total queries generated: {total_queries}")

        # Show sample queries from each section
        print("\n📋 Sample queries by section:")
        for i, section in enumerate(result.sections[:3], 1):  # Show first 3 sections
            print(f"\n  {i}. {section.section_name} ({len(section.queries)} queries)")
            # Show first 3 queries from each section
            for j, query in enumerate(section.queries[:3], 1):
                print(f"     {j}. {query.query}")
            if len(section.queries) > 3:
                print(f"     ... and {len(section.queries) - 3} more queries")

        if len(result.sections) > 3:
            print(f"\n  ... and {len(result.sections) - 3} more sections")

        # Verify CSV file was created
        assert csv_path.exists(), "CSV file was not created"

        # Read and verify CSV content
        print("\n📊 Verifying CSV file content...")
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"📈 CSV contains {len(rows)} rows")

        # Verify headers
        expected_headers = ["pdf_filename", "description", "section_name", "subsection_name", "subsection_pdf_page_number", "query"]
        assert reader.fieldnames == expected_headers, f"Unexpected headers: {reader.fieldnames}"
        print(f"✅ Headers are correct: {expected_headers}")

        # Verify data integrity
        assert (
            len(rows) == total_queries
        ), f"Row count mismatch: CSV has {len(rows)} rows, expected {total_queries}"

        # Check that all rows have data
        for i, row in enumerate(rows):
            for field in expected_headers:
                assert row[field], f"Empty field '{field}' in row {i+1}"

        print("✅ All fields contain data")

        # Check that queries are in Japanese
        japanese_queries = 0
        for row in rows:
            query = row["query"]
            if any(
                "\u3040" <= char <= "\u309f"  # Hiragana
                or "\u30a0" <= char <= "\u30ff"  # Katakana
                or "\u4e00" <= char <= "\u9fff"  # Kanji
                for char in query
            ):
                japanese_queries += 1

        print(f"✅ {japanese_queries}/{len(rows)} queries contain Japanese characters")

        # Show sample CSV content
        print("\n📄 Sample CSV content (first 5 rows):")
        print("-" * 80)
        for i, row in enumerate(rows[:5]):
            print(f"Row {i+1}:")
            print(f"  PDF: {row['pdf_filename']}")
            print(f"  Document: {row['description']}")
            print(f"  Section: {row['section_name']}")
            print(f"  Subsection: {row['subsection_name']}")
            print(f"  Page: {row['subsection_pdf_page_number']}")
            print(f"  Query: {row['query']}")
        if len(rows) > 5:
            print(f"... and {len(rows) - 5} more rows")

        print("\n✅ Integration test passed!")

    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback

        traceback.print_exc()
        raise

    finally:
        # Clean up test CSV
        if csv_path.exists():
            csv_path.unlink()
            print("\n🗑️  Cleaned up test CSV file")


def main():
    """Run the integration test."""
    print("=" * 50)
    print("PDF to CSV Integration Test")
    print("=" * 50)

    try:
        test_process_pdf_to_csv_integration()
        print("\n" + "=" * 50)
        print("✅ TEST PASSED")
        sys.exit(0)
    except (AssertionError, ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
