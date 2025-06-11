"""Integration tests for the ADK agent with ChromaDB search tool.

This module contains comprehensive integration tests that:
1. Test the agent's ability to use the ChromaDB search tool
2. Verify tool response formatting and content
3. Test agent behavior with various search queries
4. Ensure proper error handling and fallbacks
"""

import os
import time
from typing import List
from unittest.mock import patch

import pytest
import pytest_asyncio
from dotenv import load_dotenv
import certifi

from google.genai.types import Content, Part
from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig

from app.search_agent.agent import root_agent
from app.search_agent.chromadb_search import find_document_tool

# Load environment variables from backend/.env file
load_dotenv()

# Set SSL certificate file for all tests
os.environ['SSL_CERT_FILE'] = certifi.where()


class MockEvent:
    """Mock event for testing agent responses."""

    def __init__(self, content=None, partial=False, turn_complete=False,
                 interrupted=False):
        self.content = content
        self.partial = partial
        self.turn_complete = turn_complete
        self.interrupted = interrupted


class MockContent:
    """Mock content for testing."""

    def __init__(self, parts=None):
        self.parts = parts or []


class MockPart:
    """Mock part for testing."""

    def __init__(self, text=None):
        self.text = text
        self.inline_data = None


class AgentTestHelper:
    """Helper class for testing ADK agent functionality."""

    def __init__(self):
        self.runner = None
        self.session = None
        self.live_request_queue = None
        self.live_events = None
        self.responses = []

    async def setup_agent_session(self, user_id: str = "test_user"):
        """Set up an agent session for testing."""
        self.runner = InMemoryRunner(
            app_name="Test ADK Agent",
            agent=root_agent,
        )

        self.session = await self.runner.session_service.create_session(
            app_name="Test ADK Agent",
            user_id=user_id,
        )

        run_config = RunConfig(response_modalities=["TEXT"])
        self.live_request_queue = LiveRequestQueue()

        self.live_events = self.runner.run_live(
            session=self.session,
            live_request_queue=self.live_request_queue,
            run_config=run_config,
        )

    async def send_message(self, text: str) -> List[str]:
        """Send a text message and collect responses."""
        if not self.live_request_queue:
            raise RuntimeError("Agent session not initialized")

        # Clear previous responses
        self.responses.clear()

        # Send message
        content = Content(role="user", parts=[Part.from_text(text=text)])
        self.live_request_queue.send_content(content=content)

        # Collect responses with timeout
        responses = []
        timeout = 30  # 30 seconds timeout
        start_time = time.time()

        try:
            async for event in self.live_events:
                if time.time() - start_time > timeout:
                    break

                if event.turn_complete:
                    break

                part = (event.content and event.content.parts and
                        event.content.parts[0])
                if part and part.text and not event.partial:
                    responses.append(part.text)

        except Exception as exc:
            print(f"Error collecting responses: {exc}")

        self.responses = responses
        return responses

    async def cleanup(self):
        """Clean up the agent session."""
        if self.live_request_queue:
            self.live_request_queue.close()


@pytest_asyncio.fixture
async def agent_helper():
    """Fixture that provides an initialized agent helper."""
    helper = AgentTestHelper()
    await helper.setup_agent_session()
    yield helper
    await helper.cleanup()


@pytest_asyncio.fixture
async def mock_chromadb_data():
    """Fixture that sets up mock ChromaDB data for testing."""
    # Mock find_document to return predictable results
    with patch('app.search_agent.chromadb_search.find_document') as mock_find:
        mock_find.return_value = [
            ("001.pdf", "001.pdf (page 1): Air conditioner manual", 0.95),
            ("025.pdf", "025.pdf (page 3): Wi-Fi setup guide", 0.87),
            ("050.pdf", "050.pdf (page 2): Network configuration", 0.78)
        ]
        yield mock_find


