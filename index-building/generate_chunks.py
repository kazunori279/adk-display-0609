"""
Generate document explanations using Google Gemini API.

This module processes PDF documents and generates explanations
using the Google Gemini API.
"""

from models import DocumentQueries
from gemini_utils import create_gemini_client, upload_pdf, get_rag_prompt, generate_with_fallback
from csv_utils import write_queries_to_csv, print_query_summary
from config import DEFAULT_PDF_FILENAME


def main():
    """Main function to process PDF and generate explanation."""
    client = create_gemini_client()
    uploaded_file = upload_pdf(client, DEFAULT_PDF_FILENAME)
    prompt = get_rag_prompt()
    response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)

    # Process the structured response
    print("\nReceived structured response")
    print("-" * 50)

    document_queries = response.parsed

    # Print document description
    print("\nDocument Description:")
    print(document_queries.description)
    print("-" * 50)

    # Print summary
    print_query_summary(document_queries)
    print("-" * 50)

    # Print each section and its queries
    for section in document_queries.sections:
        print(f"\n## {section.section_name} ({len(section.queries)} queries)")
        for i, query_obj in enumerate(section.queries, 1):
            print(f"{i}. {query_obj.query}")


def process_pdf_to_csv(pdf_filename: str, csv_filename: str = "file_description.csv"):
    """
    Process a PDF file with Gemini and append results to a CSV file.

    Args:
        pdf_filename: Name of the PDF file to process (in resources directory)
        csv_filename: Name of the CSV file to append to (default: "file_description.csv")

    Returns:
        DocumentQueries: The parsed document queries object

    Raises:
        ValueError: If GOOGLE_API_KEY is not found
        FileNotFoundError: If PDF file is not found
        RuntimeError: If all Gemini models fail
    """
    client = create_gemini_client()
    uploaded_file = upload_pdf(client, pdf_filename)
    prompt = get_rag_prompt()
    response = generate_with_fallback(client, uploaded_file, prompt, DocumentQueries)

    document_queries = response.parsed
    if not document_queries:
        raise RuntimeError("Failed to parse response from Gemini")

    write_queries_to_csv(document_queries, csv_filename)
    print(f"Processed {pdf_filename} and appended to {csv_filename}")
    print_query_summary(document_queries)

    return document_queries


if __name__ == "__main__":
    main()
