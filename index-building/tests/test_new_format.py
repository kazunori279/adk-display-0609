#!/usr/bin/env python3
"""
Quick test to verify the new description format works.
"""

from generate_chunks import process_pdf_to_csv


def main():
    """Test the new description format."""
    # Use a small PDF for quick testing
    pdf_file = "mailbox_passcode_change.pdf"
    csv_file = "test_new_format.csv"
    
    print("Testing new description format...")
    try:
        result = process_pdf_to_csv(pdf_file, csv_file)
        print(f"✓ Success! Description: {result.description}")
        print(f"  Sections: {len(result.sections)}")
        
        # Show CSV headers to confirm new format
        import csv
        from pathlib import Path
        csv_path = Path(__file__).parent / csv_file
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            print(f"  CSV headers: {reader.fieldnames}")
            
        # Clean up
        csv_path.unlink()
        
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    main()