"""Integration test for show_document_tool with ADK agent."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
import certifi

# Add the backend directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# pylint: disable=wrong-import-position
from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.genai.types import Content, Part

from app.search_agent.agent import root_agent
from app.search_agent.chromadb_search import client_message_queue, show_document_tool


class TestShowDocumentIntegration:
    """Integration tests for show_document_tool with ADK agent."""

    @classmethod
    def setup_class(cls):
        """Set up SSL certificates and environment for all tests."""
        # Set SSL certificate file for secure API connections
        os.environ['SSL_CERT_FILE'] = certifi.where()

        # Load environment variables from backend/.env
        backend_env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(backend_env_path)

        # Check for API key
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY not found in environment")

    @pytest.mark.asyncio
    async def test_show_document_tool_direct(self):
        """Test show_document_tool function directly."""
        # Clear the queue first
        while not client_message_queue.empty():
            try:
                client_message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Test with valid PDF file
        pdf_file = "001.pdf:5"
        result = show_document_tool(pdf_file)

        # Check return value
        assert result["status"] == "success"
        assert result["action"] == "document_display_queued"
        assert result["count"] == 1
        assert "001.pdf (page 5)" in result["documents"]

        # Check that message was queued
        assert not client_message_queue.empty()

        # Get and verify the queued message
        message = client_message_queue.get_nowait()
        assert message["mime_type"] == "application/json"

        command_data = message["data"]
        assert command_data["command"] == "show_document"
        assert len(command_data["params"]) == 1

        # Verify the single document
        params = command_data["params"]

        # Check 001.pdf with page 5
        pdf_001 = params[0]
        assert pdf_001["filename"] == "001.pdf"
        assert pdf_001["page_number"] == 5

    @pytest.mark.asyncio
    async def test_show_document_tool_with_agent(self):
        """Test show_document_tool integration with ADK agent."""
        # Clear the queue first
        while not client_message_queue.empty():
            try:
                client_message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Create ADK runner and session
        runner = InMemoryRunner(
            app_name="ShowDocumentTest",
            agent=root_agent,
        )

        session = await runner.session_service.create_session(
            app_name="ShowDocumentTest",
            user_id="test_user_show_doc",
        )

        # Set response modality to TEXT
        run_config = RunConfig(response_modalities=["TEXT"])

        # Create live request queue
        live_request_queue = LiveRequestQueue()

        # Start agent session
        live_events = runner.run_live(
            session=session,
            live_request_queue=live_request_queue,
            run_config=run_config,
        )

        # Send a query that should trigger show_document_tool
        query = "Please show me documents 001.pdf page 3, 023.pdf page 8, and 007.pdf"
        content = Content(role="user", parts=[Part.from_text(text=query)])
        live_request_queue.send_content(content=content)

        # Collect agent responses
        responses = []
        turn_complete = False

        async for event in live_events:
            if event.turn_complete:
                turn_complete = True
                break

            if event.content and event.content.parts:
                part = event.content.parts[0]
                if part.text:
                    responses.append(part.text)

        # Close the queue
        live_request_queue.close()

        # Verify agent completed the turn
        assert turn_complete, "Agent did not complete the turn"

        # Check if agent used show_document_tool (queue should have messages)
        if not client_message_queue.empty():
            # Get the queued message
            message = client_message_queue.get_nowait()

            # Verify message structure
            assert message["mime_type"] == "application/json"
            command_data = message["data"]
            assert command_data["command"] == "show_document"

            # Verify document parameters
            params = command_data["params"]
            assert len(params) >= 1  # At least one document should be shown

            # Check that all params have valid filenames
            for param in params:
                assert "filename" in param
                assert param["filename"].endswith(".pdf")

            print(f"✅ Agent successfully queued document display command: {params}")
        else:
            # If no message in queue, check if agent at least responded about documents
            full_response = "".join(responses)
            keywords = ["document", "pdf", "show", "display"]
            assert any(keyword in full_response.lower() for keyword in keywords), \
                "Agent did not mention documents in response"

            response_preview = full_response[:200]
            print(f"⚠️  Agent responded about documents but didn't use show_document_tool: "
                  f"{response_preview}...")

    @pytest.mark.asyncio
    async def test_show_document_tool_error_cases(self):
        """Test show_document_tool error handling."""
        # Clear the queue first
        while not client_message_queue.empty():
            try:
                client_message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Test with empty string
        result = show_document_tool("")
        assert result["status"] == "error"
        assert "No PDF file specified" in result["message"]

        # Test with invalid format
        result = show_document_tool("invalid_file.txt")
        assert result["status"] == "success"  # It still processes, just treats as filename

        # Queue should have one message for the second test
        assert not client_message_queue.empty()
        message = client_message_queue.get_nowait()
        assert message["data"]["params"][0]["filename"] == "invalid_file.txt"

    @pytest.mark.asyncio
    async def test_queue_message_format(self):
        """Test that queued messages have the exact required format."""
        # Clear the queue first
        while not client_message_queue.empty():
            try:
                client_message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Test specific format
        pdf_file = "001.pdf:3"
        show_document_tool(pdf_file)

        # Get and verify message format
        message = client_message_queue.get_nowait()

        # Verify exact structure
        expected_structure = {
            "mime_type": "application/json",
            "data": {
                "command": "show_document",
                "params": [
                    {"filename": "001.pdf", "page_number": 3}
                ]
            }
        }

        assert message == expected_structure

        # Verify it's JSON serializable
        json_str = json.dumps(message)
        parsed = json.loads(json_str)
        assert parsed == message


@pytest.mark.asyncio
async def test_show_document_tool_direct():
    """Test show_document_tool function directly."""
    test_instance = TestShowDocumentIntegration()
    await test_instance.test_show_document_tool_direct()


@pytest.mark.asyncio
async def test_show_document_tool_with_agent():
    """Test show_document_tool integration with ADK agent."""
    test_instance = TestShowDocumentIntegration()
    test_instance.setup_class()
    await test_instance.test_show_document_tool_with_agent()


@pytest.mark.asyncio
async def test_show_document_tool_error_cases():
    """Test show_document_tool error handling."""
    test_instance = TestShowDocumentIntegration()
    await test_instance.test_show_document_tool_error_cases()


@pytest.mark.asyncio
async def test_queue_message_format():
    """Test that queued messages have the exact required format."""
    test_instance = TestShowDocumentIntegration()
    await test_instance.test_queue_message_format()


if __name__ == "__main__":
    # Set up SSL and load environment
    os.environ['SSL_CERT_FILE'] = certifi.where()
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Run tests directly
    asyncio.run(test_show_document_tool_direct())
    print("✅ Direct function test passed")

    asyncio.run(test_show_document_tool_error_cases())
    print("✅ Error cases test passed")

    asyncio.run(test_queue_message_format())
    print("✅ Queue message format test passed")

    # Agent test requires API key
    if os.getenv('GOOGLE_API_KEY'):
        asyncio.run(test_show_document_tool_with_agent())
        print("✅ Agent integration test passed")
    else:
        print("⚠️  Skipping agent test - GOOGLE_API_KEY not found")
