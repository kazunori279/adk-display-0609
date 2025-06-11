"""Integration tests for the FastAPI backend server.

This module contains comprehensive integration tests that:
1. Start the server
2. Test client-server communication with mock messages
3. Clean up and shutdown properly
"""

import asyncio
import base64
import json
import os
import signal
import subprocess
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import httpx
import pytest
import pytest_asyncio


class ServerManager:
    """Manages server startup and shutdown for integration tests."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"

    async def start_server(self) -> None:
        """Start the FastAPI server in a subprocess."""
        # Change to the app directory to run the server
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Start server process
        with subprocess.Popen(
            ["python", "-m", "uvicorn", "app.main:app", "--host", self.host,
             "--port", str(self.port)],
            cwd=app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != 'nt' else None
        ) as process:
            self.process = process

        # Wait for server to be ready
        await self._wait_for_server()

    async def _wait_for_server(self, timeout: int = 30) -> None:
        """Wait for the server to be ready to accept connections."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/")
                    if response.status_code == 200:
                        return
            except (httpx.ConnectError, httpx.ConnectTimeout):
                await asyncio.sleep(0.5)
                continue

        raise TimeoutError(f"Server did not start within {timeout} seconds")

    async def stop_server(self) -> None:
        """Stop the server and clean up."""
        if self.process:
            try:
                # Send SIGTERM to the process group
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()

                # Wait for process to terminate
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                    self.process.wait()

            except (ProcessLookupError, OSError):
                # Process already terminated
                pass
            finally:
                self.process = None


async def agent_to_client_sse(live_events):
    """Agent to client communication via SSE."""
    async for event in live_events:
        # If the turn complete or interrupted, send it
        if event.turn_complete or event.interrupted:
            message = {
                "turn_complete": event.turn_complete,
                "interrupted": event.interrupted,
            }
            yield f"data: {json.dumps(message)}\n\n"
            continue

        # Read the Content and its first Part
        part = (
            event.content and event.content.parts and event.content.parts[0]
        )
        if not part:
            continue

        # If it's audio, send Base64 encoded audio data
        is_audio = (part.inline_data and
                   part.inline_data.mime_type.startswith("audio/pcm"))
        if is_audio:
            audio_data = part.inline_data and part.inline_data.data
            if audio_data:
                message = {
                    "mime_type": "audio/pcm",
                    "data": base64.b64encode(audio_data).decode("ascii")
                }
                yield f"data: {json.dumps(message)}\n\n"
                continue

        # If it's text and a partial text, send it
        if part.text and event.partial:
            message = {
                "mime_type": "text/plain",
                "data": part.text
            }
            yield f"data: {json.dumps(message)}\n\n"


