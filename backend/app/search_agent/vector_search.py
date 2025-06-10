"""Vector search functionality for document embeddings.

This module provides functionality to:
1. Load document embeddings from CSV file
2. Generate text embeddings for queries
3. Find similar documents using dot product similarity
"""

import ast
import csv
from pathlib import Path
from typing import List, Tuple

from .generate_embeddings import generate_text_embeddings

# Path to the embeddings CSV file
CSV_FILE_PATH = Path(__file__).parent / "file_desc_emb.csv"


def generate_text_embedding(text: str) -> List[float]:
    """Generate text embedding using existing generate_embeddings module.

    Args:
        text: Input text to generate embedding for

    Returns:
        List of float values representing the text embedding
    """
    try:
        # Use the existing generate_text_embeddings function (takes a list)
        embeddings = generate_text_embeddings([text])
        return embeddings[0] if embeddings else []
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []


def load_document_embeddings(limit: int = None) -> List[Tuple[str, str, List[float]]]:
    """Load document embeddings from CSV file.

    Args:
        limit: Maximum number of documents to load (None for all)

    Returns:
        List of tuples containing (filename, page_info, embedding_vector)
    """
    documents = []

    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row_index, row in enumerate(reader):
                if limit and row_index >= limit:
                    break

                pdf_filename = row['pdf_filename']
                page_number = row['subsection_pdf_page_number']
                # Create a description from filename and page
                pdf_description = f"{pdf_filename} (page {page_number})"
                # Parse the embedding string as a Python list
                embedding_str = row['embeddings']
                embedding = ast.literal_eval(embedding_str)

                documents.append((pdf_filename, pdf_description, embedding))

    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"Error loading embeddings: {e}")

    return documents


def dot_product_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate dot product similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Dot product similarity score
    """
    if len(vec1) != len(vec2):
        return 0.0

    return sum(a * b for a, b in zip(vec1, vec2))


def find_document(search_query: str, limit: int = None) -> List[Tuple[str, str, float]]:
    """Find top 3 documents most similar to the query.

    Args:
        search_query: Search query text
        limit: Maximum number of documents to search through (None for all)

    Returns:
        List of tuples containing (filename, description, similarity_score)
        sorted by similarity score in descending order (top 3)
    """
    # Generate embedding for the query
    query_embedding = generate_text_embedding(search_query)

    if not query_embedding:
        print("Failed to generate query embedding")
        return []

    # Load document embeddings (with optional limit)
    documents = load_document_embeddings(limit)

    if not documents:
        print("No documents loaded")
        return []

    # Calculate similarities
    similarities = []
    for doc_filename, doc_description, doc_embedding in documents:
        similarity = dot_product_similarity(query_embedding, doc_embedding)
        similarities.append((doc_filename, doc_description, similarity))

    # Sort by similarity score (descending) and return top 3
    similarities.sort(key=lambda x: x[2], reverse=True)

    return similarities[:3]


# Example usage
if __name__ == "__main__":
    # Test the function
    EXAMPLE_QUERY = "Wi-Fi接続方法"
    results = find_document(EXAMPLE_QUERY)

    print(f"Query: {EXAMPLE_QUERY}")
    print("Top 3 similar documents:")
    for result_index, (result_filename, result_description, result_score) in enumerate(results, 1):
        print(f"{result_index}. {result_filename} - {result_description[:50]}... "
              f"(score: {result_score:.4f})")
