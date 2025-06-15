#!/usr/bin/env python3
"""
Create embeddings CSV with enhanced progress tracking.

This version includes detailed progress reporting with:
- Real-time progress percentage
- Processing rate (items/min)
- Estimated time remaining
- Success/error rates
- Rate limiting status
"""

import csv
import json
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict
from generate_embeddings import generate_text_embeddings


class RateLimiter:
    """Rate limiter to throttle API requests."""

    def __init__(self, max_requests_per_minute: int = 1500):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if we've exceeded the rate limit."""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]

            # If we're at the limit, wait until we can make another request
            if len(self.requests) >= self.max_requests:
                # Wait until the oldest request is 60 seconds old
                sleep_time = 60 - (now - self.requests[0]) + 0.1  # Add small buffer
                if sleep_time > 0:
                    print(f"   ⏳ Rate limit reached, waiting {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    # Remove old requests after waiting
                    now = time.time()
                    self.requests = [req_time for req_time in self.requests if now - req_time < 60]

            # Record this request
            self.requests.append(now)


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests_per_minute=1500)


def read_csv_file(csv_path: Path) -> List[Dict[str, str]]:
    """Read the CSV file and return a list of dictionaries."""
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"✓ Read {len(rows):,} rows from {csv_path}")
    return rows


def create_embedding_texts(rows: List[Dict[str, str]]) -> List[str]:
    """Create text strings for embedding generation by concatenating description and query."""
    texts = []
    for row in rows:
        description = row.get('description', '').strip()
        query = row.get('query', '').strip()
        # Concatenate description + space + query
        combined_text = f"{description} {query}".strip()
        texts.append(combined_text)
    print(f"✓ Created {len(texts):,} embedding texts")
    return texts


def process_text_batch(batch_data: tuple) -> tuple:
    """Process a batch of texts to generate embeddings with rate limiting."""
    batch_indices, batch_texts = batch_data
    try:
        # Wait for rate limit before making API call
        rate_limiter.wait_if_needed()

        # Generate embeddings for batch of texts (up to 20)
        embeddings = generate_text_embeddings(batch_texts)
        return (batch_indices, True, embeddings)
    except Exception as e:
        error_msg = f"Error processing batch starting at {batch_indices[0]}: {str(e)}"
        return (batch_indices, False, error_msg)


def generate_embeddings_multithreaded(texts: List[str],
                                      max_workers: int = 10) -> List[List[float]]:
    """Generate embeddings using multithreading with batching and detailed progress tracking."""
    total_texts = len(texts)
    all_embeddings = [None] * total_texts
    completed_count = 0
    error_count = 0
    start_time = time.time()
    last_progress_time = start_time
    batch_size = 20

    # Create thread-safe counters
    count_lock = threading.Lock()

    # Calculate number of batches
    total_batches = (total_texts + batch_size - 1) // batch_size

    print(f"🚀 Generating embeddings for {total_texts:,} texts using {max_workers} threads...")
    print(f"📦 Processing in batches of {batch_size} (total: {total_batches:,} batches)")
    print("📊 Detailed progress updates every 50 completions")
    print("⚡ Rate limit: 1500 requests/minute")

    # Create batches of texts with their indices
    batch_data = []
    for i in range(0, total_texts, batch_size):
        batch_end = min(i + batch_size, total_texts)
        batch_indices = list(range(i, batch_end))
        batch_texts = texts[i:batch_end]
        batch_data.append((batch_indices, batch_texts))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batch tasks
        future_to_batch = {
            executor.submit(process_text_batch, data): data[0]
            for data in batch_data
        }

        # Process completed batch tasks
        for future in as_completed(future_to_batch):
            batch_indices, success, result = future.result()

            with count_lock:
                if success:
                    # result is a list of embeddings for the batch
                    for i, embedding in enumerate(result):
                        all_embeddings[batch_indices[i]] = embedding
                        completed_count += 1
                else:
                    # Add empty embeddings for failed batch to maintain alignment
                    empty_embedding = [0.0] * 128
                    for batch_index in batch_indices:
                        all_embeddings[batch_index] = empty_embedding
                        error_count += 1
                    if error_count <= 5:  # Only show first 5 errors to avoid spam
                        print(f"   ❌ {result}")
                    elif error_count == 6:
                        print("   ❌ (Suppressing further error messages...)")

                # Show detailed progress every 50 items
                total_processed = completed_count + error_count
                current_time = time.time()

                if (total_processed % 50 == 0 or total_processed == total_texts or
                    current_time - last_progress_time > 30):  # Also update every 30 seconds

                    elapsed_time = current_time - start_time
                    progress_pct = (total_processed / total_texts) * 100

                    if total_processed > 0 and elapsed_time > 0:
                        rate_per_min = (total_processed / elapsed_time) * 60
                        remaining_texts = total_texts - total_processed
                        eta_seconds = (remaining_texts / (rate_per_min / 60)
                                       if rate_per_min > 0 else 0)
                        eta_minutes = eta_seconds / 60

                        success_rate = (completed_count / total_processed) * 100

                        # Format ETA
                        if eta_minutes < 60:
                            eta_str = f"{eta_minutes:.1f} minutes"
                        else:
                            eta_hours = eta_minutes / 60
                            eta_str = f"{eta_hours:.1f} hours"

                        print("\n   📈 Progress Report:")
                        print(f"      📊 Completed: {total_processed:,}/{total_texts:,} "
                              f"({progress_pct:.1f}%)")
                        print(f"      ✅ Success: {completed_count:,} ({success_rate:.1f}%)")
                        print(f"      ❌ Errors: {error_count:,}")
                        print(f"      ⚡ Rate: {rate_per_min:.1f} texts/min")
                        print(f"      ⏱️  ETA: {eta_str}")
                        print(f"      🕒 Elapsed: {elapsed_time/60:.1f} minutes")
                        print("   " + "─" * 50)

                        last_progress_time = current_time

    final_time = time.time() - start_time
    final_rate = (total_texts / final_time) * 60

    print("\n🎉 Generation Complete!")
    print(f"   📊 Total: {total_texts:,} texts in {final_time/60:.1f} minutes")
    print(f"   ✅ Success: {completed_count:,} "
          f"({(completed_count/total_texts)*100:.1f}%)")
    print(f"   ❌ Errors: {error_count:,} ({(error_count/total_texts)*100:.1f}%)")
    print(f"   ⚡ Average rate: {final_rate:.1f} texts/min")

    return all_embeddings


