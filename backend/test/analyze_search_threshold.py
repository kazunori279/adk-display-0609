#!/usr/bin/env python3
"""
Analyze search result relevancy scores to determine optimal threshold.

This script uses queries from the file_description.csv to test search results
and examine score distributions to recommend a relevancy threshold.
"""

import csv
import sys
import random
from pathlib import Path
from collections import defaultdict
import statistics

# Add the backend directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.search_agent.chromadb_search import find_document


def load_test_queries(csv_path: str, sample_size: int = None) -> list:
    """Load queries from the CSV file."""
    queries = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                query = row['query'].strip()
                pdf_filename = row['pdf_filename']
                page_number = int(row['subsection_pdf_page_number'])
                
                if query and pdf_filename:
                    queries.append({
                        'query': query,
                        'expected_pdf': pdf_filename,
                        'expected_page': page_number
                    })
    
    except Exception as e:
        print(f"Error loading queries: {e}")
        return []
    
    print(f"Loaded {len(queries)} total queries from CSV")
    
    # Sample random queries if sample_size is specified and we have more than requested
    if sample_size is not None and len(queries) > sample_size:
        # Set random seed for reproducible results
        random.seed(42)
        queries = random.sample(queries, sample_size)
        print(f"Randomly sampled {sample_size} queries for analysis")
    
    return queries


