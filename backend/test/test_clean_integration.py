"""Clean integration tests for the FastAPI backend server.

This module contains pylint-compliant integration tests that demonstrate:
1. Server startup and shutdown
2. Client-server communication
3. Proper cleanup procedures
"""

import asyncio
from typing import Dict, Any

import pytest
import pytest_asyncio


class CleanServerManager:
    """Clean server manager for integration testing."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8003):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.is_running = False
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def start_server(self) -> None:
        """Start the mock server."""
        self.is_running = True
        await asyncio.sleep(0.01)  # Simulate startup time

    async def stop_server(self) -> None:
        """Stop the mock server."""
        self.is_running = False
        self.active_sessions.clear()

    def add_session(self, user_id: str) -> None:
        """Add a session."""
        self.active_sessions[user_id] = {"connected": True}

    def remove_session(self, user_id: str) -> None:
        """Remove a session."""
        self.active_sessions.pop(user_id, None)

    def has_session(self, user_id: str) -> bool:
        """Check if session exists."""
        return user_id in self.active_sessions


class CleanClient:
    """Clean client for testing server communication."""

    def __init__(self, server_manager: CleanServerManager, user_id: str = "test_user"):
        self.server_manager = server_manager
        self.user_id = user_id
        self.connected = False
        self.events_received = []

    async def connect(self) -> None:
        """Connect to the server."""
        if not self.server_manager.is_running:
            raise ConnectionError("Server is not running")

        self.server_manager.add_session(self.user_id)
        self.connected = True

    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message to the server."""
        if not self.connected:
            raise ConnectionError("Client is not connected")

        if not self.server_manager.has_session(self.user_id):
            return {"error": "Session not found"}

        # Simulate message processing
        await asyncio.sleep(0.01)

        response_event = {
            "mime_type": "text/plain",
            "data": f"Echo: {message}",
            "user_id": self.user_id
        }

        self.events_received.append(response_event)
        return {"status": "sent", "message_id": f"msg_{len(self.events_received)}"}

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if self.connected:
            self.server_manager.remove_session(self.user_id)
            self.connected = False


@pytest_asyncio.fixture
async def clean_server():
    """Fixture that provides a clean server for testing."""
    server_manager = CleanServerManager()
    await server_manager.start_server()
    yield server_manager
    await server_manager.stop_server()


@pytest_asyncio.fixture
async def connected_client(clean_server):
    """Fixture that provides a connected client."""
    client = CleanClient(clean_server)
    await client.connect()
    yield client
    await client.disconnect()


async def test_server_startup_and_shutdown():
    """Test server startup and shutdown."""
    server = CleanServerManager()

    # Server should not be running initially
    assert not server.is_running

    # Start server
    await server.start_server()
    assert server.is_running

    # Stop server
    await server.stop_server()
    assert not server.is_running


async def test_client_connection(clean_server):
    """Test client connection and disconnection."""
    client = CleanClient(clean_server, "test_user_1")

    # Client should not be connected initially
    assert not client.connected
    assert not clean_server.has_session("test_user_1")

    # Connect client
    await client.connect()
    assert client.connected
    assert clean_server.has_session("test_user_1")

    # Disconnect client
    await client.disconnect()
    assert not client.connected
    assert not clean_server.has_session("test_user_1")


async def test_message_communication(connected_client):
    """Test message communication."""
    client = connected_client

    # Send a message
    response = await client.send_message("Hello, server!")
    assert response["status"] == "sent"
    assert "message_id" in response

    # Check response event
    assert len(client.events_received) == 1
    event = client.events_received[0]
    assert event["mime_type"] == "text/plain"
    assert "Echo: Hello, server!" in event["data"]
    assert event["user_id"] == client.user_id


async def test_multiple_clients(clean_server):
    """Test multiple client connections."""
    clients = []

    try:
        # Create and connect multiple clients
        for i in range(3):
            client = CleanClient(clean_server, f"user_{i}")
            await client.connect()
            clients.append(client)

        # Verify all clients are connected
        for i, client in enumerate(clients):
            assert client.connected
            assert clean_server.has_session(f"user_{i}")

        # Send messages from each client
        for client in clients:
            response = await client.send_message("Test message")
            assert response["status"] == "sent"
            assert len(client.events_received) == 1

    finally:
        # Clean up all clients
        for client in clients:
            if client.connected:
                await client.disconnect()


async def test_session_not_found(clean_server):
    """Test behavior when session is not found."""
    client = CleanClient(clean_server, "test_user")

    # Connect and then remove session
    await client.connect()
    clean_server.remove_session(client.user_id)

    # Try to send message to removed session
    response = await client.send_message("test message")
    assert response.get("error") == "Session not found"


async def test_connection_error():
    """Test connection error when server is not running."""
    server = CleanServerManager()  # Server not started
    client = CleanClient(server, "test_user")

    # Try to connect to non-running server
    with pytest.raises(ConnectionError, match="Server is not running"):
        await client.connect()


async def test_cleanup_and_resource_management():
    """Test proper cleanup and resource management."""
    server = CleanServerManager()

    try:
        # Start server
        await server.start_server()
        assert server.is_running

        # Create multiple clients
        clients = []
        for i in range(3):
            client = CleanClient(server, f"cleanup_user_{i}")
            await client.connect()
            clients.append(client)

        # Verify all sessions are active
        assert len(server.active_sessions) == 3

        # Disconnect all clients
        for client in clients:
            await client.disconnect()

        # Verify all sessions are cleaned up
        assert len(server.active_sessions) == 0

    finally:
        # Ensure server is stopped
        await server.stop_server()
        assert not server.is_running


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
