# ADK Display Index Building

This module processes PDF documents and generates vector embeddings for RAG
(Retrieval-Augmented Generation) systems.

## Installation

1. Navigate to the index-building directory:

   ```bash
   cd index-building
   ```

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

1. Create a `.env` file in the index-building directory with your Google API key:

   ```env
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   GOOGLE_API_KEY=your_api_key_here
   ```

## Testing

Run all tests (including integration tests that make real API calls):

```bash
python -m pytest -v
```

Note: Integration tests require a valid `GOOGLE_API_KEY` in the `.env` file and
will consume API quota.

## Usage

### Step 1: Generate CSV from PDF Files

This system processes PDF documents and generates search queries with
subsection-level granularity and PDF source tracking.

#### Process All PDFs (Recommended)

Process all PDF files in the `resources/` directory using multithreaded
processing:

```bash
python process_all_pdfs.py
```

**Features:**

- **10 concurrent threads** for fast processing
- **Automatic error handling** and retry logic
- **Progress tracking** with detailed output
- **Error logging** to `processing_errors.log`

**Output:**

- `data/file_description.csv` - Main CSV with all queries
- `data/pdf_mapping.txt` - Maps numbered files to original names
- `data/processing_errors.log` - Any processing errors

#### Process Single PDF

Process a specific PDF file:

```python
# Process a single PDF
from generate_chunks import process_pdf_to_csv
result = process_pdf_to_csv('001.pdf', 'output.csv')
print(f'Generated {sum(len(s.queries) for s in result.sections)} queries')
```

#### Custom Processing

For custom query counts or specific requirements:

```python
from generate_chunks import process_pdf_to_csv

# Process with custom number of queries per section
result = process_pdf_to_csv(
    pdf_filename='001.pdf',
    csv_filename='custom_output.csv', 
    queries_per_section=25  # Default: 50
)
```

### Step 2: Generate Embeddings

After generating the CSV with search queries, create vector embeddings for RAG
systems:

```bash
python create_embeddings_csv.py
```

**Features:**

- **Batch processing:** Processes up to 20 texts per API call for maximum
  efficiency
- **Multithreaded:** 10 concurrent workers with intelligent rate limiting
- **Progress tracking:** Real-time updates showing completion percentage,
  processing rate, and ETA
- **Rate limiting:** Respects Vertex AI quota limits (1500 requests/minute)
- **Error handling:** Graceful handling of API failures with detailed error
  reporting

**Input:** `data/file_description.csv` (generated from PDF processing)

**Output:** `data/file_desc_emb.csv` (original data + embeddings column)

**Embedding Details:**

- **Model:** `text-multilingual-embedding-002` (Vertex AI)
- **Dimensions:** 768
- **Task Type:** `SEMANTIC_SIMILARITY`
- **Input:** Concatenated "description + query" text

**Progress Example:**

```text
🚀 Generating embeddings for 34,504 texts using 10 threads...
📦 Processing in batches of 20 (total: 1,726 batches)

📈 Progress Report:
   📊 Completed: 1,000/34,504 (2.9%)
   ✅ Success: 1,000 (100.0%)
   ⚡ Rate: 650.0 texts/min
   ⏱️  ETA: 51.5 minutes
```

**Performance:**

- **Efficiency:** ~20x faster than single-item processing
- **Throughput:** ~650 texts/minute (respecting API limits)
- **Memory:** Streams processing for large datasets

## Output Format

### CSV Output Structure

The generated CSV contains the following columns:

| Column | Description |
|--------|-------------|
| `pdf_filename` | Source PDF file (e.g., "001.pdf") |
| `description` | Brief description of the document |
| `section_name` | Main section title |
| `subsection_name` | Specific subsection within the section |
| `subsection_pdf_page_number` | Page number where subsection starts |
| `query` | Generated search query in Japanese |
| `embeddings` | Vector embeddings (768 dimensions, JSON format) |

### PDF File Management

PDF files are automatically renamed to numbered format (001.pdf - 070.pdf) for
efficient processing. The mapping between numbered files and original descriptive
names is maintained in `data/pdf_mapping.txt`.

## Configuration

### Query Generation

Adjust query generation in `gemini_utils.py`:

- **Default:** 50 queries per section (production)
- **Testing:** 10 queries per section (faster)
- **Timeout handling:** Automatic fallback between Gemini models

### Performance Tuning

- **Multithreading:** 10x faster processing with concurrent threads
- **Rate limiting:** Built-in delays to respect API limits
- **Memory efficient:** Streams results directly to CSV
- **Error recovery:** Automatic retry for failed PDFs

## Troubleshooting

1. **API Key Issues:** Ensure `GOOGLE_API_KEY` is set in `.env`
1. **PDF Not Found:** Check that PDF files exist in `resources/` directory
1. **Processing Errors:** Review `data/processing_errors.log` for details
1. **Rate Limits:** Built-in delays handle most rate limiting automatically
1. **Embedding Errors:** Check Vertex AI credentials and quota limits