def analyze_query_results(queries: list) -> dict:
    """Analyze search results for multiple queries."""
    print(f"Analyzing {len(queries)} queries...")
    
    results_analysis = {
        'total_queries': len(queries),
        'queries_with_results': 0,
        'correct_matches_found': 0,
        'all_scores': [],
        'relevant_scores': [],  # Scores where expected document was found
        'irrelevant_scores': [],  # Scores where expected document was not in results
        'score_distribution': defaultdict(int),
        'detailed_results': []
    }
    
    for i, query_info in enumerate(queries):
        query = query_info['query']
        expected_pdf = query_info['expected_pdf']
        expected_page = query_info['expected_page']
        
        print(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")
        
        # Get search results
        results = find_document(query)
        
        if results:
            results_analysis['queries_with_results'] += 1
            
            # Check if expected document is in results
            found_expected = False
            expected_score = None
            
            for filename, description, score in results:
                results_analysis['all_scores'].append(score)
                
                # Check if this matches expected result
                page_match = None
                import re
                page_search = re.search(r'\(page (\d+)\)', description)
                if page_search:
                    page_match = int(page_search.group(1))
                
                if filename == expected_pdf and page_match == expected_page:
                    found_expected = True
                    expected_score = score
                    results_analysis['relevant_scores'].append(score)
                    break
            
            if found_expected:
                results_analysis['correct_matches_found'] += 1
            else:
                # If expected document not found, all scores are considered irrelevant for this query
                for filename, description, score in results:
                    results_analysis['irrelevant_scores'].append(score)
            
            # Store detailed results
            results_analysis['detailed_results'].append({
                'query': query,
                'expected_pdf': expected_pdf,
                'expected_page': expected_page,
                'found_expected': found_expected,
                'expected_score': expected_score,
                'results': results
            })
            
            # Group scores by ranges for distribution analysis
            for filename, description, score in results:
                score_range = round(score, 1)
                results_analysis['score_distribution'][score_range] += 1
    
    return results_analysis


def recommend_threshold(analysis: dict) -> float:
    """Recommend a relevancy threshold based on analysis."""
    relevant_scores = analysis['relevant_scores']
    irrelevant_scores = analysis['irrelevant_scores']
    
    if not relevant_scores or not irrelevant_scores:
        print("⚠️  Insufficient data to recommend threshold")
        return 0.8  # Default conservative threshold
    
    # Calculate statistics
    relevant_mean = statistics.mean(relevant_scores)
    relevant_min = min(relevant_scores)
    relevant_std = statistics.stdev(relevant_scores) if len(relevant_scores) > 1 else 0
    
    irrelevant_mean = statistics.mean(irrelevant_scores)
    irrelevant_max = max(irrelevant_scores)
    irrelevant_std = statistics.stdev(irrelevant_scores) if len(irrelevant_scores) > 1 else 0
    
    print(f"\n📊 Score Analysis:")
    print(f"Relevant scores  - Mean: {relevant_mean:.3f}, Min: {relevant_min:.3f}, Std: {relevant_std:.3f}")
    print(f"Irrelevant scores - Mean: {irrelevant_mean:.3f}, Max: {irrelevant_max:.3f}, Std: {irrelevant_std:.3f}")
    
    # Recommend threshold as the mean of relevant scores minus one standard deviation
    # This should capture most relevant results while filtering out irrelevant ones
    recommended_threshold = max(relevant_mean - relevant_std, relevant_min)
    
    # Ensure it's above the maximum irrelevant score if possible
    if recommended_threshold <= irrelevant_max:
        recommended_threshold = min(irrelevant_max + 0.05, relevant_min)
    
    return recommended_threshold


def print_detailed_analysis(analysis: dict, show_examples: int = 5):
    """Print detailed analysis results."""
    total = analysis['total_queries']
    with_results = analysis['queries_with_results']
    correct_matches = analysis['correct_matches_found']
    
    print(f"\n🔍 Search Analysis Results:")
    print(f"Total queries tested: {total}")
    print(f"Queries with results: {with_results} ({with_results/total*100:.1f}%)")
    print(f"Correct matches found: {correct_matches} ({correct_matches/total*100:.1f}%)")
    
    if analysis['all_scores']:
        all_scores = analysis['all_scores']
        print(f"\n📈 Score Statistics:")
        print(f"Total results analyzed: {len(all_scores)}")
        print(f"Score range: {min(all_scores):.3f} - {max(all_scores):.3f}")
        print(f"Mean score: {statistics.mean(all_scores):.3f}")
        print(f"Median score: {statistics.median(all_scores):.3f}")
    
    # Show example queries with their results
    print(f"\n📝 Example Results (first {show_examples}):")
    for i, result in enumerate(analysis['detailed_results'][:show_examples]):
        query = result['query']
        expected = f"{result['expected_pdf']} page {result['expected_page']}"
        found = "✅" if result['found_expected'] else "❌"
        expected_score = result['expected_score'] or "N/A"
        
        print(f"\n{i+1}. Query: {query}")
        print(f"   Expected: {expected}")
        print(f"   Found expected: {found} (score: {expected_score})")
        print(f"   Top results:")
        
        for j, (filename, description, score) in enumerate(result['results'][:3]):
            mark = "⭐" if filename == result['expected_pdf'] else "  "
            print(f"   {mark} {j+1}. {filename}: {description} (score: {score:.3f})")


def main():
    """Main analysis function."""
    print("🔍 Analyzing search result relevancy scores...")
    
    # Path to the CSV file
    csv_path = Path(__file__).parent.parent.parent / "index-building" / "data" / "file_description.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    # Load test queries - use manageable sample for analysis (200 queries)
    print(f"Loading queries from {csv_path}")
    queries = load_test_queries(str(csv_path), sample_size=200)
    
    if not queries:
        print("❌ No queries loaded")
        return
    
    # Analyze results
    analysis = analyze_query_results(queries)
    
    # Print detailed analysis
    print_detailed_analysis(analysis)
    
    # Recommend threshold
    threshold = recommend_threshold(analysis)
    print(f"\n🎯 Recommended Relevancy Threshold: {threshold:.3f}")
    
    # Show impact of threshold
    relevant_above = len([s for s in analysis['relevant_scores'] if s >= threshold])
    relevant_total = len(analysis['relevant_scores'])
    irrelevant_above = len([s for s in analysis['irrelevant_scores'] if s >= threshold])
    irrelevant_total = len(analysis['irrelevant_scores'])
    
    print(f"\n📊 Threshold Impact:")
    print(f"Relevant results above threshold: {relevant_above}/{relevant_total} ({relevant_above/relevant_total*100:.1f}%)")
    print(f"Irrelevant results above threshold: {irrelevant_above}/{irrelevant_total} ({irrelevant_above/irrelevant_total*100:.1f}%)")
    
    return threshold


if __name__ == "__main__":
    main()