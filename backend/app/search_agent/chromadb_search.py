"""ChromaDB-based vector search functionality for document embeddings.

This module provides the same functionality as vector_search.py but uses ChromaDB for storage:
1. Load document embeddings from CSV file into ChromaDB
2. Generate text embeddings for queries
3. Find similar documents using ChromaDB's similarity search
"""

import ast
import csv
from pathlib import Path
from typing import List, Tuple
import uuid

import chromadb
from chromadb.config import Settings

from .generate_embeddings import generate_text_embeddings

# Path to the embeddings CSV file
CSV_FILE_PATH = Path(__file__).parent / "file_desc_emb.csv"

# ChromaDB client and collection
_CLIENT = None
_COLLECTION = None
COLLECTION_NAME = "document_embeddings"


def _get_chroma_client():
    """Get or create ChromaDB client."""
    global _CLIENT  # pylint: disable=global-statement
    if _CLIENT is None:
        _CLIENT = chromadb.Client(Settings(
            allow_reset=True,
            anonymized_telemetry=False
        ))
    return _CLIENT


def _get_collection():
    """Get or create ChromaDB collection."""
    global _COLLECTION  # pylint: disable=global-statement
    if _COLLECTION is None:
        client = _get_chroma_client()
        try:
            _COLLECTION = client.get_collection(COLLECTION_NAME)
        except Exception:  # pylint: disable=broad-except
            # Collection doesn't exist, create it
            _COLLECTION = client.create_collection(COLLECTION_NAME)
    return _COLLECTION


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
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error generating embedding: {exc}")
        return []


def load_document_embeddings(limit: int = None) -> List[Tuple[str, str, List[float]]]:
    """Load document embeddings from CSV file and store in ChromaDB.

    Args:
        limit: Maximum number of documents to load (None for all)

    Returns:
        List of tuples containing (filename, page_info, embedding_vector)
    """
    documents = []
    collection = _get_collection()

    # Check if collection already has data
    if collection.count() > 0:
        # Return existing data from ChromaDB
        collection_results = collection.get(include=['embeddings', 'metadatas'])
        for i, embedding in enumerate(collection_results['embeddings']):
            if limit and i >= limit:
                break
            metadata = collection_results['metadatas'][i]
            filename = metadata['filename']
            page_info = metadata['page_info']
            documents.append((filename, page_info, embedding))
        return documents

    # Load from CSV and populate ChromaDB
    embeddings_list = []
    metadatas = []
    ids = []

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

                # Store in ChromaDB
                embeddings_list.append(embedding)
                metadatas.append({
                    'filename': pdf_filename,
                    'page_info': pdf_description,
                    'page_number': page_number
                })
                ids.append(str(uuid.uuid4()))

                documents.append((pdf_filename, pdf_description, embedding))

        # Add to ChromaDB collection
        if embeddings_list:
            collection.add(
                embeddings=embeddings_list,
                metadatas=metadatas,
                ids=ids
            )

    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Error loading embeddings: {exc}")

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
    """Find top 3 documents most similar to the query using ChromaDB.

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

    # Ensure documents are loaded in ChromaDB
    load_document_embeddings(limit)

    collection = _get_collection()

    if collection.count() == 0:
        print("No documents loaded in ChromaDB")
        return []

    try:
        # Query ChromaDB for similar documents
        query_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=['metadatas', 'distances']
        )

        similarities = []
        if query_results['metadatas'] and query_results['distances']:
            metadatas = query_results['metadatas'][0]
            distances = query_results['distances'][0]
            for metadata, distance in zip(metadatas, distances):
                # ChromaDB returns distance, convert to similarity
                # For cosine distance: similarity = 1 - distance
                # Convert distance to similarity score
                similarity = (
                    1.0 / (1.0 + distance) if distance >= 0 else 1.0
                )

                filename = metadata['filename']
                page_info = metadata['page_info']
                similarities.append((filename, page_info, similarity))

        return similarities

    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error querying ChromaDB: {exc}")
        # Fallback to original method
        return _fallback_find_document(search_query, limit)


def _fallback_find_document(search_query: str, limit: int = None) -> List[Tuple[str, str, float]]:
    """Fallback method using original vector search approach."""
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


def reset_collection():
    """Reset the ChromaDB collection (useful for testing)."""
    global _COLLECTION  # pylint: disable=global-statement
    client = _get_chroma_client()
    if client:
        try:
            client.delete_collection(COLLECTION_NAME)
        except ValueError:
            pass  # Collection doesn't exist
    _COLLECTION = None


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
