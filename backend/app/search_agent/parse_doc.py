"""Document parsing functionality using Gemini Flash model.

This module provides functionality to parse PDF documents and answer queries
based on their content using Google's Gemini Flash model.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger(__name__)


class DocumentAnalysis(BaseModel):
    """Structured output model for document analysis results."""
    answer: str
    page_number: Optional[int] = None


def _create_gemini_client() -> genai.Client:
    """Create and return a configured Gemini client."""
    # Load .env file from backend directory
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)

    # Check if we should use Vertex AI or direct API
    use_vertexai = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'FALSE').upper() == 'TRUE'

    if use_vertexai:
        # Set up service account credentials for Vertex AI
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            # Convert relative path to absolute path from current working directory
            if not os.path.isabs(credentials_path):
                current_dir = Path.cwd()
                credentials_path = str(current_dir / credentials_path)
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required for Vertex AI")

        logger.info("Using Vertex AI client (Project: %s, Location: %s)", project_id, location)
        logger.info("Credentials: %s", credentials_path)
        return genai.Client(vertexai=True)

    # Use direct API client
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    logger.info("Using direct API client")
    return genai.Client(api_key=api_key)


def _get_gcs_uri(pdf_filename: str) -> str:
    """Get the GCS URI for a PDF file."""
    base_uri = "gs://gcp-samples-ic0-homeai/resources/"
    return f"{base_uri}{pdf_filename}"



def parse_doc_tool(query: str, pdf_filename: str) -> Dict[str, str]:
    """Parse a PDF document and answer a query based on its content.

    This tool uses Google's Gemini Flash model to read a PDF document and
    provide answers to user queries based on the content of that document.

    Args:
        query: The user's question or query about the document
        pdf_filename: PDF filename to analyze (e.g., "001.pdf")

    Returns:
        Dictionary with status, answer/message, and pdf_file based on the PDF content
    """
    if not pdf_filename:
        return {
            "status": "error",
            "message": "No PDF file provided to analyze."
        }

    if not query.strip():
        return {
            "status": "error",
            "message": "No query provided."
        }

    try:
        # Create Gemini client
        client = _create_gemini_client()

        # Get GCS URI for the PDF file
        gcs_uri = _get_gcs_uri(pdf_filename)
        print(f"📄 [PARSE_DOC] Using GCS URI: {gcs_uri}")
        logger.info("📄 [PARSE_DOC] Using GCS URI: %s", gcs_uri)

        # Create a Part object from the GCS URI
        pdf_file_part = types.Part.from_uri(
            file_uri=gcs_uri,
            mime_type="application/pdf"
        )

        # Prepare the prompt
        prompt = f"""You are analyzing a product and service manual PDF document to \
answer user questions.

User Query: {query}

Please analyze the provided PDF document and provide a comprehensive answer to the user's query based on the content you find. If the information is not available in the document, please state that clearly.

Focus on:
1. Direct answers to the user's question
2. Relevant details from the document
3. Step-by-step instructions if applicable
4. Any important warnings or notes
5. IMPORTANT: Identify the page number where you found the most relevant description for the user's query

You must respond in JSON format with these exact fields:
- "answer": A comprehensive response to the user's question (string)
- "page_number": The page number where the most relevant information was found (integer, or null if no specific page)

