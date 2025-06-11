#!/usr/bin/env python3
"""
Integration test for generate_embeddings module.

This test makes real API calls to Vertex AI and processes actual text data.
Run with: python test_generate_embeddings_integration.py

WARNING: This will consume API quota and may incur costs.
"""

import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv
import pytest

# Add parent directory to path so we can import generate_embeddings
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_embeddings import generate_text_embeddings


def test_generate_embeddings_integration():
    """Integration test that generates embeddings using real Vertex AI API."""
    print("Running integration test for generate_text_embeddings...")
    print("-" * 60)

    # Load environment variables from current directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Check if we have the required Google Cloud credentials
    # Vertex AI uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS
    gcp_creds_path = "~/.config/gcloud/application_default_credentials.json"
    has_credentials = (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
        os.environ.get("GOOGLE_CLOUD_PROJECT") or
        # Check if gcloud is configured (common case)
        os.path.exists(os.path.expanduser(gcp_creds_path))
    )

    if not has_credentials:
        print("❌ Google Cloud credentials not found")
        print("Please ensure you have:")
        print("1. GOOGLE_APPLICATION_CREDENTIALS environment variable set, OR")
        print("2. Run 'gcloud auth application-default login', OR")
        print("3. Set GOOGLE_CLOUD_PROJECT environment variable")
        pytest.skip("Google Cloud credentials not found")

    # Note about project configuration
    print("📋 NOTE: This test uses the project ID configured in generate_embeddings.py")
    print("   Current project: gcp-samples-ic0")
    print("   You may need to update the PROJECT_ID in generate_embeddings.py")
    print("   to match your actual Google Cloud project.")
    print()

    # Test data - Japanese appliance items similar to what would be in the PDF corpus
    test_items = [
        {
            "name": "エアコン",
            "description": "冷暖房機能付きの家電製品。室内の温度を調整する装置。"
        },
        {
            "name": "洗濯機",
            "description": "衣類を自動で洗浄する機械。水と洗剤を使用して汚れを除去。"
        },
        {
            "name": "冷蔵庫",
            "description": "食品を冷却保存する電化製品。食材の鮮度を保つ。"
        },
        {
            "name": "電子レンジ",
            "description": "マイクロ波を使用して食品を加熱する調理器具。"
        },
        {
            "name": "炊飯器",
            "description": "米を炊くための専用調理器具。自動で適切な温度と時間を制御。"
        }
    ]

    print(f"📝 Testing with {len(test_items)} Japanese appliance items")

    try:
        print("🚀 Generating embeddings with Vertex AI...")

        # Call the function with real API
        embeddings = generate_text_embeddings(test_items)

        print("✅ Successfully generated embeddings!")

        # Verify the results
        print("\n📊 Verification Results:")
        print(f"   Number of embeddings: {len(embeddings)}")
        print(f"   Expected: {len(test_items)}")

        # Check basic structure
        expected_count = len(test_items)
        actual_count = len(embeddings)
        assert actual_count == expected_count, (
            f"Expected {expected_count} embeddings, got {actual_count}")

        # Check each embedding
        for i, embedding in enumerate(embeddings):
            item_name = test_items[i]["name"]
            print(f"\n   📋 Embedding {i+1} ({item_name}):")
            print(f"      Dimensions: {len(embedding)}")
            print(f"      Type: {type(embedding)}")
            print(f"      Sample values: {embedding[:5]}...")

            # Verify embedding properties
            assert isinstance(embedding, list), f"Embedding {i+1} is not a list"
            expected_dims = 768
            actual_dims = len(embedding)
            assert actual_dims == expected_dims, (
                f"Embedding {i+1} has {actual_dims} dimensions, expected {expected_dims}")
            assert all(isinstance(val, float) for val in embedding), (
                f"Embedding {i+1} contains non-float values")

            # Check that values are in reasonable range (embeddings are typically normalized)
            assert all(-2.0 <= val <= 2.0 for val in embedding), (
                f"Embedding {i+1} has values outside expected range")

        print("✅ All embeddings have correct structure (768 dimensions)")

        # Test semantic similarity by checking that similar items have similar embeddings
        print("\n🔍 Testing semantic relationships...")

        # Calculate simple cosine similarity between first two embeddings
        emb1, emb2 = embeddings[0], embeddings[1]
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        magnitude1 = sum(a * a for a in emb1) ** 0.5
        magnitude2 = sum(b * b for b in emb2) ** 0.5
        cosine_similarity = dot_product / (magnitude1 * magnitude2)

        print(f"   Cosine similarity between '{test_items[0]['name']}' and "
              f"'{test_items[1]['name']}': {cosine_similarity:.4f}")

        # Embeddings should be somewhat similar (both are appliances) but not identical
        assert 0.0 <= cosine_similarity <= 1.0, f"Invalid cosine similarity: {cosine_similarity}"
        assert cosine_similarity > 0.1, f"Embeddings seem too dissimilar: {cosine_similarity}"
        assert cosine_similarity < 0.99, f"Embeddings seem too similar: {cosine_similarity}"

        print("✅ Semantic similarity is within expected range")

        # Test with Japanese characters specifically
        print("\n🔤 Testing Japanese text handling...")
        japanese_chars_found = 0
        for i, item in enumerate(test_items):
            combined_text = item["name"] + " " + item["description"]
            for char in combined_text:
                if ('\u3040' <= char <= '\u309f' or  # Hiragana
                    '\u30a0' <= char <= '\u30ff' or  # Katakana
                    '\u4e00' <= char <= '\u9fff'):   # Kanji
                    japanese_chars_found += 1
                    break

        print(f"   Items with Japanese characters: {japanese_chars_found}/{len(test_items)}")
        assert japanese_chars_found == len(test_items), "Not all items contain Japanese characters"
        print("✅ Japanese text handling verified")

        # Performance metrics
        print("\n⏱️  Performance metrics:")
        print(f"   Total items processed: {len(test_items)}")
        print(f"   Total embedding dimensions: {len(embeddings) * 768}")
        print(f"   Average embedding magnitude: {(magnitude1 + magnitude2) / 2:.4f}")

        print("\n✅ Integration test passed successfully!")

    except Exception as e:
        error_str = str(e)
        print(f"\n❌ Error during embedding generation: {e}")

        # Provide specific guidance for common errors
        if "Permission denied" in error_str and "gcp-samples-ic0" in error_str:
            print("\n🔧 CONFIGURATION NEEDED:")
            print("   The test is trying to use project 'gcp-samples-ic0' "
                  "which you don't have access to.")
            print("   To run this integration test:")
            print("   1. Update PROJECT_ID in generate_embeddings.py to your GCP project")
            print("   2. Ensure Vertex AI API is enabled in your project")
            print("   3. Run: gcloud auth application-default login")
            print("   4. Or set GOOGLE_APPLICATION_CREDENTIALS to your service account key")
        elif "Permission denied" in error_str:
            print("\n🔧 PERMISSION ISSUE:")
            print("   Check that:")
            print("   1. Vertex AI API is enabled in your project")
            print("   2. Your account has aiplatform.endpoints.predict permission")
            print("   3. The project ID in generate_embeddings.py is correct")
        elif "not found" in error_str.lower():
            print("\n🔧 AUTHENTICATION ISSUE:")
            print("   Try: gcloud auth application-default login")

        traceback.print_exc()
        raise


