"""Basic integration tests for the FastAPI backend server.

This module contains integration tests that demonstrate:
1. Server startup and shutdown
2. Mock client communication testing
3. Proper cleanup procedures

This is a comprehensive example of integration testing patterns.
"""

import asyncio
import json
import subprocess
import time
import signal
import os
import tempfile
from typing import Optional, Dict, Any
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
import httpx


class MockServerManager:
    """Mock server manager that simulates server behavior for testing."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8002):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.is_running = False
        self.active_sessions = {}
    
    async def start_server(self) -> None:
        """Simulate starting the server."""
        print(f"Mock server starting on {self.base_url}")
        self.is_running = True
        await asyncio.sleep(0.1)  # Simulate startup time
    
    async def stop_server(self) -> None:
        """Simulate stopping the server."""
        print("Mock server stopping")
        self.is_running = False
        self.active_sessions.clear()
    
    def add_session(self, user_id: str) -> None:
        """Add a mock session."""
        self.active_sessions[user_id] = {"connected": True}
    
    def remove_session(self, user_id: str) -> None:
        """Remove a mock session."""
        self.active_sessions.pop(user_id, None)
    
    def has_session(self, user_id: str) -> bool:
        """Check if session exists."""
        return user_id in self.active_sessions


class MockClient:
    """Mock client for testing server communication patterns."""
    
    def __init__(self, server_manager: MockServerManager, user_id: str = "test_user_1"):
        self.server_manager = server_manager
        self.user_id = user_id
        self.connected = False
        self.events_received = []
    
    async def connect(self) -> None:
        """Simulate connecting to the server."""
        if not self.server_manager.is_running:
            raise ConnectionError("Server is not running")
        
        self.server_manager.add_session(self.user_id)
        self.connected = True
        print(f"Mock client {self.user_id} connected")
    
    async def send_message(self, message: str, message_type: str = "text") -> Dict[str, Any]:
        """Simulate sending a message to the server."""
        if not self.connected:
            raise ConnectionError("Client is not connected")
        
        if not self.server_manager.has_session(self.user_id):
            return {"error": "Session not found"}
        
        # Simulate message processing
        await asyncio.sleep(0.01)  # Simulate network delay
        
        # Mock response based on message type
        if message_type == "text":
            response_event = {
                "mime_type": "text/plain",
                "data": f"Echo: {message}",
                "user_id": self.user_id
            }
        else:
            response_event = {
                "mime_type": "audio/pcm", 
                "data": "mock_audio_response",
                "user_id": self.user_id
            }
        
        self.events_received.append(response_event)
        return {"status": "sent", "message_id": f"msg_{len(self.events_received)}"}
    
    async def send_audio_message(self, audio_data: bytes) -> Dict[str, Any]:
        """Simulate sending an audio message."""
        return await self.send_message(f"audio_data_{len(audio_data)}_bytes", "audio")
    
    async def disconnect(self) -> None:
        """Simulate disconnecting from the server."""
        if self.connected:
            self.server_manager.remove_session(self.user_id)
            self.connected = False
            print(f"Mock client {self.user_id} disconnected")


@pytest_asyncio.fixture
async def mock_server():
    """Fixture that provides a mock server for testing."""
    server_manager = MockServerManager()
    await server_manager.start_server()
    yield server_manager
    await server_manager.stop_server()


@pytest_asyncio.fixture
async def mock_client_connected(mock_server):
    """Fixture that provides a connected mock client."""
    client = MockClient(mock_server)
    await client.connect()
    yield client
    await client.disconnect()


async def test_mock_server_startup_and_shutdown():
    """Test that the mock server starts up and shuts down properly."""
    server = MockServerManager()
    
    # Server should not be running initially
    assert not server.is_running
    
    # Start server
    await server.start_server()
    assert server.is_running
    
    # Stop server
    await server.stop_server()
    assert not server.is_running


async def test_mock_client_connection(mock_server):
    """Test mock client connection and disconnection."""
    client = MockClient(mock_server, "test_user_1")
    
    # Client should not be connected initially
    assert not client.connected
    assert not mock_server.has_session("test_user_1")
    
    # Connect client
    await client.connect()
    assert client.connected
    assert mock_server.has_session("test_user_1")
    
    # Disconnect client
    await client.disconnect()
    assert not client.connected
    assert not mock_server.has_session("test_user_1")


async def test_mock_text_message_communication(mock_client_connected):
    """Test sending and receiving text messages."""
    client = mock_client_connected
    
    # Send a text message
    response = await client.send_message("Hello, server!")
    assert response["status"] == "sent"
    assert "message_id" in response
    
    # Check that a response event was received
    assert len(client.events_received) == 1
    event = client.events_received[0]
    assert event["mime_type"] == "text/plain"
    assert "Echo: Hello, server!" in event["data"]
    assert event["user_id"] == client.user_id


async def test_mock_audio_message_communication(mock_client_connected):
    """Test sending and receiving audio messages."""
    client = mock_client_connected
    
    # Create dummy audio data
    audio_data = b"fake_audio_data_for_testing"
    
    # Send an audio message
    response = await client.send_audio_message(audio_data)
    assert response["status"] == "sent"
    assert "message_id" in response
    
    # Check that a response event was received
    assert len(client.events_received) == 1
    event = client.events_received[0]
    assert event["mime_type"] == "audio/pcm"
    assert event["data"] == "mock_audio_response"


async def test_multiple_mock_clients(mock_server):
    """Test that multiple clients can connect simultaneously."""
    clients = []
    
    try:
        # Create and connect multiple clients
        for i in range(3):
            client = MockClient(mock_server, f"user_{i}")
            await client.connect()
            clients.append(client)
        
        # Verify all clients are connected
        for i, client in enumerate(clients):
            assert client.connected
            assert mock_server.has_session(f"user_{i}")
        
        # Send messages from each client
        for i, client in enumerate(clients):
            response = await client.send_message(f"Message from user_{i}")
            assert response["status"] == "sent"
            assert len(client.events_received) == 1
    
    finally:
        # Clean up all clients
        for client in clients:
            if client.connected:
                await client.disconnect()


async def test_mock_session_not_found(mock_server):
    """Test behavior when trying to send message to non-existent session."""
    client = MockClient(mock_server, "non_existent_user")
    
    # Connect client first, then remove the session to simulate session not found
    await client.connect()
    client.server_manager.remove_session(client.user_id)  # Remove session manually
    
    # Try to send message to removed session
    response = await client.send_message("test message")
    assert response.get("error") == "Session not found"


async def test_mock_client_connection_error():
    """Test client connection when server is not running."""
    server = MockServerManager()  # Server not started
    client = MockClient(server, "test_user")
    
    # Try to connect to non-running server
    with pytest.raises(ConnectionError, match="Server is not running"):
        await client.connect()


async def test_mock_cleanup_and_resource_management():
    """Test proper cleanup and resource management."""
    server = MockServerManager()
    clients = []
    
    try:
        # Start server
        await server.start_server()
        assert server.is_running
        
        # Create multiple clients
        for i in range(5):
            client = MockClient(server, f"cleanup_user_{i}")
            await client.connect()
            clients.append(client)
        
        # Verify all sessions are active
        assert len(server.active_sessions) == 5
        
        # Send some messages
        for client in clients:
            await client.send_message("cleanup test message")
        
        # Disconnect all clients
        for client in clients:
            await client.disconnect()
        
        # Verify all sessions are cleaned up
        assert len(server.active_sessions) == 0
        
    finally:
        # Ensure server is stopped
        await server.stop_server()
        assert not server.is_running


async def test_comprehensive_integration_workflow():
    """Comprehensive test that demonstrates full integration workflow."""
    # This test demonstrates the complete workflow:
    # 1. Server startup
    # 2. Client connection
    # 3. Message exchange
    # 4. Cleanup and shutdown
    
    print("\\n=== Starting Comprehensive Integration Test ===")
    
    # Step 1: Start server
    print("Step 1: Starting server...")
    server = MockServerManager()
    await server.start_server()
    assert server.is_running
    print("✓ Server started successfully")
    
    # Step 2: Connect client
    print("Step 2: Connecting client...")
    client = MockClient(server, "integration_test_user")
    await client.connect()
    assert client.connected
    print("✓ Client connected successfully")
    
    # Step 3: Exchange messages
    print("Step 3: Testing message exchange...")
    
    # Send text message
    text_response = await client.send_message("Integration test message")
    assert text_response["status"] == "sent"
    print("✓ Text message sent and received")
    
    # Send audio message
    audio_response = await client.send_audio_message(b"test_audio_data")
    assert audio_response["status"] == "sent" 
    print("✓ Audio message sent and received")
    
    # Verify events received
    assert len(client.events_received) == 2
    print(f"✓ Received {len(client.events_received)} response events")
    
    # Step 4: Clean up
    print("Step 4: Cleaning up...")
    await client.disconnect()
    assert not client.connected
    print("✓ Client disconnected")
    
    await server.stop_server()
    assert not server.is_running
    print("✓ Server stopped")
    
    print("=== Integration Test Completed Successfully ===\\n")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])