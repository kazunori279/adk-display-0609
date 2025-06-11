"""Utility functions for CSV operations."""

import csv
from pathlib import Path
from models import DocumentQueries


def write_queries_to_csv(
    document_queries: DocumentQueries, 
    csv_filename: str = "file_description.csv",
    pdf_filename: str = None
) -> None:
    """Write document queries to a CSV file."""
    # Ensure data directory exists
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    csv_path = data_dir / csv_filename
    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "pdf_filename",
            "description",
            "section_name", 
            "subsection_name",
            "subsection_pdf_page_number",
            "query"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for section in document_queries.sections:
            for query_obj in section.queries:
                writer.writerow(
                    {
                        "pdf_filename": pdf_filename or "unknown",
                        "description": document_queries.description,
                        "section_name": section.section_name,
                        "subsection_name": section.subsection_name,
                        "subsection_pdf_page_number": section.subsection_pdf_page_number,
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
        print(
            f"  - {section.section_name} > {section.subsection_name} "
            f"(p.{section.subsection_pdf_page_number}): {query_count} queries"
        )