def test_generate_embeddings_edge_cases():
    """Test edge cases with real API."""
    print("\n" + "="*60)
    print("Testing edge cases...")

    # Load environment again
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    gcp_creds_path = "~/.config/gcloud/application_default_credentials.json"
    has_credentials = (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
        os.environ.get("GOOGLE_CLOUD_PROJECT") or
        os.path.exists(os.path.expanduser(gcp_creds_path))
    )

    if not has_credentials:
        pytest.skip("Google Cloud credentials not found")

    # Test with single item
    print("\n🧪 Testing single item...")
    single_item = [{"name": "テスト", "description": "単一項目のテスト"}]
    result = generate_text_embeddings(single_item)
    assert len(result) == 1
    assert len(result[0]) == 768
    print("✅ Single item test passed")

    # Test with empty strings (but valid structure)
    print("\n🧪 Testing minimal content...")
    minimal_items = [{"name": "A", "description": "B"}]
    result = generate_text_embeddings(minimal_items)
    assert len(result) == 1
    assert len(result[0]) == 768
    print("✅ Minimal content test passed")

    # Test with longer text
    print("\n🧪 Testing longer content...")
    long_items = [{
        "name": "複雑な家電製品",
        "description": ("これは非常に長い説明文です。" * 10) +
                      "多機能で高性能な家電製品について詳細に説明しています。" +
                      "様々な機能と特徴を持つ製品です。"
    }]
    result = generate_text_embeddings(long_items)
    assert len(result) == 1
    assert len(result[0]) == 768
    print("✅ Long content test passed")


def main():
    """Run the integration tests."""
    print("=" * 60)
    print("Vertex AI Embeddings Integration Test")
    print("=" * 60)

    try:
        test_generate_embeddings_integration()
        test_generate_embeddings_edge_cases()

        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        sys.exit(0)

    except (AssertionError, ValueError, RuntimeError) as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
