#!/usr/bin/env python3
"""
Simple test script to test queries with integer user IDs.
"""

import asyncio
import json
import time

import httpx


async def test_query(query: str, user_id: int):
    """Test a single query with integer user ID."""
    print(f"🔍 Testing query: {query}")
    print(f"   Using user_id: {user_id}")

    base_url = "http://127.0.0.1:8000"

    try:
        # Connect to SSE endpoint first
        sse_task = asyncio.create_task(listen_for_responses(user_id, base_url))

        # Wait a moment for SSE connection
        await asyncio.sleep(1)

        # Send query
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url}/send/{user_id}",
                json={
                    "mime_type": "text/plain",
                    "data": query
                }
            )

            print(f"   HTTP Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Response: {result}")

                if result.get("status") == "sent":
                    print("   ✅ Query sent successfully")

                    # Wait for response
                    await asyncio.sleep(10)  # Give time for agent to respond
                else:
                    print(f"   ❌ Query failed: {result}")
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
                print(f"   Response: {response.text}")

        # Cancel SSE listening
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass

    except Exception as exc:
        print(f"   ❌ Exception: {exc}")


async def listen_for_responses(user_id: int, base_url: str):
    """Listen for SSE responses."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "GET",
                f"{base_url}/events/{user_id}?is_audio=false"
            ) as response:
                print(f"   SSE Status: {response.status_code}")
                if response.status_code == 200:
                    print("   ✅ SSE connection established")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if data.get("turn_complete"):
                                    print("   ✅ Turn completed")
                                    break
                                if data.get("data"):
                                    print(f"   📝 Received: {data['data'][:100]}...")
                            except json.JSONDecodeError:
                                continue
                else:
                    print(f"   ❌ SSE error: {response.status_code}")
    except Exception as exc:
        print(f"   SSE Exception: {exc}")


async def main():
    """Main test function."""
    print("🧪 Testing queries with integer user IDs...")
    print("=" * 50)

    # Test queries
    test_queries = [
        "How do I set up Wi-Fi in my apartment?",
        "エアコンの使い方は？",  # How to use air conditioner in Japanese
        "parking regulations"
    ]

    base_time = int(time.time())

    for i, query in enumerate(test_queries, 1):
        user_id = base_time + i  # Unique integer user ID
        await test_query(query, user_id)
        print()

        # Brief pause between queries
        await asyncio.sleep(2)

    print("🎉 Query testing completed!")


if __name__ == "__main__":
    asyncio.run(main())
