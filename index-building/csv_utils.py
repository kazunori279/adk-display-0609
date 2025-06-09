"""Utility functions for CSV operations."""

import csv
from pathlib import Path
from models import DocumentQueries


def write_queries_to_csv(
    document_queries: DocumentQueries, csv_filename: str = "file_description.csv"
) -> None:
    """Write document queries to a CSV file."""
    csv_path = Path(__file__).parent / csv_filename
    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["description", "section_name", "pdf_page_number", "query"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for section in document_queries.sections:
            for query_obj in section.queries:
                writer.writerow(
                    {
                        "description": document_queries.description,
                        "section_name": section.section_name,
                        "pdf_page_number": section.pdf_page_number,
                        "query": query_obj.query,
                    }
                )


def count_total_queries(document_queries: DocumentQueries) -> int:
    """Count total queries across all sections."""
    return sum(len(section.queries) for section in document_queries.sections)


def print_query_summary(document_queries: DocumentQueries) -> None:
    """Print a summary of the document queries."""
    print(f"\nDocument: {document_queries.description}")
    print(f"Total sections: {len(document_queries.sections)}")
    print(f"Total queries: {count_total_queries(document_queries)}")

    for section in document_queries.sections:
        query_count = len(section.queries)
        print(f"  - {section.section_name} (p.{section.pdf_page_number}): {query_count} queries")
