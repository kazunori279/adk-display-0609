"""Utility functions for Gemini API operations."""
import os
from pathlib import Path
from typing import Union
from dotenv import load_dotenv
from google import genai


def create_gemini_client() -> genai.Client:
    """Create and return a configured Gemini client."""
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return genai.Client(api_key=api_key)


def upload_pdf(client: genai.Client, pdf_filename: str):
    """Upload a PDF file and return the uploaded file object."""
    pdf_path = Path(__file__).parent / "resources" / pdf_filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    print(f"Uploading file: {pdf_path}")
    return client.files.upload(
        file=pdf_path,
        config={"mime_type": "application/pdf"}
    )


def get_rag_prompt() -> str:
    """Return the standard RAG system prompt."""
    return ("I'm developing a RAG system using this document. "
            "This document is written for a specific item or service. "
            "Describe it in Japanese in UNDER 10 words and output as 'description'. "
            "Then, for EACH section of this document, generate 100 search queries in Japanese "
            "that would be issued from the users of this RAG system. That means if there are "
            "9 sections, I expect 900 queries total (100 queries per section).")


def get_test_rag_prompt() -> str:
    """Return a test RAG system prompt with fewer queries for faster testing."""
    return ("I'm developing a RAG system using this document. "
            "This document is written for a specific item or service. "
            "Describe it in Japanese in UNDER 10 words and output as 'description'. "
            "Then, for EACH section of this document, generate 10 search queries in Japanese "
            "that would be issued from the users of this RAG system.")


def generate_with_fallback(client: genai.Client, uploaded_file,
                          prompt: str, response_schema: Union[dict, type]):
    """Generate content with model fallback logic."""
    models_to_try = [
        "gemini-2.5-pro-preview-06-05",
        "gemini-2.0-flash-preview-0514",
        "gemini-1.5-flash"
    ]

    print("Sending to Gemini...")
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[uploaded_file, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                }
            )
            print(f"Successfully used model: {model_name}")
            return response
        except Exception as error:  # pylint: disable=broad-exception-caught
            print(f"Model {model_name} not available: {error}")
            if model_name == models_to_try[-1]:
                raise RuntimeError("All models failed") from error

    raise RuntimeError("All models failed")
