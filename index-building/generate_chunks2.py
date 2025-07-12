"""
Generate structured JSON documents using Google Gemini 2.5 Pro API.

This module processes PDF documents and generates structured JSON representations
using the Google Gemini 2.5 Pro model.
"""

import json
from pathlib import Path
from models2 import StructuredDocument
from gemini_utils import create_gemini_client, upload_pdf
from config import DEFAULT_PDF_FILENAME


def get_structured_document_prompt() -> str:
    """Return the prompt for generating structured JSON documents."""
    return (
        "Convert this document to a structured document in JSON format, with "
        "1) title and short summary, "
        "2) a list of sections where each section has a list of subsections, "
        "3) each subsection has a 'text' property that contains all texts in the subsection, "
        "and 'page_number' property that represents the page number in the pdf file "
        "(not the page number printed in the content)."
    )


def generate_with_gemini_2_5_pro(client, uploaded_file, prompt: str, response_schema: type):
    """Generate content using specifically gemini-2.5-pro model."""
    model_name = "gemini-2.5-pro"
    
    print(f"Sending to Gemini model: {model_name}")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_file, prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )
        print(f"Successfully used model: {model_name}")
        return response
    except Exception as error:
        print(f"Model {model_name} failed: {error}")
        raise RuntimeError(f"Gemini 2.5 Pro model failed: {error}") from error


def write_structured_document_to_json(document: StructuredDocument, json_filename: str, pdf_filename: str):
    """Write structured document to JSON file."""
    # Create output directory if it doesn't exist
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)
    
    # Create full path for JSON file
    json_path = output_dir / json_filename
    
    # Add metadata about source PDF
    document_dict = document.model_dump()
    document_dict["source_pdf"] = pdf_filename
    
    # Write to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(document_dict, f, indent=2, ensure_ascii=False)
    
    print(f"Wrote structured document to: {json_path}")


def main():
    """Main function to process PDF and generate structured JSON."""
    client = create_gemini_client()
    uploaded_file = upload_pdf(client, DEFAULT_PDF_FILENAME)
    prompt = get_structured_document_prompt()
    response = generate_with_gemini_2_5_pro(client, uploaded_file, prompt, StructuredDocument)

    # Process the structured response
    print("\nReceived structured response")
    print("-" * 50)

    structured_document = response.parsed

    # Print document info
    print(f"\nTitle: {structured_document.title}")
    print(f"Summary: {structured_document.summary}")
    print(f"Number of sections: {len(structured_document.sections)}")
    
    # Print section summary
    for i, section in enumerate(structured_document.sections, 1):
        print(f"  {i}. {section.name} ({len(section.subsections)} subsections)")

    # Write to JSON file
    json_filename = f"{Path(DEFAULT_PDF_FILENAME).stem}_structured.json"
    write_structured_document_to_json(structured_document, json_filename, DEFAULT_PDF_FILENAME)


def process_pdf_to_json(
    pdf_filename: str,
    json_filename: str = None
):
    """
    Process a PDF file with Gemini 2.5 Pro and save as structured JSON.

    Args:
        pdf_filename: Name of the PDF file to process (in resources directory)
        json_filename: Name of the JSON file to create (default: auto-generated)

    Returns:
        StructuredDocument: The parsed structured document object

    Raises:
        ValueError: If GOOGLE_API_KEY is not found
        FileNotFoundError: If PDF file is not found
        RuntimeError: If Gemini 2.5 Pro model fails
    """
    client = create_gemini_client()
    uploaded_file = upload_pdf(client, pdf_filename)
    prompt = get_structured_document_prompt()
    response = generate_with_gemini_2_5_pro(client, uploaded_file, prompt, StructuredDocument)

    structured_document = response.parsed
    if not structured_document:
        raise RuntimeError("Failed to parse response from Gemini 2.5 Pro")

    # Auto-generate JSON filename if not provided
    if json_filename is None:
        json_filename = f"{Path(pdf_filename).stem}_structured.json"

    write_structured_document_to_json(structured_document, json_filename, pdf_filename)
    
    print(f"Processed {pdf_filename} and saved to {json_filename}")
    print(f"Document: {structured_document.title}")
    print(f"Sections: {len(structured_document.sections)}")
    total_subsections = sum(len(section.subsections) for section in structured_document.sections)
    print(f"Total subsections: {total_subsections}")

    return structured_document


if __name__ == "__main__":
    main()