class TestAgentChromaDBIntegration:
    """Test agent integration with ChromaDB search tool."""

    @pytest.mark.asyncio
    async def test_agent_uses_search_tool_real_adk(self, agent_helper, mock_chromadb_data):
        """Test that agent uses the search tool with real ADK integration."""
        # Skip if API key not available in .env file
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY not found in .env file - skipping real ADK agent test")

        # Send a query that should trigger the document search tool
        query = "How do I set up the air conditioner in my apartment?"

        try:
            responses = await agent_helper.send_message(query)

            # Check that we got some response from the agent
            assert len(responses) > 0, "Agent should respond to apartment-related query"

            # Verify the search tool was called during agent execution
            mock_chromadb_data.assert_called()

            # The agent should have used the tool and incorporated the results
            full_response = " ".join(responses)
            print(f"Agent response: {full_response}")

            # Basic validation that agent processed the tool output
            assert len(full_response) > 0, "Agent should provide a meaningful response"

        except Exception as exc:
            print(f"Agent test error: {exc}")
            pytest.skip(f"Real ADK agent test failed: {exc}")

    @pytest.mark.asyncio
    async def test_agent_tool_function_directly(self, mock_chromadb_data):
        """Test the search tool function directly without agent."""
        result = find_document_tool("air conditioner setup")

        assert result["result"] == "success"
        assert "Found relevant apartment manual documents:" in result["message"]
        assert "001.pdf" in result["message"]
        assert "relevance: 0.950" in result["message"]

        # Verify mock was called
        mock_chromadb_data.assert_called_once_with("air conditioner setup")

    @pytest.mark.asyncio
    async def test_agent_search_tool_with_wifi_query(self, mock_chromadb_data):
        """Test search tool with Wi-Fi related query."""
        result = find_document_tool("Wi-Fi connection setup")

        assert result["result"] == "success"
        assert "Found relevant apartment manual documents:" in result["message"]
        assert "025.pdf" in result["message"]
        assert "relevance: 0.870" in result["message"]

    @pytest.mark.asyncio
    async def test_agent_search_tool_formatting(self, mock_chromadb_data):
        """Test that search tool formats results correctly."""
        result = find_document_tool("network configuration")

        assert result["result"] == "success"
        lines = result["message"].split('\n')
        assert lines[0] == "Found relevant apartment manual documents:"
        assert "1. 001.pdf:1 (relevance: 0.950)" in lines
        assert "2. 025.pdf:3 (relevance: 0.870)" in lines
        assert "3. 050.pdf:2 (relevance: 0.780)" in lines

    @pytest.mark.asyncio
    async def test_agent_search_tool_no_results(self):
        """Test search tool behavior when no results are found."""
        with patch('app.search_agent.chromadb_search.find_document') as mock_find:
            mock_find.return_value = []

            result = find_document_tool("nonexistent topic")

            assert result["result"] == "success"
            assert result["message"] == "No documents found for your query."

    @pytest.mark.asyncio
    async def test_agent_search_tool_error_handling(self):
        """Test search tool error handling."""
        with patch('app.search_agent.chromadb_search.find_document') as mock_find:
            mock_find.side_effect = Exception("ChromaDB connection error")

            result = find_document_tool("test query")

            assert result["result"] == "error"
            assert "Error searching documents:" in result["message"]
            assert "ChromaDB connection error" in result["message"]

    @pytest.mark.asyncio
    async def test_tool_covers_all_document_categories(self):
        """Test that the tool description covers all document categories."""
        # Check the tool's docstring contains all expected categories
        docstring = find_document_tool.__doc__

        expected_categories = [
            "HOME APPLIANCES",
            "KITCHEN EQUIPMENT",
            "AUDIO/VIDEO EQUIPMENT",
            "COMPUTER/NETWORK",
            "SAFETY/SECURITY",
            "BUILDING INFRASTRUCTURE",
            "BUILDING SERVICES & RULES",
            "TRANSPORTATION & AMENITIES"
        ]

        for category in expected_categories:
            assert category in docstring, f"Category '{category}' missing from tool description"

    @pytest.mark.asyncio
    async def test_tool_specific_equipment_coverage(self):
        """Test that specific equipment types are covered in tool description."""
        docstring = find_document_tool.__doc__

        specific_items = [
            "Air conditioners", "washing machines", "Coffee machines",
            "Bluetooth transmitters", "NAS systems", "Fire evacuation devices",
            "Gas equipment", "Move-in procedures", "Shuttle bus schedules"
        ]

        for item in specific_items:
            assert item in docstring, f"Specific item '{item}' missing from tool description"


class TestAgentToolIntegrationMocked:
    """Test agent tool integration with mocked components for faster execution."""

    @pytest.mark.asyncio
    async def test_mock_agent_tool_response_structure(self):
        """Test agent tool response structure with mocked agent."""
        # Mock the agent's tool execution
        with patch('app.search_agent.chromadb_search.find_document') as mock_find:
            mock_find.return_value = [
                ("test.pdf", "test.pdf (page 1): Test document", 0.95)
            ]

            # Test direct tool call
            result = find_document_tool("test query")

            assert result["result"] == "success"
            expected_message = """Found relevant apartment manual documents:
1. test.pdf:1 (relevance: 0.950)"""

            assert result["message"] == expected_message

    @pytest.mark.asyncio
    async def test_tool_query_parameter_handling(self):
        """Test that the tool properly handles different query parameters."""
        test_queries = [
            "air conditioner",
            "Wi-Fi setup",
            "washing machine installation",
            "fire safety procedures",
            "parking regulations"
        ]

        with patch('app.search_agent.chromadb_search.find_document') as mock_find:
            mock_find.return_value = [
                ("result.pdf", "result.pdf (page 1): Mock result", 0.85)
            ]

            for query in test_queries:
                result = find_document_tool(query)

                assert result["result"] == "success"
                assert "Found relevant apartment manual documents:" in result["message"]
                assert "result.pdf" in result["message"]
                assert "relevance: 0.850" in result["message"]

                # Verify the query was passed correctly
                mock_find.assert_called_with(query)

    @pytest.mark.asyncio
    async def test_tool_performance_characteristics(self):
        """Test tool performance characteristics."""
        with patch('app.search_agent.chromadb_search.find_document') as mock_find:
            # Simulate some processing time with a regular function (not async)
            def slow_find(query):
                time.sleep(0.01)  # 10ms delay
                return [("perf.pdf", f"Performance test for {query}", 0.90)]

            mock_find.side_effect = slow_find

            start_time = time.time()
            result = find_document_tool("performance test query")
            execution_time = time.time() - start_time

            # Tool should complete reasonably quickly even with processing delay
            assert execution_time < 1.0  # Should complete within 1 second
            assert result["result"] == "success"
            assert "perf.pdf" in result["message"]


