import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

PROJECT_ID = "gcp-samples-ic0"
LOCATION = "us-central1"

TEXT_EMB_MODEL_NAME = "text-multilingual-embedding-002"
TEXT_EMB_TASK_TYPE = "SEMANTIC_SIMILARITY"
TEXT_EMB_DIMENSIONALITY = 768

vertexai.init(project=PROJECT_ID, location=LOCATION)
text_emb_model = TextEmbeddingModel.from_pretrained(TEXT_EMB_MODEL_NAME)

def generate_text_embeddings(items):
    """
    Generate text embeddings for items.
    """

    # Combine name and description for embedding input.
    names: list[str] = [item["name"] + " " + item["description"] for item in items]

    # Prepare inputs for the text embedding model.
    inputs: list[TextEmbeddingInput] = [
        TextEmbeddingInput(name, TEXT_EMB_TASK_TYPE) for name in names
    ]
    kwargs = {"output_dimensionality": TEXT_EMB_DIMENSIONALITY}

    # Get embeddings from the model.
    return [emb.values for emb in text_emb_model.get_embeddings(inputs, **kwargs)]
