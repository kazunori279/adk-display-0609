"""PDF to JSON document parser using Gemini 2.5 Pro.

This module provides functionality to parse PDF documents from the resources
directory and convert them to structured JSON files using Google's Gemini 2.5 Pro model.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import PROJECT_ROOT, RESOURCES_DIR
from models import DocumentStructure

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _create_gemini_client() -> genai.Client:
    """Create and return a configured Gemini client."""
    # Load .env file from project root or backend directory
    env_paths = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT.parent / ".env",
        PROJECT_ROOT.parent / "backend" / ".env",
        Path.cwd() / ".env"
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment from: %s", env_path)
            break

    # Check if we should use Vertex AI or direct API
    # Use Vertex AI for gemini-2.5-pro-preview-06-05
    use_vertexai = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE').upper() == 'TRUE'

    if use_vertexai:
        # Set up service account credentials for Vertex AI
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            # Convert relative path to absolute path from PROJECT_ROOT
            if not os.path.isabs(credentials_path):
                credentials_path = str((PROJECT_ROOT / credentials_path).absolute())
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                logger.info("Using credentials at: %s", credentials_path)

        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required for Vertex AI")

        logger.info("Using Vertex AI client (Project: %s, Location: %s)", project_id, location)
        return genai.Client(vertexai=True)

    # Use direct API client
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")

    logger.info("Using direct API client")
    return genai.Client(api_key=api_key)


def _get_prompt() -> str:
    """Get the prompt for document conversion."""
    return """Generate convert this document to a structured document in JSON format, with:
1) title and short summary
2) a list of sections where each section has a list of subsections
3) each subsection has a "text" property that contains all texts in the subsection, and "page_number" property that represents the page number in the pdf file (not the page number printed in the content).

CRITICAL LANGUAGE REQUIREMENT:
- For the "title" field: Extract EXACTLY what appears as the title in the PDF. Do not translate.
- For the "summary" field: If the document's main content is in Japanese, write the summary in Japanese. If the document's main content is in English, write the summary in English. Match the primary language of the document.
- DO NOT TRANSLATE ANY EXTRACTED TEXT. Keep everything in its original language.
- If a document contains mixed languages (e.g., English title but Japanese content), preserve each part in its original language.

You must respond in JSON format with these exact fields:
- "title": The exact title text from the PDF without any translation (string)
- "summary": A brief summary in the same language as the document's main content (string)
- "sections": Array of section objects, each containing:
  - "name": The exact section heading from the PDF without translation (string)
  - "subsections": Array of subsection objects, each containing:
    - "name": The exact subsection heading from the PDF without translation (string)
    - "text": All text content exactly as it appears in the PDF (string)
    - "page_number": PDF page number where this content appears (integer)

IMPORTANT: For documents that are primarily in Japanese (even if they have some English words),
the summary MUST be written in Japanese. Look at the main body content to determine the primary language.

