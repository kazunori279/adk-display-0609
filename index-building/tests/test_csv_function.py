#!/usr/bin/env python3
"""
Test script for the process_pdf_to_csv function.

This script demonstrates how to use the process_pdf_to_csv function
to process a PDF file and append results to a CSV file.
"""

from generate_chunks import process_pdf_to_csv


def main():
    """Main function to test PDF to CSV processing."""
    # Example: Process the waste separation guide PDF
    pdf_filename = "waste_separation_guide.pdf"

    try:
        print(f"Processing {pdf_filename}...")
        result = process_pdf_to_csv(pdf_filename)
        print("\nProcessing completed successfully!")
        print(f"Document description: {result.description}")
        print(f"Number of sections: {len(result.sections)}")
        total_queries = sum(len(section.queries) for section in result.sections)
        print(f"Total queries: {total_queries}")
    except Exception as e:
        print(f"Error processing PDF: {e}")


if __name__ == "__main__":
    main()
