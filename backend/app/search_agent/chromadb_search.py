"""ChromaDB-based vector search functionality for document embeddings.

This module provides the same functionality as vector_search.py but uses ChromaDB for storage:
1. Load document embeddings from CSV file into ChromaDB
2. Generate text embeddings for queries
3. Find similar documents using ChromaDB's similarity search
"""

import ast
import csv
import re
import time
from pathlib import Path
from typing import List, Tuple
import uuid
import asyncio

import chromadb
from chromadb.config import Settings

from .generate_embeddings import generate_text_embeddings

# Path to the embeddings CSV file
CSV_FILE_PATH = Path(__file__).parent / "file_desc_emb.csv"

# ChromaDB client and collection
_CLIENT = None
_COLLECTION = None
COLLECTION_NAME = "document_embeddings"

# Global queue for client messages
client_message_queue = asyncio.Queue()


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

        # Add to ChromaDB collection in batches to avoid batch size limits
        if embeddings_list:
            batch_size = 5000  # ChromaDB max batch size is around 5461
            for i in range(0, len(embeddings_list), batch_size):
                batch_embeddings = embeddings_list[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]

                collection.add(
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas,
                    ids=batch_ids
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
    """Find top 5 unique documents most similar to the query using ChromaDB.

    Args:
        search_query: Search query text
        limit: Maximum number of documents to search through (None for all)

    Returns:
        List of tuples containing (filename, description, similarity_score)
        sorted by similarity score in descending order (top 5 unique results)
        Results are filtered by relevancy threshold of 0.920 to remove low-quality matches.
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
        # Query ChromaDB for more results to account for duplicates
        # Request 20 results to filter down to 5 unique ones
        query_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=20,
            include=['metadatas', 'distances']
        )

        similarities = []
        seen_documents = set()  # Track (filename, page_number) combinations

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
                page_number = metadata.get('page_number', '')
                page_info = metadata['page_info']

                # Create unique key for deduplication
                doc_key = (filename, page_number)

                # Apply relevancy threshold (0.920) to filter out low-quality matches
                relevancy_threshold = 0.920

                # Only add if we haven't seen this filename+page combination and meets threshold
                if doc_key not in seen_documents and similarity >= relevancy_threshold:
                    seen_documents.add(doc_key)
                    similarities.append((filename, page_info, similarity))

                    # Stop when we have 5 unique results
                    if len(similarities) >= 5:
                        break

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

    # Sort by similarity score (descending)
    similarities.sort(key=lambda x: x[2], reverse=True)

    # Remove duplicates based on filename and page number
    seen_documents = set()
    unique_similarities = []

    for filename, description, similarity in similarities:
        # Extract page number from description (format: "filename (page number)")
        page_match = re.search(r'\(page (\d+)\)', description)
        page_number = page_match.group(1) if page_match else ''

        # Create unique key for deduplication
        doc_key = (filename, page_number)

        # Apply relevancy threshold (0.920) to filter out low-quality matches
        relevancy_threshold = 0.920

        # Only add if we haven't seen this filename+page combination and meets threshold
        if doc_key not in seen_documents and similarity >= relevancy_threshold:
            seen_documents.add(doc_key)
            unique_similarities.append((filename, description, similarity))

            # Stop when we have 5 unique results
            if len(unique_similarities) >= 5:
                break

    return unique_similarities


def reset_collection():
    """Reset the ChromaDB collection (useful for testing)."""
    global _COLLECTION  # pylint: disable=global-statement
    client = _get_chroma_client()
    if client:
        try:
            client.delete_collection(COLLECTION_NAME)
        except (ValueError, Exception):
            pass  # Collection doesn't exist or other error
    _COLLECTION = None


def find_document_tool(query: str) -> str:
    """Search comprehensive apartment manual documents for relevant information.

    This function searches through apartment manual documents using vector similarity
    to find the most relevant information for the given query.

    DOCUMENT COVERAGE:
    - HOME APPLIANCES: Air conditioners, humidifiers, dehumidifiers, vacuum cleaners,
      washing machines, dryers, rice cookers, refrigerators, water heaters, ventilation
    - KITCHEN EQUIPMENT: Coffee machines, espresso makers, dishwashers, microwave ovens,
      steam ovens, induction cooktops, range hoods, garbage disposals
    - AUDIO/VIDEO EQUIPMENT: Bluetooth transmitters, audio amplifiers, Blu-ray recorders,
      DVD players, TV systems, sound systems, speakers
    - COMPUTER/NETWORK: NAS systems, wireless keyboards, mini PCs, tablets, routers,
      network equipment, Wi-Fi setup, internet connectivity
    - SAFETY/SECURITY: Fire evacuation devices, escape ladders, emergency equipment,
      rescue tools, smoke detectors, security systems
    - BUILDING INFRASTRUCTURE: Gas equipment (stoves, heaters), electrical systems,
      plumbing, HVAC controls, elevator systems, intercom systems
    - BUILDING SERVICES & RULES: Move-in procedures, parking regulations, waste
      separation guidelines, noise policies, pet policies, common area usage
    - TRANSPORTATION & AMENITIES: Shuttle bus schedules and routes, rental bicycle
      systems, unmanned convenience store operations, package delivery systems

    Args:
        query: Search query text to find relevant documents

    Returns:
        Formatted string containing the top 5 most relevant unique documents with
        their filenames, descriptions, and relevance scores
    """
    try:
        search_results = find_document(query)

        if not search_results:
            return "No relevant apartment manual documents found for your query."

        formatted_results = ["Found relevant apartment manual documents:"]
        for i, (filename, description, score) in enumerate(search_results, 1):
            formatted_results.append(
                f"{i}. {filename}: {description} (relevance: {score:.3f})"
            )

        return "\n".join(formatted_results)

    except Exception as exc:  # pylint: disable=broad-except
        return f"Error searching documents: {exc}"


def show_document_tool(pdf_files: List[str]) -> dict:
    """Display PDF documents to the user.

    Use this tool to show specific apartment manual PDF documents to the user.
    This will open the documents in the user's interface for viewing.

    Args:
        pdf_files: List of PDF filenames with optional page numbers using format
                  "filename:page_number" (e.g., ["001.pdf:5", "023.pdf:12", "007.pdf"])
                  If no page number is specified, the document opens at the first page.

    Returns:
        Dictionary with the result of the document display action
    """
    try:
        if not pdf_files:
            return {
                "status": "error",
                "message": "No PDF files specified to show."
            }

        # Build the document list from filename:page_number format
        documents = []
        processed_files = []

        for pdf_file in pdf_files:
            # Parse filename:page_number format
            if ':' in pdf_file:
                filename, page_str = pdf_file.split(':', 1)
                try:
                    page_number = int(page_str)
                    documents.append({"filename": filename, "page_number": page_number})
                    processed_files.append(f"{filename} (page {page_number})")
                except ValueError:
                    # Invalid page number, treat as filename only
                    documents.append({"filename": pdf_file})
                    processed_files.append(pdf_file)
            else:
                # No page number specified
                documents.append({"filename": pdf_file})
                processed_files.append(pdf_file)

        if not documents:
            return {
                "status": "error",
                "message": "No valid PDF files found in the input."
            }

        # Create the JSON command for the client
        command_data = {
            "command": "show_document",
            "params": documents
        }

        # Format as the required message structure
        client_message = {
            "mime_type": "application/json",
            "data": command_data
        }

        # Put the message in the queue for the main server to send to client
        try:
            client_message_queue.put_nowait(client_message)
        except asyncio.QueueFull:
            return {
                "status": "error",
                "message": "Unable to queue document display command - queue is full."
            }

        # Return success status with details
        return {
            "status": "success",
            "action": "document_display_queued",
            "documents": processed_files,
            "count": len(documents),
            "message": f"Displaying {len(documents)} documents to the user"
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to display documents: {exc}"
        }


def initialize_chromadb_on_startup():
    """Initialize ChromaDB with all documents and run a test query on server startup."""

    print("🚀 Initializing ChromaDB with all 34k+ apartment manual documents...")
    start_time = time.time()

    # Reset collection to start fresh
    reset_collection()

    # Load all documents (no limit)
    print("📥 Loading all documents from CSV...")
    load_start = time.time()
    documents = load_document_embeddings(limit=None)
    load_time = time.time() - load_start

    print(f"✅ Loaded {len(documents)} documents in {load_time:.2f} seconds")

    # Run test query to verify everything works
    print("🔍 Running test query to verify ChromaDB search...")
    test_start = time.time()
    test_result = find_document_tool("Wi-Fi setup")
    test_time = time.time() - test_start

    total_time = time.time() - start_time

    print(f"✅ Test query completed in {test_time:.2f} seconds")
    print(f"🎯 ChromaDB initialization complete in {total_time:.2f} seconds")
    print(f"📊 Ready to search {len(documents)} apartment manual documents")

    # Show test result preview
    if "Found relevant apartment manual documents:" in test_result:
        lines = test_result.split('\n')
        print("🔍 Test query result preview:")
        for line in lines[:4]:  # Show first 4 lines
            print(f"   {line}")
    else:
        print(f"⚠️  Test query result: {test_result[:100]}...")


# ADK Function Tools are defined above:
# - find_document_tool: Search apartment manual documents
# - show_document_tool: Display PDF documents to the user


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