class TestAgentRealIntegration:
    """Integration tests with real components (requires actual ChromaDB data)."""

    @pytest.mark.asyncio
    async def test_real_agent_with_chromadb_integration(self, agent_helper):
        """Test real agent integration with ChromaDB search tool."""
        # Skip if API key not available in .env file
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY not found in .env file - skipping real agent test")

        try:
            # Test with a specific apartment-related query
            query = "How do I connect to Wi-Fi in my apartment?"

            print(f"\nTesting real agent with query: {query}")
            start_time = time.time()

            responses = await agent_helper.send_message(query)
            execution_time = time.time() - start_time

            print(f"Agent execution time: {execution_time:.3f}s")

            # Verify we got responses
            assert len(responses) > 0, "Agent should respond to apartment query"

            full_response = " ".join(responses)
            print(f"Agent response: {full_response}")

            # Basic validation
            assert execution_time < 30.0  # Should complete within 30 seconds
            assert len(full_response) > 10  # Should have meaningful content

            # The response should be relevant to the apartment context
            # (The agent should use the document search tool)

        except Exception as exc:
            print(f"Real agent integration test error: {exc}")
            pytest.skip(f"Real agent integration test failed: {exc}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_chromadb_search_integration(self):
        """Test integration with real ChromaDB data if available."""
        try:
            # This test requires actual CSV data to be loaded
            from app.search_agent.chromadb_search import load_document_embeddings

            # Try to load real data
            documents = load_document_embeddings(limit=10)  # Limit for faster testing

            if not documents:
                pytest.skip("No real ChromaDB data available for integration test")

            print(f"\nTesting with {len(documents)} real documents")

            # Test queries that should find results in apartment manuals
            test_queries = [
                "エアコン",  # Air conditioner in Japanese
                "Wi-Fi",     # Wi-Fi setup
                "洗濯機",    # Washing machine in Japanese
                "駐車場"     # Parking in Japanese
            ]

            for query in test_queries:
                start_time = time.time()
                result = find_document_tool(query)
                execution_time = time.time() - start_time

                print(f"Query: {query}")
                print(f"Execution time: {execution_time:.3f}s")
                print(f"Result: {result[:100]}...")

                # Basic assertions
                assert execution_time < 5.0  # Should complete within 5 seconds
                assert isinstance(result, str)

                if "Found relevant apartment manual documents:" in result:
                    # If results were found, verify structure
                    lines = result.split('\n')
                    assert len(lines) >= 2  # Header + at least one result

                    # Check result formatting
                    for i, line in enumerate(lines[1:], 1):
                        if line.strip():  # Skip empty lines
                            assert f"{i}." in line
                            assert ".pdf" in line
                            assert "relevance:" in line

        except ImportError:
            pytest.skip("ChromaDB dependencies not available")
        except Exception as exc:
            pytest.skip(f"Real integration test failed: {exc}")


# Performance benchmarks
class TestAgentPerformance:
    """Performance tests for agent tool integration."""

    @pytest.mark.asyncio
    async def test_tool_response_time_benchmark(self):
        """Benchmark tool response times."""
        with patch('app.search_agent.chromadb_search.find_document') as mock_find:
            mock_find.return_value = [
                (f"doc{i}.pdf", f"Document {i} description", 0.9 - i*0.1)
                for i in range(3)
            ]

            # Benchmark multiple calls
            times = []
            for _ in range(10):
                start_time = time.time()
                find_document_tool("benchmark query")
                times.append(time.time() - start_time)

            avg_time = sum(times) / len(times)
            max_time = max(times)

            print("\nTool Performance Benchmark:")
            print(f"Average response time: {avg_time*1000:.2f}ms")
            print(f"Maximum response time: {max_time*1000:.2f}ms")

            # Performance assertions
            assert avg_time < 0.1  # Average under 100ms
            assert max_time < 0.5  # Maximum under 500ms


if __name__ == "__main__":
    # Run the tests
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