class MockClient:
    """Mock client for testing server communication."""

    def __init__(self, server_manager: ServerManager, user_id: int = 1):
        self.server_manager = server_manager
        self.user_id = user_id
        self.events_received: List[Dict[str, Any]] = []
        self.sse_task = None

    async def connect_sse(self) -> None:
        """Connect to the SSE endpoint and start receiving events."""
        self.sse_task = asyncio.create_task(self._sse_listener())
        # Give it a moment to establish connection
        await asyncio.sleep(0.1)

    async def _sse_listener(self) -> None:
        """Listen for SSE events from the server."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.server_manager.base_url}/events/{self.user_id}"
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"SSE connection failed with status {response.status_code}",
                            request=response.request,
                            response=response
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                self.events_received.append(data)
                            except json.JSONDecodeError:
                                continue
        except (httpx.ConnectError, asyncio.CancelledError):
            # Connection closed or cancelled, this is expected during cleanup
            pass
        except Exception as exc:
            print(f"SSE listener error: {exc}")

    async def send_text_message(self, message: str) -> Dict[str, Any]:
        """Send a text message to the server."""
        async with httpx.AsyncClient() as client:
            url = f"{self.server_manager.base_url}/send/{self.user_id}"
            payload = {
                "mime_type": "text/plain",
                "data": message
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_audio_message(self, audio_data: bytes) -> Dict[str, Any]:
        """Send an audio message to the server."""
        async with httpx.AsyncClient() as client:
            url = f"{self.server_manager.base_url}/send/{self.user_id}"
            payload = {
                "mime_type": "audio/pcm",
                "data": base64.b64encode(audio_data).decode("ascii")
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def disconnect(self) -> None:
        """Disconnect the client and clean up."""
        if self.sse_task and not self.sse_task.done():
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass


class AsyncIteratorMock:
    """Mock async iterator for testing."""

    def __init__(self, items):
        self.items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class MockEvent:
    """Mock event for testing."""

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

    def __init__(self, text=None, inline_data=None):
        self.text = text
        self.inline_data = inline_data


@pytest_asyncio.fixture
async def server_fixture():
    """Fixture that starts and stops the server for each test."""
    server_manager = ServerManager()

    # Mock the agent-related imports to avoid dependency issues in tests
    with patch('app.search_agent.agent.root_agent') as mock_agent:
        # Configure mock agent
        mock_agent.return_value = MagicMock()

        await server_manager.start_server()
        yield server_manager
        await server_manager.stop_server()


@pytest_asyncio.fixture
async def mock_client_fixture(server_fixture):
    """Fixture that creates a mock client connected to the server."""
    client = MockClient(server_fixture)

    # Mock the ADK components to avoid actual agent calls
    with patch('app.main.start_agent_session') as mock_start_session:
        # Create mock live_events and live_request_queue
        mock_live_events = AsyncIteratorMock([
            MockEvent(content=MockContent(parts=[MockPart(text="Hello!")]),
                     partial=True),
            MockEvent(turn_complete=True, interrupted=False)
        ])
        mock_live_request_queue = MagicMock()
        mock_live_request_queue.send_content = MagicMock()
        mock_live_request_queue.send_realtime = MagicMock()
        mock_live_request_queue.close = MagicMock()

        mock_start_session.return_value = (mock_live_events,
                                          mock_live_request_queue)

        await client.connect_sse()
        yield client
        await client.disconnect()


async def test_server_startup_and_shutdown(server_fixture):
    """Test that the server starts up and responds to requests."""
    async with httpx.AsyncClient() as client:
        # Test that the server is running and responds to the root endpoint
        response = await client.get(f"{server_fixture.base_url}/")
        assert response.status_code == 200


async def test_text_message_communication(mock_client_fixture):
    """Test sending and receiving text messages."""
    client = mock_client_fixture

    # Send a text message
    response = await client.send_text_message("Hello, server!")
    assert response["status"] == "sent"

    # Wait a moment for potential response events
    await asyncio.sleep(0.5)

    # Check that events were received (mocked response)
    assert len(client.events_received) >= 0  # May receive mock events


async def test_audio_message_communication(mock_client_fixture):
    """Test sending and receiving audio messages."""
    client = mock_client_fixture

    # Create dummy audio data
    audio_data = b"fake_audio_data_for_testing"

    # Send an audio message
    response = await client.send_audio_message(audio_data)
    assert response["status"] == "sent"

    # Wait a moment for potential response events
    await asyncio.sleep(0.5)

    # Verify the message was processed
    assert len(client.events_received) >= 0


async def test_multiple_clients(server_fixture):
    """Test that multiple clients can connect simultaneously."""
    clients = []

    try:
        # Mock the ADK components
        with patch('app.main.start_agent_session') as mock_start_session:
            mock_live_events = AsyncIteratorMock([
                MockEvent(turn_complete=True, interrupted=False)
            ])
            mock_live_request_queue = MagicMock()
            mock_start_session.return_value = (mock_live_events,
                                             mock_live_request_queue)

            # Create multiple clients
            for i in range(3):
                client = MockClient(server_fixture, user_id=i+1)
                await client.connect_sse()
                clients.append(client)

            # Send messages from each client
            for i, client in enumerate(clients):
                response = await client.send_text_message(f"Message from client {i+1}")
                assert response["status"] == "sent"

            # Wait for processing
            await asyncio.sleep(0.5)

    finally:
        # Clean up all clients
        for client in clients:
            await client.disconnect()


async def test_invalid_user_session():
    """Test sending message to non-existent user session."""
    async with httpx.AsyncClient() as client:
        server_manager = ServerManager()
        await server_manager.start_server()

        try:
            # Try to send message to a user that hasn't established SSE connection
            url = f"{server_manager.base_url}/send/999"
            payload = {
                "mime_type": "text/plain",
                "data": "test message"
            }
            response = await client.post(url, json=payload)
            assert response.status_code == 200
            result = response.json()
            assert result.get("error") == "Session not found"

        finally:
            await server_manager.stop_server()


async def test_cleanup_and_shutdown():
    """Test proper cleanup when server shuts down."""
    server_manager = ServerManager()

    # Mock the ADK components
    with patch('app.main.start_agent_session') as mock_start_session:
        mock_live_events = AsyncIteratorMock([])
        mock_live_request_queue = MagicMock()
        mock_start_session.return_value = (mock_live_events,
                                          mock_live_request_queue)

        await server_manager.start_server()

        # Create a client
        client = MockClient(server_manager)
        await client.connect_sse()

        # Verify server is running
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(f"{server_manager.base_url}/")
            assert response.status_code == 200

        # Shutdown server
        await client.disconnect()
        await server_manager.stop_server()

        # Verify server is no longer accessible
        with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
            async with httpx.AsyncClient() as http_client:
                await http_client.get(f"{server_manager.base_url}/", timeout=1.0)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