Please analyze the entire document and structure it logically. Ensure that all text content is captured in the subsections and that page numbers accurately reflect the PDF page numbers (not any printed page numbers in the document content)."""


def _process_response(response: Any, json_path: Path, model_name: str,
                     pdf_path: Path, model_time: float, models_to_try: list) -> Dict[str, Any]:
    """Process the Gemini response and save to JSON."""
    try:
        # Try to access the parsed response object directly
        if hasattr(response, 'parsed') and response.parsed:
            parsed_response: DocumentStructure = response.parsed
            document_dict = parsed_response.model_dump()
        else:
            # Fallback to manual JSON parsing
            document_dict = json.loads(response.text)
            # Validate with Pydantic
            DocumentStructure.model_validate(document_dict)

        # Save to JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(document_dict, f, ensure_ascii=False, indent=2)

        logger.info("Successfully saved JSON to: %s", json_path)

        return {
            "status": "success",
            "message": "Document processed successfully",
            "input_file": str(pdf_path),
            "output_file": str(json_path),
            "model_used": model_name,
            "processing_time": model_time,
            "document_data": document_dict
        }

    except json.JSONDecodeError as parse_exc:
        logger.warning("Failed to parse response from %s: %s", model_name, parse_exc)
        logger.info("Raw response: %s", response.text)

        # If this is the last model, try to save raw response
        if model_name == models_to_try[-1]:
            try:
                # Attempt to save raw JSON response
                raw_data = json.loads(response.text)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_data, f, ensure_ascii=False, indent=2)

                return {
                    "status": "partial_success",
                    "message": "Document processed but validation failed",
                    "input_file": str(pdf_path),
                    "output_file": str(json_path),
                    "model_used": model_name,
                    "processing_time": model_time,
                    "warning": f"Response validation failed: {parse_exc}"
                }
            except json.JSONDecodeError as save_exc:
                logger.error("Failed to save raw response: %s", save_exc)
    return None


def _process_with_model(client: Any, model_name: str, content: list,
                       json_path: Path, pdf_path: Path, models_to_try: list) -> Dict[str, Any]:
    """Process PDF with a specific model."""
    try:
        model_start = time.time()
        logger.info("Calling Gemini %s...", model_name)

        response = client.models.generate_content(
            model=model_name,
            contents=content,
            config={
                "response_mime_type": "application/json",
                "response_schema": DocumentStructure,
            }
        )

        model_time = time.time() - model_start

        if response.text:
            logger.info("Gemini response received in %.2fs", model_time)
            result = _process_response(response, json_path, model_name,
                                     pdf_path, model_time, models_to_try)
            if result:
                return result

    except Exception as exc:
        model_time = time.time() - model_start
        logger.error("Model %s failed in %.2fs: %s", model_name, model_time, exc)

        if model_name == models_to_try[-1]:
            return {
                "status": "error",
                "message": f"All models failed. Last error: {exc}"
            }
    return None


def parse_pdf_to_json(pdf_filename: str, output_dir: Optional[str] = None) -> dict:
    """Parse a PDF document and convert it to structured JSON format.

    Args:
        pdf_filename: Name of the PDF file in the resources directory (e.g., "001.pdf")
        output_dir: Directory to save the JSON file. Defaults to data/ directory.

    Returns:
        Dictionary with status and result information
    """
    if not pdf_filename:
        return {
            "status": "error",
            "message": "No PDF filename provided"
        }

    # Construct file paths
    pdf_path = RESOURCES_DIR / pdf_filename
    if not pdf_path.exists():
        return {
            "status": "error",
            "message": f"PDF file not found: {pdf_path}"
        }

    # Set output directory
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data"
    else:
        output_dir = Path(output_dir)

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    # Generate output filename
    json_filename = pdf_filename.replace('.pdf', '.json')
    json_path = output_dir / json_filename

    try:
        # Create Gemini client
        client = _create_gemini_client()

        logger.info("Processing PDF: %s", pdf_path)

        # Read PDF file and create Part object
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        pdf_file_part = types.Part.from_bytes(
            data=pdf_data,
            mime_type="application/pdf"
        )

        # Prepare the prompt
        prompt = _get_prompt()

        # Prepare content list with PDF part and prompt
        content = [pdf_file_part, prompt]

        # Use gemini-2.5-pro-preview-06-05 model
        models_to_try = [
            "gemini-2.5-pro-preview-06-05",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]

        for model_name in models_to_try:
            result = _process_with_model(client, model_name, content,
                                       json_path, pdf_path, models_to_try)
            if result:
                return result

        return {
            "status": "error",
            "message": "All models failed to generate response"
        }

    except Exception as exc:
        logger.error("Error processing document: %s", exc)
        return {
            "status": "error",
            "message": f"Error processing document: {exc}"
        }


def main():
    """Main function for command line usage."""
    if len(sys.argv) != 2:
        print("Usage: python parse_doc.py <pdf_filename>")
        print("Example: python parse_doc.py 001.pdf")
        sys.exit(1)

    pdf_filename = sys.argv[1]

    print(f"🔍 Processing PDF: {pdf_filename}")
    print("=" * 50)

    start_time = time.time()
    result = parse_pdf_to_json(pdf_filename)
    end_time = time.time()

    total_time = end_time - start_time

    print("=" * 50)
    print(f"⏱️  Total Time: {total_time:.2f} seconds")
    print(f"📊 Status: {result.get('status', 'unknown')}")

    if result.get('status') == 'success':
        print(f"✅ Input: {result.get('input_file', 'unknown')}")
        print(f"📄 Output: {result.get('output_file', 'unknown')}")
        print(f"🤖 Model: {result.get('model_used', 'unknown')}")
        print(f"⚡ Processing Time: {result.get('processing_time', 0):.2f}s")

        # Show document structure summary
        doc_data = result.get('document_data', {})
        if doc_data:
            print(f"📖 Title: {doc_data.get('title', 'N/A')}")
            print(f"📝 Summary: {doc_data.get('summary', 'N/A')[:100]}...")
            sections = doc_data.get('sections', [])
            print(f"📑 Sections: {len(sections)}")
            total_subsections = sum(len(section.get('subsections', [])) for section in sections)
            print(f"📋 Total Subsections: {total_subsections}")
    else:
        print(f"❌ Error: {result.get('message', 'unknown error')}")

    print("=" * 50)


if __name__ == "__main__":
    main()
