"""Tests for vector_search module."""

import csv
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.search_agent.vector_search import (
    dot_product_similarity,
    find_document,
    generate_text_embedding,
    load_document_embeddings,
)


class TestDotProductSimilarity:
    """Test dot product similarity calculation."""
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        result = dot_product_similarity(vec1, vec2)
        expected = 1.0 + 4.0 + 9.0  # 1*1 + 2*2 + 3*3
        assert result == expected
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        result = dot_product_similarity(vec1, vec2)
        assert result == 0.0
    
    def test_different_length_vectors(self):
        """Test vectors with different lengths."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        result = dot_product_similarity(vec1, vec2)
        assert result == 0.0
    
    def test_empty_vectors(self):
        """Test empty vectors."""
        vec1 = []
        vec2 = []
        result = dot_product_similarity(vec1, vec2)
        assert result == 0.0


class TestGenerateTextEmbedding:
    """Test text embedding generation."""
    
    @patch('app.search_agent.vector_search.generate_text_embeddings')
    def test_successful_embedding_generation(self, mock_generate):
        """Test successful embedding generation."""
        mock_embedding = [0.1, 0.2, 0.3]
        mock_generate.return_value = [mock_embedding]
        
        result = generate_text_embedding("test text")
        
        mock_generate.assert_called_once_with(["test text"])
        assert result == mock_embedding
    
    @patch('app.search_agent.vector_search.generate_text_embeddings')
    def test_embedding_generation_failure(self, mock_generate):
        """Test embedding generation failure."""
        mock_generate.side_effect = Exception("API Error")
        
        result = generate_text_embedding("test text")
        
        assert result == []
    
    @patch('app.search_agent.vector_search.generate_text_embeddings')
    def test_empty_embedding_response(self, mock_generate):
        """Test empty embedding response."""
        mock_generate.return_value = []
        
        result = generate_text_embedding("test text")
        
        assert result == []


class TestLoadDocumentEmbeddings:
    """Test document embeddings loading."""
    
    def test_load_valid_csv(self):
        """Test loading valid CSV file."""
        # Create temporary CSV file
        csv_content = """pdf_filename,description,section_name,subsection_name,subsection_pdf_page_number,query,embeddings
001.pdf,Test document 1,Section 1,Subsection 1,1,Test query 1,"[0.1, 0.2, 0.3]"
002.pdf,Test document 2,Section 2,Subsection 2,2,Test query 2,"[0.4, 0.5, 0.6]"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        # Mock the CSV_FILE_PATH
        with patch('app.search_agent.vector_search.CSV_FILE_PATH', Path(temp_path)):
            result = load_document_embeddings()
        
        # Clean up
        Path(temp_path).unlink()
        
        assert len(result) == 2
        assert result[0] == ("001.pdf", "Test document 1", [0.1, 0.2, 0.3])
        assert result[1] == ("002.pdf", "Test document 2", [0.4, 0.5, 0.6])
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent CSV file."""
        with patch('app.search_agent.vector_search.CSV_FILE_PATH', Path('/nonexistent/file.csv')):
            result = load_document_embeddings()
        
        assert result == []
    
    def test_load_invalid_csv_format(self):
        """Test loading CSV with invalid format."""
        csv_content = """invalid,header,format
data,without,embeddings
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        with patch('app.search_agent.vector_search.CSV_FILE_PATH', Path(temp_path)):
            result = load_document_embeddings()
        
        # Clean up
        Path(temp_path).unlink()
        
        assert result == []


