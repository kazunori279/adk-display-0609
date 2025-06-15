#!/usr/bin/env python3
"""Quick test for updated find_document function with unique results."""

import sys
from pathlib import Path

# Add the backend directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.search_agent.chromadb_search import find_document


def test_find_document_unique():
    """Test that find_document returns 5 unique results without duplicates."""
    
    # Test with a query that might have duplicates
    query = "Wi-Fi setup"
    results = find_document(query)
    
    print(f"Query: {query}")
    print(f"Number of results: {len(results)}")
    print("\nResults:")
    
    seen_docs = set()
    for i, (filename, description, score) in enumerate(results, 1):
        print(f"{i}. {filename}: {description} (score: {score:.4f})")
        
        # Extract page number to check for duplicates
        import re
        page_match = re.search(r'\(page (\d+)\)', description)
        page_number = page_match.group(1) if page_match else 'unknown'
        
        doc_key = (filename, page_number)
        if doc_key in seen_docs:
            print(f"   ⚠️  DUPLICATE: {filename} page {page_number}")
        else:
            seen_docs.add(doc_key)
    
    print(f"\nUnique documents found: {len(seen_docs)}")
    print(f"Expected max results: 5")
    
    # Verify we have at most 5 results and no duplicates
    assert len(results) <= 5, f"Expected at most 5 results, got {len(results)}"
    assert len(seen_docs) == len(results), f"Found duplicates! Unique: {len(seen_docs)}, Total: {len(results)}"
    
    print("✅ Test passed: No duplicates found, results limited to 5")


if __name__ == "__main__":
    test_find_document_unique()