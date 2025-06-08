#!/usr/bin/env python3
"""
Demo script to process a PDF and display the resulting CSV content.
"""

import csv
from pathlib import Path
from generate_chunks import process_pdf_to_csv
from csv_utils import print_query_summary


def main():
    """Process a PDF and display the CSV content."""
    # Use a small PDF for demo
    pdf_file = "mailbox_passcode_change.pdf"
    csv_file = "demo_output.csv"
    
    print(f"Processing {pdf_file} with Gemini API...")
    print("=" * 80)
    
    # Process the PDF
    result = process_pdf_to_csv(pdf_file, csv_file)
    
    print("\n" + "=" * 80)
    print("CSV FILE CONTENT")
    print("=" * 80)
    
    # Read and display the CSV file
    csv_path = Path(__file__).parent / csv_file
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    
    # Also show some statistics
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Total rows: {len(rows)}")
    print_query_summary(result)


if __name__ == "__main__":
    main()