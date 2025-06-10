"""Performance test for vector search with real data."""

import time
from app.search_agent.vector_search import find_document, generate_text_embedding, load_document_embeddings


def test_performance():
    """Test vector search performance with detailed measurements."""
    print("=== Vector Search Performance Test ===")
    
    query = "Wi-Fi接続方法"
    print(f"Query: {query}")
    
    try:
        # Test 1: Embedding generation
        print("\n1. Testing embedding generation...")
        start = time.time()
        query_embedding = generate_text_embedding(query)
        embedding_time = time.time() - start
        print(f"   ✓ Generated {len(query_embedding)} dimensions in {embedding_time:.3f}s")
        if len(query_embedding) == 128:
            print("   ✓ Using new 128-dimensional embeddings")
        elif len(query_embedding) == 768:
            print("   ⚠️  Still using old 768-dimensional embeddings")
        else:
            print(f"   ? Unknown embedding dimension: {len(query_embedding)}")
        
        # Test 2: Document loading (limited)
        print("\n2. Testing document loading (first 100 docs)...")
        start = time.time()
        documents = load_document_embeddings(limit=100)
        loading_time = time.time() - start
        print(f"   ✓ Loaded {len(documents)} documents in {loading_time:.3f}s")
        
        # Test 3: Full search with limited dataset
        print("\n3. Testing full search (100 docs)...")
        start = time.time()
        results = find_document(query, limit=100)
        search_time = time.time() - start
        print(f"   ✓ Found {len(results)} results in {search_time:.3f}s")
        
        # Test 4: Larger dataset test
        print("\n4. Testing with larger dataset (1000 docs)...")
        start = time.time()
        results_large = find_document(query, limit=1000)
        large_search_time = time.time() - start
        print(f"   ✓ Found {len(results_large)} results in {large_search_time:.3f}s")
        
        # Display results
        print(f"\n=== Results (100 docs) ===")
        for i, (filename, description, score) in enumerate(results, 1):
            print(f"{i}. {filename} (score: {score:.6f})")
            print(f"   {description[:80]}...")
            
        print(f"\n=== Results (1000 docs) ===")
        for i, (filename, description, score) in enumerate(results_large, 1):
            print(f"{i}. {filename} (score: {score:.6f})")
            print(f"   {description[:80]}...")
        
        # Performance summary
        print(f"\n=== Performance Summary ===")
        print(f"Embedding generation:   {embedding_time:.3f}s")
        print(f"Document loading (100): {loading_time:.3f}s") 
        print(f"Search (100 docs):      {search_time:.3f}s")
        print(f"Search (1000 docs):     {large_search_time:.3f}s")
        print(f"Documents processed:    100 / 1000")
        
        # Performance checks
        if large_search_time > 10.0:
            print(f"⚠️  Large search is slow ({large_search_time:.3f}s > 10s)")
        else:
            print(f"✅ Performance acceptable for 1000 docs ({large_search_time:.3f}s)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_performance()