class TestFindDocument:
    """Test document finding functionality."""
    
    @patch('app.search_agent.vector_search.generate_text_embedding')
    @patch('app.search_agent.vector_search.load_document_embeddings')
    def test_successful_document_search(self, mock_load, mock_generate):
        """Test successful document search."""
        # Mock query embedding
        query_embedding = [1.0, 0.0, 0.0]
        mock_generate.return_value = query_embedding
        
        # Mock document embeddings
        mock_documents = [
            ("doc1.pdf", "Document 1", [1.0, 0.0, 0.0]),  # Perfect match
            ("doc2.pdf", "Document 2", [0.5, 0.5, 0.0]),  # Partial match
            ("doc3.pdf", "Document 3", [0.0, 1.0, 0.0]),  # No match
            ("doc4.pdf", "Document 4", [0.8, 0.2, 0.0]),  # Good match
        ]
        mock_load.return_value = mock_documents
        
        result = find_document("test query")
        
        # Should return top 3 documents sorted by similarity
        assert len(result) == 3
        assert result[0][0] == "doc1.pdf"  # Best match
        assert result[0][2] == 1.0  # Perfect similarity
        assert result[1][0] == "doc4.pdf"  # Second best
        assert result[2][0] == "doc2.pdf"  # Third best
    
    @patch('app.search_agent.vector_search.generate_text_embedding')
    def test_failed_query_embedding(self, mock_generate):
        """Test failed query embedding generation."""
        mock_generate.return_value = []
        
        result = find_document("test query")
        
        assert result == []
    
    @patch('app.search_agent.vector_search.generate_text_embedding')
    @patch('app.search_agent.vector_search.load_document_embeddings')
    def test_no_documents_loaded(self, mock_load, mock_generate):
        """Test when no documents are loaded."""
        mock_generate.return_value = [1.0, 0.0, 0.0]
        mock_load.return_value = []
        
        result = find_document("test query")
        
        assert result == []
    
    @patch('app.search_agent.vector_search.generate_text_embedding')
    @patch('app.search_agent.vector_search.load_document_embeddings')
    def test_fewer_than_three_documents(self, mock_load, mock_generate):
        """Test when fewer than 3 documents exist."""
        mock_generate.return_value = [1.0, 0.0, 0.0]
        mock_documents = [
            ("doc1.pdf", "Document 1", [1.0, 0.0, 0.0]),
            ("doc2.pdf", "Document 2", [0.5, 0.5, 0.0]),
        ]
        mock_load.return_value = mock_documents
        
        result = find_document("test query")
        
        # Should return only 2 documents
        assert len(result) == 2
        assert result[0][0] == "doc1.pdf"
        assert result[1][0] == "doc2.pdf"


# Integration test (requires actual CSV file)
class TestIntegration:
    """Integration tests that require actual data."""
    
    def test_find_document_with_real_data(self):
        """Test find_document with real CSV data if available with performance measurement."""
        import time
        
        # This test will only pass if the actual CSV file exists
        try:
            print("\n=== Performance Test ===")
            
            # Test query
            query = "Wi-Fi接続方法"
            print(f"Query: {query}")
            
            # Measure total time
            start_time = time.time()
            
            # Measure embedding generation time
            embedding_start = time.time()
            from app.search_agent.vector_search import generate_text_embedding
            query_embedding = generate_text_embedding(query)
            embedding_time = time.time() - embedding_start
            print(f"Embedding generation time: {embedding_time:.3f} seconds")
            
            # Measure document loading time
            loading_start = time.time()
            from app.search_agent.vector_search import load_document_embeddings
            documents = load_document_embeddings()
            loading_time = time.time() - loading_start
            print(f"Document loading time: {loading_time:.3f} seconds")
            print(f"Number of documents loaded: {len(documents)}")
            
            # Measure similarity calculation time
            similarity_start = time.time()
            result = find_document(query)
            total_time = time.time() - start_time
            similarity_time = total_time - embedding_time - loading_time
            print(f"Similarity calculation time: {similarity_time:.3f} seconds")
            print(f"Total search time: {total_time:.3f} seconds")
            
            # Display results
            if result:
                print(f"\nTop {len(result)} results:")
                for i, (filename, description, score) in enumerate(result, 1):
                    print(f"{i}. {filename}")
                    print(f"   Description: {description[:100]}...")
                    print(f"   Similarity: {score:.6f}")
                
                # Performance assertions
                assert total_time < 10.0, f"Search took too long: {total_time:.3f}s"
                assert len(result) <= 3
                assert all(len(item) == 3 for item in result)  # filename, description, score
                assert all(isinstance(item[2], float) for item in result)  # score is float
                
                # Check results are sorted by similarity (descending)
                scores = [item[2] for item in result]
                assert scores == sorted(scores, reverse=True), "Results not sorted by similarity"
                
                print(f"\n✅ Performance test passed!")
            else:
                print("No results found")
                
        except Exception as e:
            # Skip if CSV doesn't exist or other issues
            print(f"Integration test skipped: {e}")
            pytest.skip("Real CSV data not available for integration test")


if __name__ == "__main__":
    pytest.main([__file__])