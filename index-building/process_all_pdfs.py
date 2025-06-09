#!/usr/bin/env python3
"""
Script to process all PDF files in the resources directory and generate a CSV file.

This script uses 10 threads to process PDF files concurrently with Gemini,
appending results to a CSV file. Errors are logged to processing_errors.log.
"""

import os
import time
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from generate_chunks import process_pdf_to_csv


def process_single_pdf(pdf_filename, file_index, total_files):
    """
    Process a single PDF file.
    
    Args:
        pdf_filename: Name of PDF file to process
        file_index: Current file number for progress tracking
        total_files: Total number of files to process
        
    Returns:
        tuple: (success: bool, pdf_filename: str, result_or_error: any)
    """
    try:
        print(f"\n[{file_index}/{total_files}] Processing: {pdf_filename}")
        result = process_pdf_to_csv(pdf_filename)
        sections = len(result.sections)
        total_queries = sum(len(section.queries) for section in result.sections)
        print(f"✓ Successfully processed {pdf_filename}")
        print(f"  Sections: {sections}, Queries: {total_queries}")
        return (True, pdf_filename, result)
        
    except Exception as e:
        error_msg = f"{pdf_filename}: {str(e)}"
        error_details = f"\n{pdf_filename} - Detailed Error:\n{traceback.format_exc()}\n"
        print(f"✗ Error processing {pdf_filename}: {e}")
        return (False, pdf_filename, (error_msg, error_details))


def main():
    """Process all PDFs in the resources directory using multithreading."""
    resources_dir = Path(__file__).parent / "resources"

    # Get all PDF files
    pdf_files = sorted([f for f in os.listdir(resources_dir) if f.endswith(".pdf")])

    print(f"Found {len(pdf_files)} PDF files to process")
    print("Using 10 threads for concurrent processing")
    print("=" * 50)

    # Error tracking
    errors = []
    success_count = 0
    
    # Create a lock for thread-safe printing and error collection
    print_lock = threading.Lock()
    error_lock = threading.Lock()

    # Process PDFs using ThreadPoolExecutor with 10 threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_pdf = {
            executor.submit(process_single_pdf, pdf_filename, i+1, len(pdf_files)): pdf_filename
            for i, pdf_filename in enumerate(pdf_files)
        }
        
        # Process completed tasks
        for future in as_completed(future_to_pdf):
            pdf_filename = future_to_pdf[future]
            try:
                success, filename, result = future.result()
                
                if success:
                    success_count += 1
                else:
                    with error_lock:
                        errors.extend(result)  # result is (error_msg, error_details)
                    
            except Exception as e:
                with error_lock:
                    error_msg = f"{pdf_filename}: {str(e)}"
                    error_details = f"\n{pdf_filename} - Future Error:\n{traceback.format_exc()}\n"
                    errors.extend([error_msg, error_details])

    # Write error log if there were any errors
    if errors:
        error_log_path = Path(__file__).parent / "processing_errors.log"
        with open(error_log_path, "w", encoding="utf-8") as f:
            f.write(f"PDF Processing Errors Report (Multithreaded)\n")
            f.write(f"Total files processed: {len(pdf_files)}\n")
            f.write(f"Successful: {success_count}\n")
            f.write(f"Failed: {len(errors)//2}\n")  # Divide by 2 since we store both summary and details
            f.write("=" * 50 + "\n\n")
            for error in errors:
                f.write(f"{error}\n")
        print(f"\n❌ {len(errors)//2} files had errors - see processing_errors.log")

    print("\n" + "=" * 50)
    print("Processing complete!")
    print(f"✓ Successfully processed: {success_count}/{len(pdf_files)} files")
    if errors:
        print(f"✗ Failed: {len(errors)//2} files (logged to processing_errors.log)")
    else:
        print("✓ All files processed successfully!")
    print("Results saved to: file_description.csv")


if __name__ == "__main__":
    main()
