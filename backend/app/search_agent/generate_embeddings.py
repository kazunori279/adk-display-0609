"""Text embeddings generation using Vertex AI."""
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

PROJECT_ID = "gcp-samples-ic0"
LOCATION = "us-central1"

TEXT_EMB_MODEL_NAME = "text-multilingual-embedding-002"
TEXT_EMB_TASK_TYPE = "SEMANTIC_SIMILARITY"
TEXT_EMB_DIMENSIONALITY = 128

vertexai.init(project=PROJECT_ID, location=LOCATION)
text_emb_model = TextEmbeddingModel.from_pretrained(TEXT_EMB_MODEL_NAME)

def generate_text_embeddings(texts):
    """
    Generate text embeddings for texts.
    
    Args:
        texts: List of strings (max 20 items)
    """
    if len(texts) > 20:
        raise ValueError(f"Maximum 20 texts allowed, got {len(texts)}")

    # Prepare inputs for the text embedding model.
    inputs: list[TextEmbeddingInput] = [
        TextEmbeddingInput(text, TEXT_EMB_TASK_TYPE) for text in texts
    ]
    kwargs = {"output_dimensionality": TEXT_EMB_DIMENSIONALITY}

    # Get embeddings from the model.
    return [emb.values for emb in text_emb_model.get_embeddings(inputs, **kwargs)]
