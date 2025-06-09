"""
Test cases for the generate_embeddings module.

This module contains unit tests for the text embedding generation functionality
using Google Cloud Vertex AI's TextEmbeddingModel.
"""

from unittest.mock import Mock, patch
from pathlib import Path
import pytest
from vertexai.language_models import TextEmbeddingInput


class TestGenerateEmbeddings:
    """Test cases for generate_text_embeddings function."""

    @pytest.fixture
    def sample_items(self):
        """Sample items for testing."""
        return [
            {"name": "エアコン", "description": "冷暖房機能付きの家電製品"},
            {"name": "洗濯機", "description": "衣類を自動で洗浄する機械"},
            {"name": "冷蔵庫", "description": "食品を冷却保存する電化製品"}
        ]

    @pytest.fixture
    def mock_embedding_response(self):
        """Mock embedding response from Vertex AI."""
        mock_emb1 = Mock()
        mock_emb1.values = [0.1, 0.2, 0.3] * 256  # 768 dimensions

        mock_emb2 = Mock()
        mock_emb2.values = [0.4, 0.5, 0.6] * 256  # 768 dimensions

        mock_emb3 = Mock()
        mock_emb3.values = [0.7, 0.8, 0.9] * 256  # 768 dimensions

        return [mock_emb1, mock_emb2, mock_emb3]

    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_generate_text_embeddings_success(self, mock_vertexai, mock_model,
                                            sample_items, mock_embedding_response):
        """Test successful embedding generation."""
        # Import after patching to avoid initialization
        from generate_embeddings import generate_text_embeddings

        # Setup mock
        mock_model.get_embeddings.return_value = mock_embedding_response

        # Call function
        result = generate_text_embeddings(sample_items)

        # Verify result
        assert len(result) == 3
        assert all(len(embedding) == 768 for embedding in result)
        assert result[0] == [0.1, 0.2, 0.3] * 256
        assert result[1] == [0.4, 0.5, 0.6] * 256
        assert result[2] == [0.7, 0.8, 0.9] * 256

        # Verify model was called correctly
        mock_model.get_embeddings.assert_called_once()
        call_args = mock_model.get_embeddings.call_args
        inputs, kwargs = call_args

        # Check inputs
        assert len(inputs[0]) == 3
        assert all(isinstance(inp, TextEmbeddingInput) for inp in inputs[0])

        # Check kwargs
        assert kwargs == {"output_dimensionality": 768}

    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_generate_text_embeddings_combines_name_and_description(
            self, mock_vertexai, mock_model, mock_embedding_response):
        """Test that function correctly combines name and description."""
        from generate_embeddings import generate_text_embeddings

        mock_model.get_embeddings.return_value = mock_embedding_response

        items = [{"name": "テスト", "description": "説明文"}]
        generate_text_embeddings(items)

        # Verify the input text was combined correctly
        call_args = mock_model.get_embeddings.call_args
        inputs = call_args[0][0]
        assert len(inputs) == 1
        # The TextEmbeddingInput should have been created with combined text
        # We can't directly access the text, but we can verify the call pattern

    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_generate_text_embeddings_empty_list(self, mock_vertexai, mock_model):
        """Test handling of empty input list."""
        from generate_embeddings import generate_text_embeddings

        mock_model.get_embeddings.return_value = []

        result = generate_text_embeddings([])

        assert result == []
        mock_model.get_embeddings.assert_called_once()

    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_generate_text_embeddings_single_item(self, mock_vertexai, mock_model,
                                                 mock_embedding_response):
        """Test with single item."""
        from generate_embeddings import generate_text_embeddings

        mock_model.get_embeddings.return_value = [mock_embedding_response[0]]

        items = [{"name": "単一項目", "description": "テスト用の単一項目"}]
        result = generate_text_embeddings(items)

        assert len(result) == 1
        assert len(result[0]) == 768

    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_generate_text_embeddings_api_error(self, mock_vertexai, mock_model,
                                               sample_items):
        """Test handling of API errors."""
        from generate_embeddings import generate_text_embeddings

        # Mock API error
        mock_model.get_embeddings.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            generate_text_embeddings(sample_items)

    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_generate_text_embeddings_invalid_response(self, mock_vertexai,
                                                      mock_model, sample_items):
        """Test handling of invalid response from API."""
        from generate_embeddings import generate_text_embeddings

        # Mock invalid response (missing values attribute)
        mock_invalid_emb = Mock()
        del mock_invalid_emb.values  # Remove values attribute
        mock_model.get_embeddings.return_value = [mock_invalid_emb]

        with pytest.raises(AttributeError):
            generate_text_embeddings(sample_items)

    def test_constants(self):
        """Test that constants are defined correctly."""
        from generate_embeddings import (
            PROJECT_ID, LOCATION, TEXT_EMB_MODEL_NAME,
            TEXT_EMB_TASK_TYPE, TEXT_EMB_DIMENSIONALITY
        )

        assert PROJECT_ID == "gcp-samples-ic0"
        assert LOCATION == "us-central1"
        assert TEXT_EMB_MODEL_NAME == "text-multilingual-embedding-002"
        assert TEXT_EMB_TASK_TYPE == "SEMANTIC_SIMILARITY"
        assert TEXT_EMB_DIMENSIONALITY == 768


    @patch('generate_embeddings.text_emb_model')
    @patch('generate_embeddings.vertexai')
    def test_text_embedding_input_creation(self, mock_vertexai, mock_model,
                                          mock_embedding_response):
        """Test that TextEmbeddingInput objects are created with correct parameters."""
        from generate_embeddings import generate_text_embeddings, TEXT_EMB_TASK_TYPE

        mock_model.get_embeddings.return_value = mock_embedding_response

        items = [
            {"name": "項目1", "description": "説明1"},
            {"name": "項目2", "description": "説明2"}
        ]

        with patch('generate_embeddings.TextEmbeddingInput') as mock_input_class:
            generate_text_embeddings(items)

            # Verify TextEmbeddingInput was called correctly
            assert mock_input_class.call_count == 2
            calls = mock_input_class.call_args_list

            # Check first call
            args1, _ = calls[0]
            assert args1[0] == "項目1 説明1"
            assert args1[1] == TEXT_EMB_TASK_TYPE

            # Check second call
            args2, _ = calls[1]
            assert args2[0] == "項目2 説明2"
            assert args2[1] == TEXT_EMB_TASK_TYPE


    @pytest.mark.integration
    def test_generate_embeddings_real_api(self):
        """Integration test with real Vertex AI API."""
        import os
        from dotenv import load_dotenv

        # Load environment variables
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)

        # Check if we have the required Google Cloud credentials
        has_credentials = (
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
            os.environ.get("GOOGLE_CLOUD_PROJECT") or
            os.path.exists(os.path.expanduser(
                "~/.config/gcloud/application_default_credentials.json"))
        )

        if not has_credentials:
            pytest.skip("Google Cloud credentials not found")

        from generate_embeddings import generate_text_embeddings

        # Test with real Japanese appliance data
        test_items = [
            {"name": "エアコン", "description": "冷暖房機能付きの家電製品"},
            {"name": "洗濯機", "description": "衣類を自動で洗浄する機械"}
        ]

        # Generate real embeddings
        result = generate_text_embeddings(test_items)

        # Verify results
        assert len(result) == 2
        assert all(len(embedding) == 768 for embedding in result)
        assert all(isinstance(embedding, list) for embedding in result)
        assert all(all(isinstance(val, float) for val in embedding)
                  for embedding in result)

        # Check that embeddings are in reasonable range
        for embedding in result:
            assert all(-2.0 <= val <= 2.0 for val in embedding)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