def write_embeddings_csv(rows: List[Dict[str, str]],
                        embeddings: List[List[float]], output_path: Path):
    """Write the new CSV file with filename, page number, and embeddings columns."""
    if len(rows) != len(embeddings):
        raise ValueError(f"Mismatch: {len(rows)} rows but {len(embeddings)} embeddings")

    # Include filename, page number, and embeddings columns
    fieldnames = ['pdf_filename', 'subsection_pdf_page_number', 'embeddings']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row, embedding in zip(rows, embeddings):
            # Create new row with filename, page number, and embeddings
            new_row = {
                'pdf_filename': row.get('pdf_filename', ''),
                'subsection_pdf_page_number': row.get('subsection_pdf_page_number', ''),
                'embeddings': json.dumps(embedding)
            }
            writer.writerow(new_row)

    print(f"✓ Wrote {len(rows):,} rows with filename, page number, and embeddings to {output_path}")


def main():
    """Main function to process CSV and generate embeddings with enhanced progress."""
    print("=" * 70)
    print("CSV Embeddings Generator (Enhanced Progress Tracking)")
    print("=" * 70)

    # Define file paths
    data_dir = Path(__file__).parent / "data"
    input_csv = data_dir / "file_description.csv"
    output_csv = data_dir / "file_desc_emb.csv"

    # Check if input file exists
    if not input_csv.exists():
        print(f"❌ Input file not found: {input_csv}")
        print("Please ensure file_description.csv exists in the data/ directory")
        sys.exit(1)

    try:
        # Step 1: Read the original CSV
        print(f"\n📖 Reading input CSV: {input_csv}")
        rows = read_csv_file(input_csv)

        if not rows:
            print("❌ No data found in CSV file")
            sys.exit(1)

        # Show sample data
        print("\n📋 Sample row structure:")
        if rows:
            sample_row = rows[0]
            for key, value in sample_row.items():
                print(f"   {key}: {value}")

        # Step 2: Create embedding texts
        print("\n🔧 Preparing embedding texts...")
        texts = create_embedding_texts(rows)

        # Show sample embedding text
        if texts:
            print(f"\n📝 Sample embedding text: '{texts[0][:100]}...'")

        # Step 3: Generate embeddings with rate limiting
        print("\n🤖 Generating embeddings using Vertex AI with rate limiting (1500/min)...")
        embeddings = generate_embeddings_multithreaded(texts, max_workers=10)

        # Step 4: Write new CSV with embeddings
        print(f"\n💾 Writing output CSV: {output_csv}")
        write_embeddings_csv(rows, embeddings, output_csv)

        print(f"\n✅ Successfully created {output_csv}")
        print(f"   Output columns: pdf_filename, subsection_pdf_page_number, embeddings")
        print(f"   Total rows: {len(rows):,}")
        print(f"   Embedding dimensions: 128")

    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