Example response format:
{{
  "answer": "Your detailed answer here...",
  "page_number": 9
}}"""

        # Prepare content list with PDF part and prompt
        content = [pdf_file_part, prompt]

        # Use model fallback similar to gemini_utils
        models_to_try = [
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.0-flash",
        ]

        for model_name in models_to_try:
            try:
                model_start = time.time()
                print(f"🤖 [PARSE_DOC] Calling Gemini {model_name}...")
                logger.info("🤖 [PARSE_DOC] Calling Gemini %s...", model_name)
                response = client.models.generate_content(
                    model=model_name,
                    contents=content,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": DocumentAnalysis,
                    }
                )
                model_time = time.time() - model_start

                if response.text:
                    print(f"✅ [PARSE_DOC] Gemini response received in {model_time:.2f}s")
                    logger.info("✅ [PARSE_DOC] Gemini response received in %.2fs", model_time)
                    # Use the parsed structured output directly
                    try:
                        # Access the parsed response object directly
                        parsed_response: DocumentAnalysis = response.parsed

                        print(f"📄 [PARSE_DOC] Raw JSON response: {response.text}")
                        print(f"📄 [PARSE_DOC] Answer: {parsed_response.answer}")
                        print(f"📍 [PARSE_DOC] Page number: {parsed_response.page_number}")
                        logger.info("📄 [PARSE_DOC] Raw JSON response: %s", response.text)
                        logger.info("📄 [PARSE_DOC] Answer: %s", parsed_response.answer)
                        logger.info("📍 [PARSE_DOC] Page number: %s", parsed_response.page_number)

                        # Format pdf_file with page number if available
                        if parsed_response.page_number:
                            pdf_file_formatted = f"{pdf_filename}:{parsed_response.page_number}"
                        else:
                            pdf_file_formatted = pdf_filename

                        return {
                            "status": "success",
                            "answer": parsed_response.answer,
                            "pdf_file": pdf_file_formatted
                        }
                    except Exception as parse_exc:
                        print(f"⚠️ [PARSE_DOC] Failed to access parsed response: {parse_exc}")
                        logger.warning("⚠️ [PARSE_DOC] Failed to access parsed response: %s",
                                     parse_exc)
                        print(f"📄 [PARSE_DOC] Raw response text: {response.text}")
                        logger.info("📄 [PARSE_DOC] Raw response text: %s", response.text)

                        # Fallback: try manual JSON parsing
                        try:
                            parsed_response = DocumentAnalysis.model_validate_json(response.text)
                            print("📄 [PARSE_DOC] Fallback parsing successful")
                            logger.info("📄 [PARSE_DOC] Fallback parsing successful")

                            # Format pdf_file with page number if available
                            if parsed_response.page_number:
                                pdf_file_formatted = f"{pdf_filename}:{parsed_response.page_number}"
                            else:
                                pdf_file_formatted = pdf_filename

                            return {
                                "status": "success",
                                "answer": parsed_response.answer,
                                "pdf_file": pdf_file_formatted
                            }
                        except Exception as fallback_exc:
                            print(f"⚠️ [PARSE_DOC] Fallback parsing also failed: "
                                  f"{fallback_exc}")
                            logger.warning("⚠️ [PARSE_DOC] Fallback parsing also failed: %s",
                                         fallback_exc)

                            # Final fallback to raw response
                            return {
                                "status": "success",
                                "answer": response.text,
                                "pdf_file": pdf_filename
                            }
            except Exception as exc:
                model_time = time.time() - model_start
                print(f"❌ [PARSE_DOC] Model {model_name} failed in {model_time:.2f}s: {exc}")
                logger.error("❌ [PARSE_DOC] Model %s failed in %.2fs: %s",
                           model_name, model_time, exc)
                if model_name == models_to_try[-1]:
                    return {
                        "status": "error",
                        "message": f"All models failed. Last error: {exc}"
                    }
                continue

        return {
            "status": "error",
            "message": "All models failed to generate response."
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Error parsing document: {exc}"
        }


# Example usage
if __name__ == "__main__":

    # Test the function with latency measurement
    TEST_QUERY = "How do I set up Wi-Fi?"
    TEST_FILE = "053.pdf"

    print("🔍 Testing parse_doc function")
    print(f"Query: {TEST_QUERY}")
    print(f"File: {TEST_FILE}")
    print("=" * 50)

    start_time = time.time()
    result = parse_doc_tool(TEST_QUERY, TEST_FILE)
    end_time = time.time()

    latency = end_time - start_time

    print("=" * 50)
    print(f"⏱️  Total Latency: {latency:.2f} seconds")
    print(f"📊 Status: {result.get('status', 'unknown')}")

    if result.get('status') == 'success':
        print(f"📝 Answer Length: {len(result.get('answer', ''))} characters")
        print(f"💬 Answer Preview: {result.get('answer', '')[:200]}...")
    else:
        print(f"❌ Error: {result.get('message', 'unknown error')}")

    print("=" * 50)
