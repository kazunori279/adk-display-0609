"""Configuration constants for the project."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
RESOURCES_DIR = PROJECT_ROOT / "resources"
TESTS_DIR = PROJECT_ROOT / "tests"

DEFAULT_CSV_FILENAME = "file_description.csv"
DEFAULT_PDF_FILENAME = "waste_separation_guide.pdf"

GEMINI_MODELS = [
    "gemini-2.5-pro-preview-06-05",
    "gemini-2.0-flash-preview-0514",
    "gemini-1.5-flash",
]
