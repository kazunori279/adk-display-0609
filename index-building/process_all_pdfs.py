#!/usr/bin/env python3
"""
Script to process all PDF files in the resources directory and generate a CSV file.

This script iterates through all PDF files in the resources directory
and processes each one with Gemini, appending results to a CSV file.
"""

import os
import time
from pathlib import Path
from generate_chunks import process_pdf_to_csv


def main():
    """Process all PDFs in the resources directory."""
    resources_dir = Path(__file__).parent / "resources"

    # Get all PDF files
    pdf_files = sorted([f for f in os.listdir(resources_dir) if f.endswith(".pdf")])

    print(f"Found {len(pdf_files)} PDF files to process")
    print("=" * 50)

    # Process each PDF
    for i, pdf_filename in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_filename}")

        try:
            process_pdf_to_csv(pdf_filename)
            print(f"✓ Successfully processed {pdf_filename}")

            # Add a small delay to avoid rate limiting
            if i < len(pdf_files):
                print("Waiting 2 seconds before next file...")
                time.sleep(2)

        except (ValueError, FileNotFoundError, RuntimeError) as e:
            print(f"✗ Error processing {pdf_filename}: {e}")
            continue

    print("\n" + "=" * 50)
    print("Processing complete!")
    print("Results saved to: file_description.csv")


if __name__ == "__main__":
    main()
