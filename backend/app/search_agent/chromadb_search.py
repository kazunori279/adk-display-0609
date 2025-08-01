"""ChromaDB-based vector search functionality for document embeddings.

This module provides the same functionality as vector_search.py but uses ChromaDB for storage:
1. Load document embeddings from CSV file into ChromaDB
2. Generate text embeddings for queries
3. Find similar documents using ChromaDB's similarity search
"""

import ast
import csv
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

# Relevancy threshold for filtering search results
RELEVANCY_THRESHOLD = 0.920


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
    """Find top 3 documents most similar to the query using ChromaDB.

    Args:
        search_query: Search query text
        limit: Maximum number of documents to search through (None for all)

    Returns:
        List of tuples containing (filename, description, similarity_score)
        sorted by document frequency (count) and similarity score (top 3 results)
        Results are filtered by relevancy threshold of 0.920 to remove low-quality matches.
        Documents are ranked by: 1) count of pages per document, 2) highest similarity score.
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

    # Query ChromaDB for top 10 results to analyze document frequency
    query_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        include=['metadatas', 'distances']
    )

    document_scores = {}  # filename -> {'count': int, 'max_similarity': float, 'page_info': str}

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

            # Apply relevancy threshold to filter out low-quality matches
            if similarity >= RELEVANCY_THRESHOLD:
                filename = metadata['filename']
                page_info = metadata['page_info']

                if filename not in document_scores:
                    document_scores[filename] = {
                        'count': 0,
                        'max_similarity': 0.0,
                        'page_info': page_info
                    }
                document_scores[filename]['count'] += 1
                if similarity > document_scores[filename]['max_similarity']:
                    document_scores[filename]['max_similarity'] = similarity
                    document_scores[filename]['page_info'] = page_info

    # Sort documents by: 1) count (descending), 2) max_similarity (descending)
    sorted_documents = sorted(
        document_scores.items(),
        key=lambda x: (x[1]['count'], x[1]['max_similarity']),
        reverse=True
    )

    # Return top 3 documents
    similarities = []
    for filename, doc_data in sorted_documents[:3]:
        similarities.append((filename, doc_data['page_info'], doc_data['max_similarity']))

    return similarities




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


def find_document_tool(query: str) -> dict:
    """Search comprehensive product and service manual documents for relevant information.

    This function searches through product and service manual documents using vector similarity
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
        Dictionary with result status and message containing search results with \
filenames only (no page numbers)
    """
    try:
        search_results = find_document(query)

        if not search_results:
            return {
                "result": "success",
                "message": "No documents found for your query."
            }

        # Format results with filename only (no page numbers) for the agent
        formatted_results = ["Found relevant product and service manual documents:"]
        for i, (filename, _, score) in enumerate(search_results, 1):
            formatted_results.append(f"{i}. {filename} (relevance: {score:.3f})")

        return {
            "result": "success",
            "message": "\n".join(formatted_results)
        }

    except Exception as exc:  # pylint: disable=broad-except
        return {
            "result": "error",
            "message": f"Error searching documents: {exc}"
        }


def show_document_tool(pdf_file: str) -> dict:
    """Display PDF document to the user.

    Use this tool to show a specific product and service manual PDF document to the user.
    This will open the document in the user's interface for viewing.

    Args:
        pdf_file: PDF filename with optional page number using format
                 "filename:page_number" (e.g., "001.pdf:5", "023.pdf:12", "007.pdf")
                 If no page number is specified, document opens at page 1.

    Returns:
        Dictionary with the result of the document display action
    """
    try:
        if not pdf_file:
            return {
                "status": "error",
                "message": "No PDF file specified to show."
            }

        # Parse filename:page_number format
        if ':' in pdf_file:
            filename, page_str = pdf_file.split(':', 1)
            try:
                page_number = int(page_str)
                document = {"filename": filename, "page_number": page_number}
                processed_file = f"{filename} (page {page_number})"
            except ValueError:
                # Invalid page number, default to page 1
                document = {"filename": filename, "page_number": 1}
                processed_file = f"{filename} (page 1)"
        else:
            # No page number specified, default to page 1
            document = {"filename": pdf_file, "page_number": 1}
            processed_file = f"{pdf_file} (page 1)"

        # Create the JSON command for the client
        command_data = {
            "command": "show_document",
            "params": [document]
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
            "documents": [processed_file],
            "count": 1,
            "message": f"Displaying {processed_file} to the user"
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to display documents: {exc}"
        }


def initialize_chromadb_on_startup():
    """Initialize ChromaDB with all documents and run a test query on server startup."""

    print("🚀 Initializing ChromaDB with all 34k+ product and service manual documents...")
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
    print(f"📊 Ready to search {len(documents)} product and service manual documents")

    # Show test result preview
    if isinstance(test_result, dict) and test_result.get("result") == "success":
        message = test_result.get("message", "")
        if "Found relevant product and service manual documents:" in message:
            lines = message.split('\n')
            print("🔍 Test query result preview:")
            for line in lines[:4]:  # Show first 4 lines
                print(f"   {line}")
        else:
            print(f"⚠️  Test query message: {message[:100]}...")
    else:
        print(f"⚠️  Test query result: {str(test_result)[:100]}...")


# ADK Function Tools are defined above:
# - find_document_tool: Search product and service manual documents
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
